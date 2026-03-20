import time

from boss_agent_cli.cache.store import CacheStore


def test_greet_record(tmp_path):
	store = CacheStore(tmp_path / "test.db")
	assert store.is_greeted("sec_001") is False
	store.record_greet("sec_001", "job_001")
	assert store.is_greeted("sec_001") is True


def test_get_job_id_for_greeted(tmp_path):
	store = CacheStore(tmp_path / "test.db")
	store.record_greet("sec_001", "job_001")
	assert store.get_job_id("sec_001") == "job_001"


def test_search_cache_hit(tmp_path):
	store = CacheStore(tmp_path / "test.db")
	params = {"query": "golang", "city": "杭州", "page": "1"}
	store.put_search(params, '{"jobs": []}')
	result = store.get_search(params)
	assert result == '{"jobs": []}'


def test_search_cache_miss(tmp_path):
	store = CacheStore(tmp_path / "test.db")
	params = {"query": "golang", "city": "杭州", "page": "1"}
	assert store.get_search(params) is None


def test_search_cache_expired(tmp_path):
	store = CacheStore(tmp_path / "test.db", search_ttl_seconds=1)
	params = {"query": "golang", "page": "1"}
	store.put_search(params, '{"jobs": []}')
	time.sleep(1.1)
	assert store.get_search(params) is None


def test_search_cache_different_params(tmp_path):
	store = CacheStore(tmp_path / "test.db")
	params_a = {"query": "golang", "city": "杭州", "page": "1"}
	params_b = {"query": "golang", "city": "北京", "page": "1"}
	store.put_search(params_a, '{"a": 1}')
	store.put_search(params_b, '{"b": 2}')
	assert store.get_search(params_a) == '{"a": 1}'
	assert store.get_search(params_b) == '{"b": 2}'


def test_search_cache_max_100(tmp_path):
	store = CacheStore(tmp_path / "test.db")
	for i in range(105):
		store.put_search({"query": f"q{i}", "page": "1"}, f'{{"i": {i}}}')
	assert store.get_search({"query": "q0", "page": "1"}) is None
	assert store.get_search({"query": "q104", "page": "1"}) is not None
