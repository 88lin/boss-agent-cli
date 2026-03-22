import random
import time

import click

from boss_agent_cli.api.client import BossClient
from boss_agent_cli.api.models import JobItem
from boss_agent_cli.auth.manager import AuthManager, AuthRequired, TokenRefreshFailed
from boss_agent_cli.cache.store import CacheStore
from boss_agent_cli.output import emit_error, emit_success


@click.command("greet")
@click.argument("security_id")
@click.argument("job_id")
@click.option("--message", default="", help="自定义打招呼消息")
@click.pass_context
def greet_cmd(ctx, security_id, job_id, message):
	"""向指定招聘者打招呼"""
	data_dir = ctx.obj["data_dir"]
	logger = ctx.obj["logger"]
	delay = ctx.obj["delay"]

	cache = CacheStore(data_dir / "cache" / "boss_agent.db")

	if cache.is_greeted(security_id):
		cache.close()
		emit_error(
			"greet",
			code="ALREADY_GREETED",
			message="已向该招聘者打过招呼",
			recoverable=False,
			hints={"next_actions": ["boss search <query> — 搜索其他职位"]},
		)
		return

	try:
		auth = AuthManager(data_dir, logger=logger)
		client = BossClient(auth, delay=delay)
		result = client.greet(security_id, job_id, message)

		cache.record_greet(security_id, job_id)
		cache.close()

		emit_success("greet", {
			"security_id": security_id,
			"job_id": job_id,
			"message": "打招呼成功",
		}, hints={
			"next_actions": [
				"boss search <query> — 继续搜索其他职位",
				"boss recommend — 获取个性化推荐",
			],
		})
	except AuthRequired:
		cache.close()
		emit_error(
			"greet",
			code="AUTH_REQUIRED",
			message="未登录，请先执行 boss login",
			recoverable=True,
			recovery_action="boss login",
		)
	except TokenRefreshFailed:
		cache.close()
		emit_error(
			"greet",
			code="TOKEN_REFRESH_FAILED",
			message="Token 刷新失败，请重新登录",
			recoverable=True,
			recovery_action="boss login",
		)
	except Exception as e:
		cache.close()
		emit_error(
			"greet",
			code="NETWORK_ERROR",
			message=f"打招呼失败: {e}",
			recoverable=True,
			recovery_action="重试",
		)


@click.command("batch-greet")
@click.argument("query")
@click.option("--city", default=None, help="城市名称")
@click.option("--salary", default=None, help="薪资范围")
@click.option("--count", default=10, help="打招呼数量上限（最大 10）")
@click.option("--dry-run", is_flag=True, default=False, help="仅模拟执行，不实际打招呼")
@click.pass_context
def batch_greet_cmd(ctx, query, city, salary, count, dry_run):
	"""搜索后批量打招呼（上限 10）"""
	data_dir = ctx.obj["data_dir"]
	logger = ctx.obj["logger"]
	delay = ctx.obj["delay"]

	count = min(count, 10)

	cache = CacheStore(data_dir / "cache" / "boss_agent.db")

	try:
		auth = AuthManager(data_dir, logger=logger)
		client = BossClient(auth, delay=delay)

		raw = client.search_jobs(query, city=city, salary=salary)
		zp_data = raw.get("zpData", {})
		job_list = zp_data.get("jobList", [])

		candidates = []
		for raw_item in job_list:
			item = JobItem.from_api(raw_item)
			if not cache.is_greeted(item.security_id):
				candidates.append(item)
			if len(candidates) >= count:
				break

		if dry_run:
			items = [item.to_dict() for item in candidates]
			cache.close()
			emit_success("batch-greet", {
				"dry_run": True,
				"candidates": items,
				"count": len(items),
			})
			return

		results = []
		stopped_reason = None

		for item in candidates:
			retry_count = 0
			success = False

			while retry_count <= 1:
				try:
					client.greet(item.security_id, item.job_id)
					cache.record_greet(item.security_id, item.job_id)
					results.append({
						"security_id": item.security_id,
						"job_id": item.job_id,
						"title": item.title,
						"company": item.company,
						"status": "success",
					})
					success = True
					logger.info(f"打招呼成功: {item.title} @ {item.company}")
					break
				except Exception as e:
					error_msg = str(e)
					if "RATE_LIMITED" in error_msg or "频率" in error_msg:
						stopped_reason = "RATE_LIMITED"
						break
					if "GREET_LIMIT" in error_msg or "上限" in error_msg:
						stopped_reason = "GREET_LIMIT"
						break
					if retry_count == 0:
						logger.warning(f"打招呼失败，重试中: {item.title}")
						retry_count += 1
						time.sleep(random.uniform(1.0, 2.0))
					else:
						results.append({
							"security_id": item.security_id,
							"job_id": item.job_id,
							"title": item.title,
							"company": item.company,
							"status": "failed",
							"error": error_msg,
						})
						break

			if stopped_reason:
				break

			if success and item != candidates[-1]:
				time.sleep(random.uniform(2.0, 5.0))

		cache.close()

		data = {
			"greeted": [r for r in results if r["status"] == "success"],
			"failed": [r for r in results if r["status"] == "failed"],
			"total_greeted": sum(1 for r in results if r["status"] == "success"),
			"total_failed": sum(1 for r in results if r["status"] == "failed"),
		}
		if stopped_reason:
			data["stopped_reason"] = stopped_reason

		emit_success("batch-greet", data)
	except AuthRequired:
		cache.close()
		emit_error(
			"batch-greet",
			code="AUTH_REQUIRED",
			message="未登录，请先执行 boss login",
			recoverable=True,
			recovery_action="boss login",
		)
	except TokenRefreshFailed:
		cache.close()
		emit_error(
			"batch-greet",
			code="TOKEN_REFRESH_FAILED",
			message="Token 刷新失败，请重新登录",
			recoverable=True,
			recovery_action="boss login",
		)
	except Exception as e:
		cache.close()
		emit_error(
			"batch-greet",
			code="NETWORK_ERROR",
			message=f"批量打招呼失败: {e}",
			recoverable=True,
			recovery_action="重试",
		)
