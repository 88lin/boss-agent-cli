import click

from boss_agent_cli.api.client import BossClient
from boss_agent_cli.auth.manager import AuthManager, AuthRequired, TokenRefreshFailed
from boss_agent_cli.display import handle_error_output, handle_output, render_simple_list


@click.command("chat")
@click.pass_context
def chat_cmd(ctx):
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
		resp = client.friend_list()
		zp_data = resp.get("zpData", {})

		# API 可能返回 result 或 friendList 字段
		items = zp_data.get("result") or zp_data.get("friendList") or []

		friends = []
		for item in items:
			friends.append({
				"name": item.get("name") or item.get("bossName", "-"),
				"brand_name": item.get("brandName", "-"),
				"job_name": item.get("jobName", "-"),
				"last_msg": item.get("lastMsg") or item.get("lastText", "-"),
			})

		def _render(data):
			render_simple_list(
				data,
				"沟通列表",
				[
					("Boss", "name", "bold cyan"),
					("公司", "brand_name", "green"),
					("职位", "job_name", "yellow"),
					("最近消息", "last_msg", "dim"),
				],
			)

		handle_output(
			ctx, "chat", friends,
			render=_render,
			hints={"next_actions": ["boss detail <security_id> — 查看职位详情"]},
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
