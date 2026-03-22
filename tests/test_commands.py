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
	assert len(commands) == 9


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
