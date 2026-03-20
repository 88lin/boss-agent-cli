import json

from boss_agent_cli.auth.token_store import TokenStore


def test_save_and_load(tmp_path):
	store = TokenStore(tmp_path)
	token_data = {
		"cookies": {"wt2": "abc123"},
		"stoken": "zp_stoken_value",
	}
	store.save(token_data)
	loaded = store.load()
	assert loaded == token_data


def test_load_empty(tmp_path):
	store = TokenStore(tmp_path)
	assert store.load() is None


def test_overwrite(tmp_path):
	store = TokenStore(tmp_path)
	store.save({"cookies": {"wt2": "old"}})
	store.save({"cookies": {"wt2": "new"}})
	loaded = store.load()
	assert loaded["cookies"]["wt2"] == "new"


def test_file_lock(tmp_path):
	store = TokenStore(tmp_path)
	with store.refresh_lock():
		assert (tmp_path / "refresh.lock").exists()
	assert not (tmp_path / "refresh.lock").exists()
