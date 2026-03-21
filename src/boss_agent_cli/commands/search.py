import json

import click

from boss_agent_cli.api.client import BossClient
from boss_agent_cli.api.endpoints import CITY_CODES
from boss_agent_cli.api.models import JobItem
from boss_agent_cli.auth.manager import AuthManager, AuthRequired, TokenRefreshFailed
from boss_agent_cli.cache.store import CacheStore
from boss_agent_cli.output import emit_error, emit_success

# 福利关键词分组：用户输入 -> 在 welfareList 和 postDescription 中匹配的关键词
_WELFARE_KEYWORDS = {
	"双休": ["双休", "周末双休", "五天工作制", "5天工作制"],
	"五险一金": ["五险一金"],
	"五险": ["五险一金", "五险"],
	"年终奖": ["年终奖"],
	"带薪年假": ["带薪年假"],
	"餐补": ["餐补", "包吃", "免费午餐"],
	"住房补贴": ["住房补贴", "住房补助"],
	"定期体检": ["定期体检"],
	"股票期权": ["股票期权"],
	"加班补助": ["加班补助"],
}

_MAX_FILTER_PAGES = 5  # 福利筛选时最多翻页数


def _match_welfare(keywords: list[str], welfare_list: list[str], description: str) -> bool:
	"""检查福利标签或职位描述中是否包含任一关键词"""
	text = " ".join(welfare_list) + " " + description
	return any(kw in text for kw in keywords)


@click.command("search")
@click.argument("query")
@click.option("--city", default=None, help="城市名称（如 北京、上海）")
@click.option("--salary", default=None, help="薪资范围（如 10-20K）")
@click.option("--experience", default=None, help="经验要求（如 3-5年）")
@click.option("--education", default=None, help="学历要求（如 本科）")
@click.option("--industry", default=None, help="行业类型")
@click.option("--scale", default=None, help="公司规模（如 100-499人）")
@click.option("--welfare", default=None, help="福利筛选（如 双休、五险一金），会逐个检查职位详情")
@click.option("--page", default=1, help="页码")
@click.option("--no-cache", is_flag=True, default=False, help="跳过缓存")
@click.pass_context
def search_cmd(ctx, query, city, salary, experience, education, industry, scale, welfare, page, no_cache):
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

	# 解析福利关键词
	welfare_keywords = None
	if welfare:
		welfare_keywords = _WELFARE_KEYWORDS.get(welfare)
		if welfare_keywords is None:
			# 用户输入的不在预设映射中，直接作为关键词使用
			welfare_keywords = [welfare]

	cache = CacheStore(data_dir / "cache" / "boss_agent.db")

	# 有福利筛选时跳过缓存（因为需要逐个查详情）
	if not welfare_keywords and not no_cache:
		search_params = {
			"query": query, "city": city, "salary": salary,
			"experience": experience, "education": education,
			"industry": industry, "scale": scale, "page": page,
		}
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

		if welfare_keywords:
			# 福利筛选模式：逐页搜索 + 逐个检查详情
			items = _search_with_welfare_filter(
				client, cache, logger, query,
				welfare_keywords=welfare_keywords,
				welfare_label=welfare,
				city=city, salary=salary, experience=experience,
				education=education, industry=industry, scale=scale,
				start_page=page,
			)
			pagination = {"page": 1, "has_more": False, "total": len(items)}
			hints = {
				"next_actions": [
					"使用 boss detail <job_id> 查看职位详情",
					"使用 boss greet <security_id> <job_id> 打招呼",
				],
			}
			emit_success("search", items, pagination=pagination, hints=hints)
		else:
			# 普通搜索模式
			raw = client.search_jobs(
				query, city=city, salary=salary, experience=experience,
				education=education, industry=industry, scale=scale, page=page,
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
			search_params = {
				"query": query, "city": city, "salary": salary,
				"experience": experience, "education": education,
				"industry": industry, "scale": scale, "page": page,
			}
			cache_data = {"data": items, "pagination": pagination, "hints": hints}
			cache.put_search(search_params, json.dumps(cache_data, ensure_ascii=False))
			emit_success("search", items, pagination=pagination, hints=hints)
	except AuthRequired:
		emit_error(
			"search", code="AUTH_REQUIRED",
			message="未登录，请先执行 boss login",
			recoverable=True, recovery_action="boss login",
		)
	except TokenRefreshFailed:
		emit_error(
			"search", code="TOKEN_REFRESH_FAILED",
			message="Token 刷新失败，请重新登录",
			recoverable=True, recovery_action="boss login",
		)
	except Exception as e:
		emit_error(
			"search", code="NETWORK_ERROR",
			message=f"搜索失败: {e}",
			recoverable=True, recovery_action="重试",
		)
	finally:
		cache.close()


def _search_with_welfare_filter(
	client: BossClient,
	cache: CacheStore,
	logger,
	query: str,
	*,
	welfare_keywords: list[str],
	welfare_label: str,
	city=None, salary=None, experience=None,
	education=None, industry=None, scale=None,
	start_page: int = 1,
) -> list[dict]:
	"""逐页搜索，对每个职位先检查福利标签，不匹配再查详情描述"""
	matched = []
	current_page = start_page

	for _ in range(_MAX_FILTER_PAGES):
		logger.info(f"正在搜索第 {current_page} 页...")
		raw = client.search_jobs(
			query, city=city, salary=salary, experience=experience,
			education=education, industry=industry, scale=scale,
			page=current_page,
		)
		zp_data = raw.get("zpData", {})
		job_list = zp_data.get("jobList", [])
		if not job_list:
			break

		for raw_item in job_list:
			welfare_list = raw_item.get("welfareList", [])
			# 第一步：检查福利标签（无需额外请求）
			if _match_welfare(welfare_keywords, welfare_list, ""):
				item = JobItem.from_api(raw_item)
				item.greeted = cache.is_greeted(item.security_id)
				d = item.to_dict()
				d["welfare_match"] = f"✅ {welfare_label}（福利标签）"
				matched.append(d)
				logger.info(f"  ✅ {item.company} - {item.title}（标签匹配）")
				continue

			# 第二步：查职位卡片详情中的描述
			try:
				card_raw = client.job_card(
					raw_item.get("securityId", ""),
					raw_item.get("lid", ""),
				)
				desc = card_raw.get("zpData", {}).get("jobCard", {}).get("postDescription", "")
			except Exception:
				desc = ""

			if _match_welfare(welfare_keywords, welfare_list, desc):
				item = JobItem.from_api(raw_item)
				item.greeted = cache.is_greeted(item.security_id)
				d = item.to_dict()
				d["welfare_match"] = f"✅ {welfare_label}（描述提及）"
				matched.append(d)
				logger.info(f"  ✅ {item.company} - {item.title}（描述匹配）")
			else:
				title = raw_item.get("jobName", "")
				company = raw_item.get("brandName", "")
				logger.info(f"  ❌ {company} - {title}（不匹配）")

		has_more = zp_data.get("hasMore", False)
		if not has_more:
			break
		current_page += 1

	return matched
