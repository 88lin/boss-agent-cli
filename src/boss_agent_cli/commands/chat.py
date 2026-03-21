import click

from boss_agent_cli.api.client import BossClient
from boss_agent_cli.auth.manager import AuthManager, AuthRequired, TokenRefreshFailed
from boss_agent_cli.output import emit_error, emit_success


@click.command("chat")
@click.option("--page", default=1, type=int, help="页码")
@click.pass_context
def chat_cmd(ctx, page):
	"""查看已沟通的招聘者列表"""
	data_dir = ctx.obj["data_dir"]
	logger = ctx.obj["logger"]
	delay = ctx.obj["delay"]

	try:
		auth = AuthManager(data_dir, logger=logger)
		client = BossClient(auth, delay=delay)

		raw = client.chat_list(page=page)
		zp_data = raw.get("zpData", {})
		friend_list = zp_data.get("result", zp_data.get("friendList", []))

		items = []
		for raw_item in friend_list:
			items.append({
				"boss_name": raw_item.get("name", raw_item.get("bossName", "")),
				"boss_title": raw_item.get("title", raw_item.get("bossTitle", "")),
				"company": raw_item.get("brandName", ""),
				"job_title": raw_item.get("jobName", ""),
				"last_message": raw_item.get("lastContent", raw_item.get("lastMsg", "")),
				"update_time": raw_item.get("updateTime", ""),
				"security_id": raw_item.get("securityId", raw_item.get("encryptFriendId", "")),
			})

		pagination = {
			"page": page,
			"has_more": zp_data.get("hasMore", False),
			"total": len(items),
		}
		hints = {
			"next_actions": [
				f"使用 boss chat --page {page + 1} 查看下一页",
			],
		}
		emit_success("chat", items, pagination=pagination, hints=hints)
	except AuthRequired:
		emit_error("chat", code="AUTH_REQUIRED", message="未登录", recoverable=True, recovery_action="boss login")
	except TokenRefreshFailed:
		emit_error("chat", code="TOKEN_REFRESH_FAILED", message="Token 刷新失败", recoverable=True, recovery_action="boss login")
	except Exception as e:
		emit_error("chat", code="NETWORK_ERROR", message=f"获取聊天列表失败: {e}", recoverable=True, recovery_action="重试")
