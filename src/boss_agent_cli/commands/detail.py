import click

from boss_agent_cli.api.client import BossClient
from boss_agent_cli.auth.manager import AuthManager, AuthRequired, TokenRefreshFailed
from boss_agent_cli.cache.store import CacheStore
from boss_agent_cli.display import handle_error_output, handle_output, render_job_detail


@click.command("detail")
@click.argument("security_id")
@click.option("--lid", default="", help="列表项 ID（从 search 结果获取，可选）")
@click.option("--job-id", default="", help="职位加密 ID（提供时走 httpx 快速通道，跳过浏览器）")
@click.pass_context
def detail_cmd(ctx, security_id, lid, job_id):
	"""查看职位完整信息（职位描述、地址、招聘者信息）"""
	data_dir = ctx.obj["data_dir"]
	logger = ctx.obj["logger"]
	delay = ctx.obj["delay"]
	cdp_url = ctx.obj.get("cdp_url")

	try:
		auth = AuthManager(data_dir, logger=logger)
		client = BossClient(auth, delay=delay, cdp_url=cdp_url)

		# 优先走 httpx 快速通道：显式传入 > 缓存查找 > 降级浏览器通道
		if not job_id:
			cache = CacheStore(data_dir / "cache" / "boss_agent.db")
			job_id = cache.get_job_id(security_id) or ""
			cache.close()
			if job_id:
				logger.info(f"从缓存命中 job_id，走 httpx 快速通道")

		if job_id:
			result = _detail_via_httpx(client, security_id, job_id, data_dir)
		else:
			result = _detail_via_browser(client, security_id, lid, data_dir)

		if result is None:
			handle_error_output(
				ctx, "detail",
				code="JOB_NOT_FOUND",
				message="职位不存在或已下架",
			)
			return

		greet_target = f"boss greet {security_id} {result['job_id']}"
		hints = {"next_actions": [greet_target, "boss search <query>"]}
		handle_output(ctx, "detail", result, render=render_job_detail, hints=hints)
	except AuthRequired:
		handle_error_output(
			ctx, "detail",
			code="AUTH_REQUIRED",
			message="未登录，请先执行 boss login",
			recoverable=True, recovery_action="boss login",
		)
	except TokenRefreshFailed:
		handle_error_output(
			ctx, "detail",
			code="TOKEN_REFRESH_FAILED",
			message="Token 刷新失败，请重新登录",
			recoverable=True, recovery_action="boss login",
		)
	except Exception as e:
		handle_error_output(
			ctx, "detail",
			code="NETWORK_ERROR",
			message=f"获取职位详情失败: {e}",
			recoverable=True, recovery_action="重试",
		)


def _detail_via_httpx(client, security_id, job_id, data_dir):
	"""快速通道：通过 httpx 获取职位详情（不需要浏览器）"""
	raw = client.job_detail(job_id)
	zp = raw.get("zpData", {})
	job_info = zp.get("jobInfo", {})
	boss_info = zp.get("bossInfo", {})
	brand_info = zp.get("brandComInfo", {})

	if not job_info:
		return None

	cache = CacheStore(data_dir / "cache" / "boss_agent.db")
	greeted = cache.is_greeted(security_id)
	cache.close()

	return {
		"job_id": job_id,
		"title": job_info.get("jobName", ""),
		"company": brand_info.get("brandName", ""),
		"salary": job_info.get("salaryDesc", ""),
		"city": job_info.get("cityName", ""),
		"experience": job_info.get("experienceName", ""),
		"education": job_info.get("degreeName", ""),
		"description": zp.get("jobDetail", "") or job_info.get("postDescription", ""),
		"address": job_info.get("address", ""),
		"skills": job_info.get("jobLabels", []) or job_info.get("skills", []),
		"boss_name": boss_info.get("name", ""),
		"boss_title": boss_info.get("title", ""),
		"boss_active": boss_info.get("activeTimeDesc", "离线"),
		"security_id": security_id,
		"greeted": greeted,
	}


def _detail_via_browser(client, security_id, lid, data_dir):
	"""兜底通道：通过浏览器 job_card 获取职位详情"""
	raw = client.job_card(security_id, lid)
	card = raw.get("zpData", {}).get("jobCard", {})
	if not card:
		return None

	job_id = card.get("encryptJobId", "")

	cache = CacheStore(data_dir / "cache" / "boss_agent.db")
	greeted = cache.is_greeted(security_id)
	cache.close()

	return {
		"job_id": job_id,
		"title": card.get("jobName", ""),
		"company": card.get("brandName", ""),
		"salary": card.get("salaryDesc", ""),
		"city": card.get("cityName", ""),
		"experience": card.get("experienceName", ""),
		"education": card.get("degreeName", ""),
		"description": card.get("postDescription", ""),
		"address": card.get("address", ""),
		"skills": card.get("jobLabels", []),
		"boss_name": card.get("bossName", ""),
		"boss_title": card.get("bossTitle", ""),
		"boss_active": card.get("activeTimeDesc", "离线"),
		"security_id": security_id,
		"greeted": greeted,
	}
