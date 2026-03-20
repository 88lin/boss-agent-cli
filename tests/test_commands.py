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
