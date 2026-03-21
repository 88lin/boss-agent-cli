import click

from boss_agent_cli.api.client import BossClient
from boss_agent_cli.auth.manager import AuthManager, AuthRequired, TokenRefreshFailed
from boss_agent_cli.output import emit_error, emit_success


@click.command("applied")
@click.option("--page", default=1, type=int, help="页码")
@click.pass_context
def applied_cmd(ctx, page):
	"""查看已投递的职位列表"""
	data_dir = ctx.obj["data_dir"]
	logger = ctx.obj["logger"]
	delay = ctx.obj["delay"]

	try:
		auth = AuthManager(data_dir, logger=logger)
		client = BossClient(auth, delay=delay)

		raw = client.applied_list(page=page)
		zp_data = raw.get("zpData", {})
		job_list = zp_data.get("list", zp_data.get("jobList", []))

		items = []
		for raw_item in job_list:
			items.append({
				"job_id": raw_item.get("encryptJobId", ""),
				"title": raw_item.get("jobName", ""),
				"company": raw_item.get("brandName", ""),
				"salary": raw_item.get("salaryDesc", ""),
				"city": raw_item.get("cityName", ""),
				"status": raw_item.get("friendStatus", 0),
				"applied_time": raw_item.get("addTime", ""),
			})

		pagination = {
			"page": page,
			"has_more": zp_data.get("hasMore", False),
			"total": len(items),
		}
		hints = {
			"next_actions": [
				f"使用 boss applied --page {page + 1} 查看下一页",
			],
		}
		emit_success("applied", items, pagination=pagination, hints=hints)
	except AuthRequired:
		emit_error("applied", code="AUTH_REQUIRED", message="未登录", recoverable=True, recovery_action="boss login")
	except TokenRefreshFailed:
		emit_error("applied", code="TOKEN_REFRESH_FAILED", message="Token 刷新失败", recoverable=True, recovery_action="boss login")
	except Exception as e:
		emit_error("applied", code="NETWORK_ERROR", message=f"获取已投递列表失败: {e}", recoverable=True, recovery_action="重试")
