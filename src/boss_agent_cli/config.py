import json
import math
from pathlib import Path
from typing import Any

DEFAULTS: dict[str, Any] = {
	"request_delay": [1.5, 3.0],
	"request_budget_dir": None,
	"request_max_per_minute": 20,
	"request_wait_timeout": 30.0,
	"batch_greet_delay": [2.0, 5.0],
	"log_level": "error",
	"cdp_url": None,
	"browser_source": "auto",
	"export_dir": None,
	"platform": "zhipin",
	"role": "candidate",
	"operating_mode": "assisted",
	"low_risk_mode": True,
	"automation": {
		"mode": "autonomous",
		"platforms": ["zhipin"],
		"allowed_actions": [
			"scan_conversations",
			"read_candidate_profile",
			"send_questionnaire",
			"send_follow_up",
			"exchange_contact",
			"create_interview_lead",
		],
		"human_review_threshold": 0.65,
		"auto_execute_threshold": 0.82,
	},
	"crawl": {
		"chrome_path": None,
		"cdp_port": None,
		"hook_profile": "none",
		"hook_dir": None,
		"max_requests": 20,
		"max_details": 50,
		"max_seconds": 600,
		"max_retries": 1,
	},
}


def validate_request_config(cfg: dict[str, Any]) -> None:
	"""Validate local pacing limits before they reach a transport or persistence."""
	for key in ("request_delay", "batch_greet_delay"):
		value = cfg.get(key, DEFAULTS[key])
		if (
			not isinstance(value, (list, tuple))
			or len(value) != 2
			or not all(
				isinstance(item, (int, float)) and not isinstance(item, bool) and math.isfinite(item) for item in value
			)
			or not 0 <= value[0] <= value[1]
		):
			raise ValueError(f"{key} 必须包含两个有限数值，且满足 0 <= 下限 <= 上限")
	limit = cfg.get("request_max_per_minute", DEFAULTS["request_max_per_minute"])
	if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
		raise ValueError("request_max_per_minute 必须是正整数")
	seconds = cfg.get("request_wait_timeout", DEFAULTS["request_wait_timeout"])
	if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or seconds <= 0:
		raise ValueError("request_wait_timeout 必须是有限正数")
	directory = cfg.get("request_budget_dir")
	if directory is not None and (
		not isinstance(directory, str) or not directory.strip() or not Path(directory).expanduser().is_absolute()
	):
		raise ValueError("request_budget_dir 必须是非空绝对路径或 null")


def load_config(config_path: Path | None) -> dict[str, Any]:
	cfg = dict(DEFAULTS)
	user_cfg: dict[str, Any] = {}
	if config_path and config_path.exists():
		with open(config_path, encoding="utf-8") as f:
			user_cfg = json.load(f)
		if not isinstance(user_cfg, dict):
			raise ValueError("config.json 必须是 JSON 对象")
		cfg.update(user_cfg)
	mode = user_cfg.get("operating_mode")
	if mode not in {"assisted", "research"}:
		if "low_risk_mode" in user_cfg:
			mode = "research" if user_cfg["low_risk_mode"] is False else "assisted"
		else:
			mode = DEFAULTS.get("operating_mode", "assisted")
	if mode not in {"assisted", "research"}:
		mode = "assisted"
	cfg["operating_mode"] = mode
	return cfg
