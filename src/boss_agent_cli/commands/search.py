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


def _resolve_welfare_keywords(label: str) -> list[str]:
	"""将单个福利标签解析为匹配关键词列表"""
	return _WELFARE_KEYWORDS.get(label, [label])


def _check_welfare_in_text(keywords: list[str], text: str) -> bool:
	"""检查文本中是否包含任一关键词"""
	return any(kw in text for kw in keywords)


def _match_all_welfare(
	conditions: list[tuple[str, list[str]]],
	welfare_list: list[str],
	description: str,
) -> list[str]:
	"""
	检查所有福利条件是否都满足（AND 逻辑）。
	返回每个条件的匹配结果列表，全部匹配返回非空列表，否则返回空列表。
	"""
	text = " ".join(welfare_list)
	full_text = text + " " + description
	results = []
	for label, keywords in conditions:
		if _check_welfare_in_text(keywords, text):
			results.append(f"{label}(标签)")
		elif description and _check_welfare_in_text(keywords, full_text):
			results.append(f"{label}(描述)")
		else:
			return []  # 任一条件不满足，直接返回空
	return results


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

	# 解析福利关键词（支持逗号分隔的多条件组合）
	welfare_conditions = None
	if welfare:
		labels = [w.strip() for w in welfare.split(",") if w.strip()]
		welfare_conditions = [(label, _resolve_welfare_keywords(label)) for label in labels]

	cache = CacheStore(data_dir / "cache" / "boss_agent.db")

	# 有福利筛选时跳过缓存（因为需要逐个查详情）
	if not welfare_conditions and not no_cache:
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

		if welfare_conditions:
			# 福利筛选模式：逐页搜索 + 逐个检查详情
			items = _search_with_welfare_filter(
				client, cache, logger, query,
				welfare_conditions=welfare_conditions,
				city=city, salary=salary, experience=experience,
				education=education, industry=industry, scale=scale,
				start_page=page,
			)
			pagination = {"page": 1, "has_more": False, "total": len(items)}
			hints = {
				"next_actions": [
					"使用 boss detail <security_id> 查看职位详情",
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
					"使用 boss detail <security_id> 查看职位详情",
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
	welfare_conditions: list[tuple[str, list[str]]],
	city=None, salary=None, experience=None,
	education=None, industry=None, scale=None,
	start_page: int = 1,
) -> list[dict]:
	"""逐页搜索，对每个职位检查所有福利条件是否同时满足（AND 逻辑）"""
	matched = []
	current_page = start_page
	condition_labels = [c[0] for c in welfare_conditions]
	label_str = "+".join(condition_labels)

	for _ in range(_MAX_FILTER_PAGES):
		logger.info(f"正在搜索第 {current_page} 页（筛选: {label_str}）...")
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
			company = raw_item.get("brandName", "")
			title = raw_item.get("jobName", "")

			# 第一步：仅用福利标签检查
			match_results = _match_all_welfare(welfare_conditions, welfare_list, "")
			if match_results:
				item = JobItem.from_api(raw_item)
				item.greeted = cache.is_greeted(item.security_id)
				d = item.to_dict()
				d["welfare_match"] = "✅ " + ", ".join(match_results)
				matched.append(d)
				logger.info(f"  ✅ {company} - {title}（标签匹配）")
				continue

			# 第二步：标签不够，查详情描述补充判断
			try:
				card_raw = client.job_card(
					raw_item.get("securityId", ""),
					raw_item.get("lid", ""),
				)
				desc = card_raw.get("zpData", {}).get("jobCard", {}).get("postDescription", "")
			except Exception:
				desc = ""

			match_results = _match_all_welfare(welfare_conditions, welfare_list, desc)
			if match_results:
				item = JobItem.from_api(raw_item)
				item.greeted = cache.is_greeted(item.security_id)
				d = item.to_dict()
				d["welfare_match"] = "✅ " + ", ".join(match_results)
				matched.append(d)
				logger.info(f"  ✅ {company} - {title}（详情匹配）")
			else:
				logger.info(f"  ❌ {company} - {title}")

		has_more = zp_data.get("hasMore", False)
		if not has_more:
			break
		current_page += 1

	return matched
