import click

from boss_agent_cli.auth.manager import AuthManager
from boss_agent_cli.output import emit_error, emit_success


@click.command("login")
@click.option("--timeout", default=120, help="扫码登录超时时间（秒）")
@click.option("--cookie-source", default=None, help="指定浏览器提取 Cookie（如 chrome/firefox/edge），不指定则自动检测")
@click.pass_context
def login_cmd(ctx, timeout, cookie_source):
	"""登录 BOSS 直聘（优先从浏览器提取 Cookie，失败则扫码）"""
	data_dir = ctx.obj["data_dir"]
	logger = ctx.obj["logger"]
	auth = AuthManager(data_dir, logger=logger)
	try:
		token = auth.login(timeout=timeout, cookie_source=cookie_source)
		method = "Cookie 提取" if not token.get("stoken") and token.get("cookies") else "扫码登录"
		emit_success("login", {"message": f"登录成功（{method}）"}, hints={
			"next_actions": [
				"boss status — 验证登录态",
				"boss search <query> — 搜索职位",
				"boss recommend — 获取个性化推荐",
			],
		})
	except Exception as e:
		emit_error(
			"login",
			code="NETWORK_ERROR",
			message=f"登录失败: {e}",
			recoverable=True,
			recovery_action="boss login",
		)
