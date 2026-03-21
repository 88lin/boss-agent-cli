import click

from boss_agent_cli.output import emit_success

SCHEMA_DATA = {
	"name": "boss-agent-cli",
	"description": "BOSS直聘求职工具。支持搜索职位、查看详情、向招聘者打招呼。",
	"commands": {
		"login": {
			"description": "启动浏览器扫码登录 BOSS 直聘",
			"args": [],
			"options": {
				"--timeout": {
					"type": "int",
					"default": 120,
					"description": "登录超时时间（秒）",
				},
			},
		},
		"status": {
			"description": "检查当前登录态",
			"args": [],
			"options": {},
		},
		"search": {
			"description": "按关键词和筛选条件搜索职位列表",
			"args": [
				{"name": "query", "required": True, "description": "搜索关键词"},
			],
			"options": {
				"--city": {
					"type": "string",
					"default": None,
					"description": "城市名称（如 北京、上海）",
				},
				"--salary": {
					"type": "string",
					"default": None,
					"description": "薪资范围（如 10-20K）",
				},
				"--experience": {
					"type": "string",
					"default": None,
					"description": "经验要求（如 3-5年）",
				},
				"--education": {
					"type": "string",
					"default": None,
					"description": "学历要求（如 本科）",
				},
				"--industry": {
					"type": "string",
					"default": None,
					"description": "行业类型",
				},
				"--scale": {
					"type": "string",
					"default": None,
					"description": "公司规模（如 100-499人）",
				},
				"--welfare": {
					"type": "string",
					"default": None,
					"description": "福利筛选关键词（如 双休、五险一金）。启用后会逐个检查职位详情，自动翻页直到找到匹配结果",
					"examples": ["双休", "五险一金", "年终奖", "餐补", "住房补贴"],
				},
				"--page": {
					"type": "int",
					"default": 1,
					"description": "页码",
				},
				"--no-cache": {
					"type": "bool",
					"default": False,
					"description": "跳过缓存，强制请求接口",
				},
			},
		},
		"detail": {
			"description": "查看职位完整信息（职位描述、地址、招聘者信息）",
			"args": [
				{"name": "security_id", "required": True, "description": "安全 ID，从 search 结果中获取"},
			],
			"options": {
				"--lid": {
					"type": "string",
					"default": "",
					"description": "列表项 ID（可选，提高匹配精度）",
				},
			},
		},
		"greet": {
			"description": "向指定招聘者打招呼",
			"args": [
				{"name": "security_id", "required": True, "description": "安全 ID"},
				{"name": "job_id", "required": True, "description": "加密职位 ID"},
			],
			"options": {
				"--message": {
					"type": "string",
					"default": "",
					"description": "自定义打招呼消息",
				},
			},
		},
		"batch-greet": {
			"description": "搜索后批量打招呼（上限 10）",
			"args": [
				{"name": "query", "required": True, "description": "搜索关键词"},
			],
			"options": {
				"--city": {
					"type": "string",
					"default": None,
					"description": "城市名称",
				},
				"--salary": {
					"type": "string",
					"default": None,
					"description": "薪资范围",
				},
				"--count": {
					"type": "int",
					"default": 10,
					"description": "打招呼数量上限（最大 10）",
				},
				"--dry-run": {
					"type": "bool",
					"default": False,
					"description": "仅模拟执行，不实际打招呼",
				},
			},
		},
	},
	"global_options": {
		"--data-dir": {
			"type": "string",
			"default": "~/.boss-agent",
			"description": "数据存储目录",
		},
		"--delay": {
			"type": "string",
			"default": "1.5-3.0",
			"description": "请求间隔范围（秒），如 1.5-3.0",
		},
		"--log-level": {
			"type": "string",
			"default": "error",
			"choices": ["error", "warning", "info", "debug"],
			"description": "日志级别",
		},
	},
	"error_codes": {
		"AUTH_EXPIRED": {
			"message": "登录态过期",
			"recoverable": True,
			"recovery_action": "boss login",
		},
		"AUTH_REQUIRED": {
			"message": "未登录",
			"recoverable": True,
			"recovery_action": "boss login",
		},
		"RATE_LIMITED": {
			"message": "请求频率过高",
			"recoverable": True,
			"recovery_action": "等待后重试",
		},
		"TOKEN_REFRESH_FAILED": {
			"message": "Token 刷新失败",
			"recoverable": True,
			"recovery_action": "boss login",
		},
		"JOB_NOT_FOUND": {
			"message": "职位不存在或已下架",
			"recoverable": False,
			"recovery_action": None,
		},
		"ALREADY_GREETED": {
			"message": "已向该招聘者打过招呼",
			"recoverable": False,
			"recovery_action": None,
		},
		"GREET_LIMIT": {
			"message": "今日打招呼次数已用完",
			"recoverable": False,
			"recovery_action": None,
		},
		"NETWORK_ERROR": {
			"message": "网络请求失败",
			"recoverable": True,
			"recovery_action": "重试",
		},
		"INVALID_PARAM": {
			"message": "参数校验失败",
			"recoverable": False,
			"recovery_action": "修正参数",
		},
	},
	"conventions": {
		"stdout": "仅 JSON 结构化数据（信封格式）",
		"stderr": "日志和进度信息（通过 --log-level 控制）",
		"exit_code": {
			"0": "命令成功 (ok=true)",
			"1": "命令失败 (ok=false)",
		},
	},
}


@click.command("schema")
def schema_cmd():
	"""返回工具完整能力描述的 JSON"""
	emit_success("schema", SCHEMA_DATA)
