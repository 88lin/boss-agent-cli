import json
from unittest.mock import patch, MagicMock

from click.testing import CliRunner
from boss_agent_cli.main import cli


def test_schema_command():
	runner = CliRunner()
	result = runner.invoke(cli, ["schema"])
	assert result.exit_code == 0
	parsed = json.loads(result.output)
	assert parsed["ok"] is True
	assert parsed["command"] == "schema"
	assert "search" in parsed["data"]["commands"]
	assert "login" in parsed["data"]["commands"]
	assert "greet" in parsed["data"]["commands"]
	assert "AUTH_EXPIRED" in parsed["data"]["error_codes"]
	assert "stdout" in parsed["data"]["conventions"]


@patch("boss_agent_cli.commands.status.AuthManager")
def test_status_not_logged_in(mock_auth_cls):
	mock_auth_cls.return_value.check_status.return_value = None
	runner = CliRunner()
	result = runner.invoke(cli, ["status"])
	assert result.exit_code == 1
	parsed = json.loads(result.output)
	assert parsed["ok"] is False
	assert parsed["error"]["code"] == "AUTH_REQUIRED"


@patch("boss_agent_cli.commands.search.CacheStore")
@patch("boss_agent_cli.commands.search.AuthManager")
@patch("boss_agent_cli.commands.search.BossClient")
def test_search_invalid_city(mock_client_cls, mock_auth_cls, mock_cache_cls):
	runner = CliRunner()
	result = runner.invoke(cli, ["search", "golang", "--city", "火星"])
	assert result.exit_code == 1
	parsed = json.loads(result.output)
	assert parsed["error"]["code"] == "INVALID_PARAM"


@patch("boss_agent_cli.commands.greet.BossClient")
@patch("boss_agent_cli.commands.greet.AuthManager")
@patch("boss_agent_cli.commands.greet.CacheStore")
def test_greet_already_greeted(mock_cache_cls, mock_auth_cls, mock_client_cls):
	mock_cache_cls.return_value.is_greeted.return_value = True
	runner = CliRunner()
	result = runner.invoke(cli, ["greet", "sec_001", "job_001"])
	assert result.exit_code == 1
	parsed = json.loads(result.output)
	assert parsed["error"]["code"] == "ALREADY_GREETED"


@patch("boss_agent_cli.commands.greet.time")
@patch("boss_agent_cli.commands.greet.BossClient")
@patch("boss_agent_cli.commands.greet.AuthManager")
@patch("boss_agent_cli.commands.greet.CacheStore")
def test_batch_greet_dry_run(mock_cache_cls, mock_auth_cls, mock_client_cls, mock_time):
	mock_cache = mock_cache_cls.return_value
	mock_cache.is_greeted.return_value = False
	mock_client = mock_client_cls.return_value
	mock_client.search_jobs.return_value = {
		"zpData": {
			"jobList": [
				{
					"encryptJobId": "j1",
					"jobName": "Golang",
					"brandName": "ByteDance",
					"salaryDesc": "30K",
					"cityName": "北京",
					"jobExperience": "3-5年",
					"jobDegree": "本科",
					"bossName": "张",
					"bossTitle": "CTO",
					"bossOnline": True,
					"securityId": "sec_1",
				},
			],
		},
	}
	runner = CliRunner()
	result = runner.invoke(cli, ["batch-greet", "golang", "--dry-run"])
	assert result.exit_code == 0
	parsed = json.loads(result.output)
	assert parsed["ok"] is True
	assert parsed["data"]["dry_run"] is True
	assert parsed["data"]["count"] == 1


def test_cities_command():
	runner = CliRunner()
	result = runner.invoke(cli, ["cities"])
	assert result.exit_code == 0
	parsed = json.loads(result.output)
	assert parsed["ok"] is True
	assert parsed["command"] == "cities"
	assert parsed["data"]["count"] == 40
	assert "广州" in parsed["data"]["cities"]
	assert "北京" in parsed["data"]["cities"]
	assert parsed["hints"] is not None


def test_schema_includes_new_commands():
	runner = CliRunner()
	result = runner.invoke(cli, ["schema"])
	parsed = json.loads(result.output)
	commands = parsed["data"]["commands"]
	assert "recommend" in commands
	assert "export" in commands
	assert "cities" in commands
	assert "me" in commands
	assert "show" in commands
	assert "history" in commands
	assert "chat" in commands
	assert "interviews" in commands
	assert "logout" in commands
	assert len(commands) == 15


@patch("boss_agent_cli.commands.recommend.CacheStore")
@patch("boss_agent_cli.commands.recommend.BossClient")
@patch("boss_agent_cli.commands.recommend.AuthManager")
def test_recommend_success(mock_auth_cls, mock_client_cls, mock_cache_cls):
	mock_cache = mock_cache_cls.return_value
	mock_cache.is_greeted.return_value = False
	mock_client = mock_client_cls.return_value
	mock_client.recommend_jobs.return_value = {
		"zpData": {
			"hasMore": True,
			"jobList": [
				{
					"encryptJobId": "j1",
					"jobName": "Go 开发",
					"brandName": "TestCo",
					"salaryDesc": "20K",
					"cityName": "广州",
					"areaDistrict": "天河区",
					"jobExperience": "3-5年",
					"jobDegree": "本科",
					"skills": ["Golang"],
					"welfareList": ["五险一金"],
					"brandIndustry": "互联网",
					"brandScaleName": "100-499人",
					"brandStageName": "A轮",
					"bossName": "李",
					"bossTitle": "HR",
					"bossOnline": True,
					"securityId": "sec_r1",
				},
			],
		},
	}
	runner = CliRunner()
	result = runner.invoke(cli, ["recommend"])
	assert result.exit_code == 0
	parsed = json.loads(result.output)
	assert parsed["ok"] is True
	assert len(parsed["data"]) == 1
	assert parsed["data"][0]["company"] == "TestCo"
	assert parsed["pagination"]["has_more"] is True
	assert parsed["hints"] is not None


@patch("boss_agent_cli.commands.export.BossClient")
@patch("boss_agent_cli.commands.export.AuthManager")
def test_export_to_stdout(mock_auth_cls, mock_client_cls):
	mock_client = mock_client_cls.return_value
	mock_client.search_jobs.return_value = {
		"zpData": {
			"hasMore": False,
			"jobList": [
				{
					"encryptJobId": "j1",
					"jobName": "Go 开发",
					"brandName": "TestCo",
					"salaryDesc": "20K",
					"cityName": "广州",
					"areaDistrict": "天河区",
					"jobExperience": "3-5年",
					"jobDegree": "本科",
					"skills": ["Golang"],
					"welfareList": ["五险一金"],
					"brandIndustry": "互联网",
					"brandScaleName": "100-499人",
					"brandStageName": "A轮",
					"bossName": "李",
					"bossTitle": "HR",
					"bossOnline": True,
					"securityId": "sec_e1",
				},
			],
		},
	}
	runner = CliRunner()
	result = runner.invoke(cli, ["export", "golang", "--count", "1"])
	assert result.exit_code == 0
	parsed = json.loads(result.output)
	assert parsed["ok"] is True
	assert parsed["data"]["count"] == 1
	assert parsed["data"]["format"] == "csv"
	assert len(parsed["data"]["jobs"]) == 1


def _make_friend_item(name, brand, relation_type, last_ts):
	"""构造 friend_list API 返回的单条记录"""
	return {
		"name": name,
		"title": "HR",
		"brandName": brand,
		"lastMsg": "你好",
		"lastTime": "今天 10:00",
		"lastTS": last_ts,
		"securityId": f"sec_{name}",
		"encryptJobId": f"job_{name}",
		"unreadMsgCount": 0,
		"relationType": relation_type,
		"friendSource": 0,
		"sourceType": 0,
		"lastMessageInfo": {"status": 2},
	}


@patch("boss_agent_cli.commands.chat.BossClient")
@patch("boss_agent_cli.commands.chat.AuthManager")
def test_chat_from_boss_filter(mock_auth_cls, mock_client_cls):
	"""--from boss 只返回 relationType=1 的记录"""
	import time
	now_ms = int(time.time() * 1000)
	mock_auth_cls.return_value.check_status.return_value = {"cookies": {}}
	mock_client_cls.return_value.friend_list.return_value = {
		"zpData": {
			"result": [
				_make_friend_item("张HR", "阿里", 1, now_ms),
				_make_friend_item("我自己", "腾讯", 2, now_ms),
				_make_friend_item("李HR", "字节", 1, now_ms),
			],
		},
	}
	runner = CliRunner()
	result = runner.invoke(cli, ["chat", "--from", "boss"])
	assert result.exit_code == 0
	parsed = json.loads(result.output)
	assert parsed["ok"] is True
	assert len(parsed["data"]) == 2
	assert all(f["initiated_by"] == "对方主动" for f in parsed["data"])


@patch("boss_agent_cli.commands.chat.BossClient")
@patch("boss_agent_cli.commands.chat.AuthManager")
def test_chat_days_filter(mock_auth_cls, mock_client_cls):
	"""--days 3 只返回最近 3 天的记录"""
	import time
	now_ms = int(time.time() * 1000)
	old_ms = now_ms - 5 * 86400 * 1000  # 5 天前
	mock_auth_cls.return_value.check_status.return_value = {"cookies": {}}
	mock_client_cls.return_value.friend_list.return_value = {
		"zpData": {
			"result": [
				_make_friend_item("新HR", "阿里", 1, now_ms),
				_make_friend_item("旧HR", "腾讯", 1, old_ms),
			],
		},
	}
	runner = CliRunner()
	result = runner.invoke(cli, ["chat", "--days", "3"])
	assert result.exit_code == 0
	parsed = json.loads(result.output)
	assert parsed["ok"] is True
	assert len(parsed["data"]) == 1
	assert parsed["data"][0]["brand_name"] == "阿里"


@patch("boss_agent_cli.commands.chat.BossClient")
@patch("boss_agent_cli.commands.chat.AuthManager")
def test_chat_combined_filter(mock_auth_cls, mock_client_cls):
	"""--from boss --days 3 组合筛选"""
	import time
	now_ms = int(time.time() * 1000)
	old_ms = now_ms - 5 * 86400 * 1000
	mock_auth_cls.return_value.check_status.return_value = {"cookies": {}}
	mock_client_cls.return_value.friend_list.return_value = {
		"zpData": {
			"result": [
				_make_friend_item("新HR", "阿里", 1, now_ms),       # 命中
				_make_friend_item("新我", "腾讯", 2, now_ms),       # from 不匹配
				_make_friend_item("旧HR", "字节", 1, old_ms),       # days 不匹配
			],
		},
	}
	runner = CliRunner()
	result = runner.invoke(cli, ["chat", "--from", "boss", "--days", "3"])
	assert result.exit_code == 0
	parsed = json.loads(result.output)
	assert parsed["ok"] is True
	assert len(parsed["data"]) == 1
	assert parsed["data"][0]["brand_name"] == "阿里"
	assert parsed["data"][0]["initiated_by"] == "对方主动"


@patch("boss_agent_cli.commands.chat.BossClient")
@patch("boss_agent_cli.commands.chat.AuthManager")
def test_chat_export_md(mock_auth_cls, mock_client_cls, tmp_path):
	"""--export md 导出包含 security_id 和 diff 摘要"""
	import time
	now_ms = int(time.time() * 1000)
	mock_auth_cls.return_value.check_status.return_value = {"cookies": {}}
	mock_client_cls.return_value.friend_list.return_value = {
		"zpData": {
			"result": [
				_make_friend_item("张HR", "阿里", 1, now_ms),
				_make_friend_item("我自己", "腾讯", 2, now_ms),
			],
		},
	}
	out_file = str(tmp_path / "chat.md")
	runner = CliRunner()
	result = runner.invoke(cli, [
		"--data-dir", str(tmp_path),
		"chat", "--export", "md", "-o", out_file,
	])
	assert result.exit_code == 0
	with open(out_file, encoding="utf-8") as f:
		content = f.read()
	assert "security_id" in content  # 折叠映射表中包含
	assert "sec_张HR" in content    # 完整 sid 在映射表中
	assert "S1" in content          # 主表用短编号
	assert "BOSS 直聘沟通列表" in content
	assert "对方主动" in content
	# 快照应已保存
	import os
	snapshot_dir = tmp_path / "chat-history"
	assert snapshot_dir.exists()
	json_files = list(snapshot_dir.glob("*.json"))
	assert len(json_files) == 1


@patch("boss_agent_cli.commands.chat.BossClient")
@patch("boss_agent_cli.commands.chat.AuthManager")
def test_chat_export_csv(mock_auth_cls, mock_client_cls, tmp_path):
	"""--export csv 导出 CSV 格式"""
	import time
	now_ms = int(time.time() * 1000)
	mock_auth_cls.return_value.check_status.return_value = {"cookies": {}}
	mock_client_cls.return_value.friend_list.return_value = {
		"zpData": {
			"result": [
				_make_friend_item("张HR", "阿里", 1, now_ms),
			],
		},
	}
	out_file = str(tmp_path / "chat.csv")
	runner = CliRunner()
	result = runner.invoke(cli, [
		"--data-dir", str(tmp_path),
		"chat", "--export", "csv", "-o", out_file,
	])
	assert result.exit_code == 0
	with open(out_file, encoding="utf-8") as f:
		content = f.read()
	assert "name,title,brand_name" in content
	assert "张HR" in content


@patch("boss_agent_cli.commands.chat.BossClient")
@patch("boss_agent_cli.commands.chat.AuthManager")
def test_chat_export_json_default_path(mock_auth_cls, mock_client_cls, tmp_path):
	"""--export json 不指定 -o 时自动保存到 chat-export/ 目录"""
	import time
	now_ms = int(time.time() * 1000)
	mock_auth_cls.return_value.check_status.return_value = {"cookies": {}}
	mock_client_cls.return_value.friend_list.return_value = {
		"zpData": {
			"result": [
				_make_friend_item("张HR", "阿里", 1, now_ms),
			],
		},
	}
	runner = CliRunner()
	result = runner.invoke(cli, [
		"--data-dir", str(tmp_path),
		"chat", "--export", "json",
	])
	assert result.exit_code == 0
	parsed = json.loads(result.output)
	assert parsed["ok"] is True
	assert parsed["data"]["format"] == "json"
	# 文件应已写入 chat-export/
	import os, datetime
	today = datetime.date.today().isoformat()
	expected = tmp_path / "chat-export" / f"沟通列表-{today}.json"
	assert expected.exists()
	with open(expected, encoding="utf-8") as f:
		items = json.load(f)
	assert items[0]["security_id"] == "sec_张HR"


@patch("boss_agent_cli.commands.chat.BossClient")
@patch("boss_agent_cli.commands.chat.AuthManager")
def test_chat_snapshot_diff(mock_auth_cls, mock_client_cls, tmp_path):
	"""第二次导出时 diff 能检测新增条目"""
	import time
	now_ms = int(time.time() * 1000)

	# 先手动写入一份"昨天"的快照
	import os, datetime
	snapshot_dir = tmp_path / "chat-history"
	snapshot_dir.mkdir(parents=True)
	yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
	prev_snapshot = [
		{"name": "张HR", "brand_name": "阿里", "security_id": "sec_张HR",
		 "unread": 0, "last_time": "昨天"},
	]
	with open(snapshot_dir / f"{yesterday}.json", "w") as f:
		json.dump(prev_snapshot, f)

	# 现在 API 返回多了一条
	mock_auth_cls.return_value.check_status.return_value = {"cookies": {}}
	mock_client_cls.return_value.friend_list.return_value = {
		"zpData": {
			"result": [
				_make_friend_item("张HR", "阿里", 1, now_ms),
				_make_friend_item("新HR", "字节", 1, now_ms),
			],
		},
	}
	out_file = str(tmp_path / "chat.md")
	runner = CliRunner()
	result = runner.invoke(cli, [
		"--data-dir", str(tmp_path),
		"chat", "--export", "md", "-o", out_file,
	])
	assert result.exit_code == 0
	with open(out_file, encoding="utf-8") as f:
		content = f.read()
	assert "新增 1 条" in content
	assert "NEW" in content

