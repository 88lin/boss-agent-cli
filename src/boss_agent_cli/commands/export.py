import csv
import io
import json

import click

from boss_agent_cli.api.client import BossClient
from boss_agent_cli.api.models import JobItem
from boss_agent_cli.auth.manager import AuthManager, AuthRequired, TokenRefreshFailed
from boss_agent_cli.output import emit_error, emit_success


@click.command("export")
@click.argument("query")
@click.option("--city", default=None, help="城市名称")
@click.option("--salary", default=None, help="薪资范围")
@click.option("--count", default=50, type=int, help="导出数量")
@click.option("--format", "fmt", default="csv", type=click.Choice(["csv", "json"]), help="输出格式")
@click.option("--output", "-o", default=None, help="输出文件路径（不指定则输出到 stdout JSON 信封）")
@click.pass_context
def export_cmd(ctx, query, city, salary, count, fmt, output):
	"""导出搜索结果为 CSV 或 JSON 文件"""
	data_dir = ctx.obj["data_dir"]
	logger = ctx.obj["logger"]
	delay = ctx.obj["delay"]

	try:
		auth = AuthManager(data_dir, logger=logger)
		client = BossClient(auth, delay=delay)

		all_items = []
		page = 1
		max_pages = (count + 14) // 15  # 每页约 15 条

		while len(all_items) < count and page <= max_pages:
			logger.info(f"正在获取第 {page} 页...")
			raw = client.search_jobs(query, city=city, salary=salary, page=page)
			zp_data = raw.get("zpData", {})
			job_list = zp_data.get("jobList", [])
			if not job_list:
				break

			for raw_item in job_list:
				if len(all_items) >= count:
					break
				item = JobItem.from_api(raw_item)
				all_items.append(item.to_dict())

			if not zp_data.get("hasMore", False):
				break
			page += 1

		if output:
			_write_to_file(all_items, fmt, output)
			emit_success("export", {
				"message": f"已导出 {len(all_items)} 条到 {output}",
				"count": len(all_items),
				"format": fmt,
				"path": output,
			})
		else:
			emit_success("export", {
				"count": len(all_items),
				"format": fmt,
				"jobs": all_items,
			})
	except AuthRequired:
		emit_error("export", code="AUTH_REQUIRED", message="未登录", recoverable=True, recovery_action="boss login")
	except TokenRefreshFailed:
		emit_error("export", code="TOKEN_REFRESH_FAILED", message="Token 刷新失败", recoverable=True, recovery_action="boss login")
	except Exception as e:
		emit_error("export", code="NETWORK_ERROR", message=f"导出失败: {e}", recoverable=True, recovery_action="重试")


def _write_to_file(items: list[dict], fmt: str, path: str):
	if fmt == "json":
		with open(path, "w", encoding="utf-8") as f:
			json.dump(items, f, ensure_ascii=False, indent=2)
	elif fmt == "csv":
		if not items:
			with open(path, "w") as f:
				f.write("")
			return
		fields = ["title", "company", "salary", "city", "district", "experience",
				"education", "skills", "welfare", "industry", "scale", "boss_name",
				"boss_title", "job_id", "security_id"]
		with open(path, "w", encoding="utf-8", newline="") as f:
			writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
			writer.writeheader()
			for item in items:
				row = dict(item)
				if isinstance(row.get("skills"), list):
					row["skills"] = ", ".join(row["skills"])
				if isinstance(row.get("welfare"), list):
					row["welfare"] = ", ".join(row["welfare"])
				writer.writerow(row)
