import click

from boss_agent_cli.api.client import BossClient
from boss_agent_cli.auth.manager import AuthManager, AuthRequired, TokenRefreshFailed
from boss_agent_cli.display import handle_error_output, handle_output, render_simple_list


@click.command("interviews")
@click.pass_context
def interviews_cmd(ctx):
	"""查看面试邀请列表"""
	data_dir = ctx.obj["data_dir"]
	logger = ctx.obj["logger"]
	delay = ctx.obj["delay"]
	cdp_url = ctx.obj.get("cdp_url")
	auth = AuthManager(data_dir, logger=logger)

	token = auth.check_status()
	if token is None:
		handle_error_output(
			ctx, "interviews",
			code="AUTH_REQUIRED",
			message="未登录，请先执行 boss login",
			recoverable=True, recovery_action="boss login",
		)
		return

	try:
		client = BossClient(auth, delay=delay, cdp_url=cdp_url)
		raw = client.interview_data()
		interview_list = raw.get("zpData", {}).get("interviewList", [])

		items = [
			{
				"jobName": it.get("jobName", "-"),
				"brandName": it.get("brandName", "-"),
				"interviewTime": it.get("interviewTime", "-"),
				"address": it.get("address", "-"),
				"statusDesc": it.get("statusDesc", "-"),
			}
			for it in interview_list
		]

		def _render(data):
			render_simple_list(
				data,
				"interviews",
				columns=[
					("job", "jobName", "bold cyan"),
					("company", "brandName", "green"),
					("time", "interviewTime", "yellow"),
					("address", "address", ""),
					("status", "statusDesc", "blue"),
				],
			)

		handle_output(
			ctx, "interviews", items,
			render=_render,
			hints={"next_actions": ["boss detail <job_id>"]},
		)
	except AuthRequired:
		handle_error_output(
			ctx, "interviews",
			code="AUTH_REQUIRED",
			message="登录态已失效，请重新登录",
			recoverable=True, recovery_action="boss login",
		)
	except TokenRefreshFailed:
		handle_error_output(
			ctx, "interviews",
			code="TOKEN_REFRESH_FAILED",
			message="Token 刷新失败，请重新登录",
			recoverable=True, recovery_action="boss login",
		)
	except Exception as e:
		handle_error_output(
			ctx, "interviews",
			code="NETWORK_ERROR",
			message=f"获取面试邀请失败: {e}",
			recoverable=True, recovery_action="重试",
		)
