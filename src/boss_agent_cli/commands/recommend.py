import click

from boss_agent_cli.api.client import BossClient
from boss_agent_cli.api.models import JobItem
from boss_agent_cli.auth.manager import AuthManager, AuthRequired, TokenRefreshFailed
from boss_agent_cli.cache.store import CacheStore
from boss_agent_cli.index_cache import save_index
from boss_agent_cli.output import emit_error, emit_success


@click.command("recommend")
@click.option("--page", default=1, type=int, help="页码")
@click.pass_context
def recommend_cmd(ctx, page):
	"""基于简历的个性化职位推荐"""
	data_dir = ctx.obj["data_dir"]
	logger = ctx.obj["logger"]
	delay = ctx.obj["delay"]
	cdp_url = ctx.obj.get("cdp_url")

	try:
		auth = AuthManager(data_dir, logger=logger)
		client = BossClient(auth, delay=delay, cdp_url=cdp_url)
		cache = CacheStore(data_dir / "cache" / "boss_agent.db")

		raw = client.recommend_jobs(page=page)
		zp_data = raw.get("zpData", {})
		job_list = zp_data.get("jobList", [])

		items = []
		for raw_item in job_list:
			item = JobItem.from_api(raw_item)
			item.greeted = cache.is_greeted(item.security_id)
			items.append(item.to_dict())

		cache.close()

		save_index(data_dir, items, source="recommend")

		pagination = {
			"page": page,
			"has_more": zp_data.get("hasMore", False),
			"total": len(items),
		}
		hints = {
			"next_actions": [
				"使用 boss detail <security_id> 查看职位详情",
				"使用 boss greet <security_id> <job_id> 打招呼",
				f"使用 boss recommend --page {page + 1} 查看下一页",
			],
		}
		emit_success("recommend", items, pagination=pagination, hints=hints)
	except AuthRequired:
		emit_error("recommend", code="AUTH_REQUIRED", message="未登录", recoverable=True, recovery_action="boss login")
	except TokenRefreshFailed:
		emit_error("recommend", code="TOKEN_REFRESH_FAILED", message="Token 刷新失败", recoverable=True, recovery_action="boss login")
	except Exception as e:
		emit_error("recommend", code="NETWORK_ERROR", message=f"获取推荐失败: {e}", recoverable=True, recovery_action="重试")
