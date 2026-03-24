import datetime
import time

import click

from boss_agent_cli.api.client import BossClient
from boss_agent_cli.auth.manager import AuthManager, AuthRequired, TokenRefreshFailed
from boss_agent_cli.display import handle_error_output, handle_output, render_simple_list

# relationType 映射：API 返回值 → 可读标签
_RELATION_LABELS = {1: "对方主动", 2: "我主动", 3: "投递"}
_FROM_FILTER = {"boss": 1, "me": 2}
_MSG_STATUS_LABELS = {1: "未读", 2: "已读"}


@click.command("chat")
@click.option("--page", default=1, help="页码")
@click.option("--from", "from_who", default=None, type=click.Choice(["boss", "me"]),
	help="筛选发起方：boss=对方主动联系 / me=我主动打招呼")
@click.option("--days", default=None, type=int, help="只显示最近 N 天的记录")
@click.pass_context
def chat_cmd(ctx, page, from_who, days):
	"""查看沟通列表（支持按发起方和时间筛选）"""
	data_dir = ctx.obj["data_dir"]
	logger = ctx.obj["logger"]
	delay = ctx.obj["delay"]
	cdp_url = ctx.obj.get("cdp_url")
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
		client = BossClient(auth, delay=delay, cdp_url=cdp_url)
		resp = client.friend_list(page=page)
		zp_data = resp.get("zpData", {})
		items = zp_data.get("result") or zp_data.get("friendList") or []

		# 时间筛选阈值
		cutoff_ts = None
		if days is not None:
			cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
			cutoff_ts = cutoff.timestamp() * 1000

		# 发起方筛选值
		relation_filter = _FROM_FILTER.get(from_who) if from_who else None

		friends = []
		for item in items:
			# 时间筛选
			last_ts = item.get("lastTS", 0)
			if cutoff_ts and last_ts and last_ts < cutoff_ts:
				continue

			# 发起方筛选
			relation_type = item.get("relationType")
			if relation_filter is not None and relation_type != relation_filter:
				continue

			if last_ts:
				last_time_str = _format_ts(last_ts)
			else:
				last_time_str = item.get("lastTime", "-")

			friends.append({
				"name": item.get("name", "-"),
				"title": item.get("title", "-"),
				"brand_name": item.get("brandName", "-"),
				"initiated_by": _RELATION_LABELS.get(relation_type, "未知"),
				"last_msg": item.get("lastMsg", "-"),
				"last_time": last_time_str,
				"msg_status": _MSG_STATUS_LABELS.get(
					item.get("lastMessageInfo", {}).get("status"), "未知"
				),
				"security_id": item.get("securityId", ""),
				"encrypt_job_id": item.get("encryptJobId", ""),
				"unread": item.get("unreadMsgCount", 0),
			})

		# 根据筛选条件动态调整标题
		title = "沟通列表"
		if from_who == "boss":
			title = "对方主动联系"
		elif from_who == "me":
			title = "我主动打招呼"
		if days is not None:
			title += f"（最近 {days} 天）"

		def _render(data):
			render_simple_list(
				data,
				title,
				[
					("Boss", "name", "bold cyan"),
					("职称", "title", "dim"),
					("公司", "brand_name", "green"),
					("发起方", "initiated_by", "magenta"),
					("已读", "msg_status", "dim"),
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
