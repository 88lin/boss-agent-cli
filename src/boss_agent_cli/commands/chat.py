import time

import click

from boss_agent_cli.api.client import BossClient
from boss_agent_cli.auth.manager import AuthManager, AuthRequired, TokenRefreshFailed
from boss_agent_cli.display import handle_error_output, handle_output, render_simple_list


@click.command("chat")
@click.option("--page", default=1, help="页码")
@click.pass_context
def chat_cmd(ctx, page):
	"""查看沟通列表（已打招呼的 Boss）"""
	data_dir = ctx.obj["data_dir"]
	logger = ctx.obj["logger"]
	delay = ctx.obj["delay"]
	auth = AuthManager(data_dir, logger=logger)

	token = auth.check_status()
	if token is None:
		handle_error_output(
			ctx, "chat",
			code="AUTH_REQUIRED",
			message="未登录，请先执行 boss login",
			recoverable=True, recovery_action="boss login",
		)
		return

	try:
		client = BossClient(auth, delay=delay)
		resp = client.friend_list(page=page)
		zp_data = resp.get("zpData", {})
		items = zp_data.get("result") or zp_data.get("friendList") or []

		friends = []
		for item in items:
			last_ts = item.get("lastTS", 0)
			if last_ts:
				last_time_str = _format_ts(last_ts)
			else:
				last_time_str = item.get("lastTime", "-")

			friends.append({
				"name": item.get("name", "-"),
				"title": item.get("title", "-"),
				"brand_name": item.get("brandName", "-"),
				"last_msg": item.get("lastMsg", "-"),
				"last_time": last_time_str,
				"security_id": item.get("securityId", ""),
				"encrypt_job_id": item.get("encryptJobId", ""),
				"unread": item.get("unreadMsgCount", 0),
			})

		def _render(data):
			render_simple_list(
				data,
				"沟通列表",
				[
					("Boss", "name", "bold cyan"),
					("职称", "title", "dim"),
					("公司", "brand_name", "green"),
					("最近消息", "last_msg", "yellow"),
					("时间", "last_time", "dim"),
				],
			)

		handle_output(
			ctx, "chat", friends,
			render=_render,
			hints={"next_actions": [
				"boss detail <security_id> — 查看职位详情",
				"boss greet <security_id> <job_id> — 打招呼",
			]},
		)
	except AuthRequired:
		handle_error_output(
			ctx, "chat",
			code="AUTH_REQUIRED",
			message="登录态已失效，请重新登录",
			recoverable=True, recovery_action="boss login",
		)
	except TokenRefreshFailed:
		handle_error_output(
			ctx, "chat",
			code="TOKEN_REFRESH_FAILED",
			message="Token 刷新失败，请重新登录",
			recoverable=True, recovery_action="boss login",
		)
	except Exception as e:
		handle_error_output(
			ctx, "chat",
			code="NETWORK_ERROR",
			message=f"获取沟通列表失败: {e}",
			recoverable=True, recovery_action="重试",
		)


def _format_ts(ts_ms: int) -> str:
	"""将毫秒时间戳格式化为可读日期"""
	import datetime
	dt = datetime.datetime.fromtimestamp(ts_ms / 1000)
	now = datetime.datetime.now()
	if dt.date() == now.date():
		return dt.strftime("今天 %H:%M")
	delta = (now.date() - dt.date()).days
	if delta == 1:
		return dt.strftime("昨天 %H:%M")
	if delta < 7:
		return f"{delta}天前"
	return dt.strftime("%m-%d %H:%M")
