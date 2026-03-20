import click

from boss_agent_cli.auth.manager import AuthManager
from boss_agent_cli.output import emit_error, emit_success


@click.command("login")
@click.option("--timeout", default=120, help="登录超时时间（秒）")
@click.pass_context
def login_cmd(ctx, timeout):
	"""启动浏览器扫码登录 BOSS 直聘"""
	data_dir = ctx.obj["data_dir"]
	logger = ctx.obj["logger"]
	auth = AuthManager(data_dir, logger=logger)
	try:
		auth.login(timeout=timeout)
		emit_success("login", {"message": "登录成功"})
	except Exception as e:
		emit_error(
			"login",
			code="NETWORK_ERROR",
			message=f"登录失败: {e}",
			recoverable=True,
			recovery_action="重试 boss login",
		)
