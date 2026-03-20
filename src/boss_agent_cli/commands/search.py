import json

import click

from boss_agent_cli.api.client import BossClient
from boss_agent_cli.api.endpoints import CITY_CODES
from boss_agent_cli.api.models import JobItem
from boss_agent_cli.auth.manager import AuthManager, AuthRequired, TokenRefreshFailed
from boss_agent_cli.cache.store import CacheStore
from boss_agent_cli.output import emit_error, emit_success


@click.command("search")
@click.argument("query")
@click.option("--city", default=None, help="城市名称（如 北京、上海）")
@click.option("--salary", default=None, help="薪资范围（如 10-20K）")
@click.option("--experience", default=None, help="经验要求（如 3-5年）")
@click.option("--education", default=None, help="学历要求（如 本科）")
@click.option("--industry", default=None, help="行业类型")
@click.option("--scale", default=None, help="公司规模（如 100-499人）")
@click.option("--page", default=1, help="页码")
@click.option("--no-cache", is_flag=True, default=False, help="跳过缓存")
@click.pass_context
def search_cmd(ctx, query, city, salary, experience, education, industry, scale, page, no_cache):
	"""按关键词和筛选条件搜索职位列表"""
	data_dir = ctx.obj["data_dir"]
	logger = ctx.obj["logger"]
	delay = ctx.obj["delay"]

	if city and city not in CITY_CODES:
		emit_error(
			"search",
			code="INVALID_PARAM",
			message=f"未知城市: {city}，请使用 CITY_CODES 中的城市名",
		)
		return

	cache = CacheStore(data_dir / "cache" / "boss_agent.db")
	search_params = {
		"query": query,
		"city": city,
		"salary": salary,
		"experience": experience,
		"education": education,
		"industry": industry,
		"scale": scale,
		"page": page,
	}

	if not no_cache:
		cached = cache.get_search(search_params)
		if cached is not None:
			logger.debug("搜索命中缓存")
			result = json.loads(cached)
			emit_success("search", result["data"], pagination=result.get("pagination"), hints=result.get("hints"))
			cache.close()
			return

	try:
		auth = AuthManager(data_dir, logger=logger)
		client = BossClient(auth, delay=delay)
		raw = client.search_jobs(
			query,
			city=city,
			salary=salary,
			experience=experience,
			education=education,
			industry=industry,
			scale=scale,
			page=page,
		)

		zp_data = raw.get("zpData", {})
		job_list = zp_data.get("jobList", [])
		items = []
		for raw_item in job_list:
			item = JobItem.from_api(raw_item)
			item.greeted = cache.is_greeted(item.security_id)
			items.append(item.to_dict())

		pagination = {
			"page": page,
			"has_more": zp_data.get("hasMore", False),
			"total": zp_data.get("totalCount", len(items)),
		}
		hints = {
			"next_actions": [
				"使用 boss detail <job_id> 查看职位详情",
				"使用 boss greet <security_id> <job_id> 打招呼",
				"使用 boss search <query> --page {} 查看下一页".format(page + 1),
			],
		}

		cache_data = {"data": items, "pagination": pagination, "hints": hints}
		cache.put_search(search_params, json.dumps(cache_data, ensure_ascii=False))
		emit_success("search", items, pagination=pagination, hints=hints)
	except AuthRequired:
		emit_error(
			"search",
			code="AUTH_REQUIRED",
			message="未登录，请先执行 boss login",
			recoverable=True,
			recovery_action="boss login",
		)
	except TokenRefreshFailed:
		emit_error(
			"search",
			code="TOKEN_REFRESH_FAILED",
			message="Token 刷新失败，请重新登录",
			recoverable=True,
			recovery_action="boss login",
		)
	except Exception as e:
		emit_error(
			"search",
			code="NETWORK_ERROR",
			message=f"搜索失败: {e}",
			recoverable=True,
			recovery_action="重试",
		)
	finally:
		cache.close()
