"""搜索结果索引缓存，支持 boss show N 快速导航。
缓存文件: ~/.boss-agent/cache/index_cache.json
"""
import json
import time
from pathlib import Path

_CACHE_FILE = "index_cache.json"


def _cache_path(data_dir: Path) -> Path:
	return data_dir / "cache" / _CACHE_FILE


def save_index(data_dir: Path, jobs: list[dict], source: str = "search") -> None:
	"""保存搜索/推荐结果到索引缓存。"""
	entries = []
	for job in jobs:
		entries.append({
			"security_id": job.get("security_id", ""),
			"job_id": job.get("job_id", ""),
			"title": job.get("title", ""),
			"company": job.get("company", ""),
			"salary": job.get("salary", ""),
			"city": job.get("city", ""),
			"experience": job.get("experience", ""),
			"education": job.get("education", ""),
			"skills": job.get("skills", []),
		})

	cache_data = {
		"source": source,
		"count": len(entries),
		"saved_at": time.time(),
		"jobs": entries,
	}

	path = _cache_path(data_dir)
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(json.dumps(cache_data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_job_by_index(data_dir: Path, index: int) -> dict | None:
	"""按 1-based 编号获取缓存的职位信息。"""
	path = _cache_path(data_dir)
	if not path.exists():
		return None

	try:
		cache_data = json.loads(path.read_text(encoding="utf-8"))
	except (json.JSONDecodeError, OSError):
		return None

	jobs = cache_data.get("jobs", [])
	if index < 1 or index > len(jobs):
		return None

	return jobs[index - 1]


def get_index_info(data_dir: Path) -> dict:
	"""获取缓存元信息（来源、数量、保存时间）。"""
	path = _cache_path(data_dir)
	if not path.exists():
		return {"exists": False, "source": "", "count": 0, "saved_at": 0}

	try:
		cache_data = json.loads(path.read_text(encoding="utf-8"))
	except (json.JSONDecodeError, OSError):
		return {"exists": False, "source": "", "count": 0, "saved_at": 0}

	return {
		"exists": True,
		"source": cache_data.get("source", ""),
		"count": cache_data.get("count", 0),
		"saved_at": cache_data.get("saved_at", 0),
	}
