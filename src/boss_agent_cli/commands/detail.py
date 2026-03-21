import click

from boss_agent_cli.api.client import BossClient
from boss_agent_cli.auth.manager import AuthManager, AuthRequired, TokenRefreshFailed
from boss_agent_cli.cache.store import CacheStore
from boss_agent_cli.output import emit_error, emit_success


@click.command("detail")
@click.argument("security_id")
@click.option("--lid", default="", help="列表项 ID（从 search 结果获取，可选）")
@click.pass_context
def detail_cmd(ctx, security_id, lid):
	"""查看职位完整信息（职位描述、地址、招聘者信息）"""
	data_dir = ctx.obj["data_dir"]
	logger = ctx.obj["logger"]
	delay = ctx.obj["delay"]

	try:
		auth = AuthManager(data_dir, logger=logger)
		client = BossClient(auth, delay=delay)
		raw = client.job_card(security_id, lid)

		card = raw.get("zpData", {}).get("jobCard", {})
		if not card:
			emit_error(
				"detail",
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
		}

		hints = {
			"next_actions": [
				f"boss greet {security_id} {job_id} — 向招聘者打招呼",
				"boss search <query> — 继续搜索其他职位",
			],
		}
		emit_success("detail", result, hints=hints)
	except AuthRequired:
		emit_error(
			"detail",
			code="AUTH_REQUIRED",
			message="未登录，请先执行 boss login",
			recoverable=True,
			recovery_action="boss login",
		)
	except TokenRefreshFailed:
		emit_error(
			"detail",
			code="TOKEN_REFRESH_FAILED",
			message="Token 刷新失败，请重新登录",
			recoverable=True,
			recovery_action="boss login",
		)
	except Exception as e:
		emit_error(
			"detail",
			code="NETWORK_ERROR",
			message=f"获取职位详情失败: {e}",
			recoverable=True,
			recovery_action="重试",
		)
