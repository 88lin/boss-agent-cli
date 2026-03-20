import click

from boss_agent_cli.api.client import BossClient
from boss_agent_cli.api.models import JobDetail
from boss_agent_cli.auth.manager import AuthManager, AuthRequired, TokenRefreshFailed
from boss_agent_cli.cache.store import CacheStore
from boss_agent_cli.output import emit_error, emit_success


@click.command("detail")
@click.argument("job_id")
@click.pass_context
def detail_cmd(ctx, job_id):
	"""查看职位完整信息"""
	data_dir = ctx.obj["data_dir"]
	logger = ctx.obj["logger"]
	delay = ctx.obj["delay"]

	try:
		auth = AuthManager(data_dir, logger=logger)
		client = BossClient(auth, delay=delay)
		raw = client.job_detail(job_id)

		zp_data = raw.get("zpData", {})
		detail = JobDetail.from_api(zp_data)

		cache = CacheStore(data_dir / "cache" / "boss_agent.db")
		detail.greeted = cache.is_greeted(detail.security_id)
		cache.close()

		hints = {
			"next_actions": [
				"使用 boss greet {} {} 向招聘者打招呼".format(detail.security_id, detail.job_id),
				"使用 boss search <query> 继续搜索其他职位",
			],
		}
		emit_success("detail", detail.to_dict(), hints=hints)
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
