import click

from boss_agent_cli.api.client import BossClient
from boss_agent_cli.auth.manager import AuthManager, AuthRequired, TokenRefreshFailed
from boss_agent_cli.cache.store import CacheStore
from boss_agent_cli.display import handle_error_output, handle_output, render_job_detail
from boss_agent_cli.index_cache import get_index_info, get_job_by_index


@click.command("show")
@click.argument("index", type=int)
@click.pass_context
def show_cmd(ctx, index):
	"""按编号查看搜索/推荐结果中的职位详情（如 boss show 3）"""
	data_dir = ctx.obj["data_dir"]
	logger = ctx.obj["logger"]
	delay = ctx.obj["delay"]

	# 从索引缓存获取职位信息
	job = get_job_by_index(data_dir, index)
	if job is None:
		info = get_index_info(data_dir)
		if not info["exists"]:
			handle_error_output(
				ctx, "show",
				code="INVALID_PARAM",
				message="没有缓存的搜索结果，请先执行 boss search 或 boss recommend",
			)
		else:
			handle_error_output(
				ctx, "show",
				code="INVALID_PARAM",
				message=f"编号 {index} 超出范围，当前缓存共 {info['count']} 条结果（来源: {info['source']}）",
			)
		return

	security_id = job.get("security_id", "")
	if not security_id:
		handle_error_output(
			ctx, "show",
			code="INVALID_PARAM",
			message=f"编号 {index} 的职位缺少 security_id",
		)
		return

	try:
		auth = AuthManager(data_dir, logger=logger)
		client = BossClient(auth, delay=delay)
		raw = client.job_card(security_id)

		card = raw.get("zpData", {}).get("jobCard", {})
		if not card:
			handle_error_output(
				ctx, "show",
				code="JOB_NOT_FOUND",
				message="职位不存在或已下架",
			)
			return

		job_id = card.get("encryptJobId", "")

		cache = CacheStore(data_dir / "cache" / "boss_agent.db")
		greeted = cache.is_greeted(security_id)
		cache.close()

		result = {
			"job_id": job_id,
			"title": card.get("jobName", ""),
			"company": card.get("brandName", ""),
			"salary": card.get("salaryDesc", ""),
			"city": card.get("cityName", ""),
			"experience": card.get("experienceName", ""),
			"education": card.get("degreeName", ""),
			"description": card.get("postDescription", ""),
			"address": card.get("address", ""),
			"skills": card.get("jobLabels", []),
			"boss_name": card.get("bossName", ""),
			"boss_title": card.get("bossTitle", ""),
			"boss_active": card.get("activeTimeDesc", "离线"),
			"security_id": security_id,
			"greeted": greeted,
			"index": index,
		}

		hints = {
			"next_actions": [
				f"boss greet {security_id} {job_id}",
				"boss search <query>",
			],
		}
		handle_output(ctx, "show", result, render=render_job_detail, hints=hints)
	except AuthRequired:
		handle_error_output(
			ctx, "show",
			code="AUTH_REQUIRED",
			message="未登录，请先执行 boss login",
			recoverable=True, recovery_action="boss login",
		)
	except TokenRefreshFailed:
		handle_error_output(
			ctx, "show",
			code="TOKEN_REFRESH_FAILED",
			message="Token 刷新失败，请重新登录",
			recoverable=True, recovery_action="boss login",
		)
	except Exception as e:
		handle_error_output(
			ctx, "show",
			code="NETWORK_ERROR",
			message=f"获取职位详情失败: {e}",
			recoverable=True, recovery_action="重试",
		)
