# boss-agent-cli 实施计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个专为 AI Agent 设计的 BOSS 直聘求职 CLI 工具，支持搜索职位、查看详情、自动打招呼，所有输出为结构化 JSON。

**Architecture:** Playwright 处理登录和 Token 刷新，httpx 执行日常 API 调用，Click 提供 CLI 入口，SQLite 做轻量缓存。所有命令输出统一 JSON 信封格式到 stdout，日志到 stderr。

**Tech Stack:** Python >=3.10, Click, httpx, Playwright + playwright-stealth, cryptography (Fernet), sqlite3, uv + hatchling

**Spec:** `docs/superpowers/specs/2026-03-20-boss-agent-cli-design.md`

---

## File Map

| File | Responsibility | Task |
|------|---------------|------|
| `pyproject.toml` | 项目元数据、依赖、构建配置、CLI 入口点 | 1 |
| `src/boss_agent_cli/__init__.py` | 包初始化，版本号 | 1 |
| `src/boss_agent_cli/output.py` | JSON 信封封装 + 日志级别过滤 | 2 |
| `tests/test_output.py` | output.py 测试 | 2 |
| `src/boss_agent_cli/config.py` | 配置文件读取与默认值 | 2 |
| `src/boss_agent_cli/cache/__init__.py` | 包初始化 | 3 |
| `src/boss_agent_cli/cache/store.py` | SQLite WAL 缓存（含 100 条上限） | 3 |
| `tests/test_cache.py` | cache 测试 | 3 |
| `src/boss_agent_cli/auth/__init__.py` | 包初始化 | 4 |
| `src/boss_agent_cli/auth/token_store.py` | Fernet 加密 Token 持久化 + 文件锁 | 4 |
| `tests/test_auth.py` | token_store 测试 | 4 |
| `src/boss_agent_cli/api/__init__.py` | 包初始化 | 5 |
| `src/boss_agent_cli/api/endpoints.py` | wapi 端点常量 + 城市/薪资映射表 | 5 |
| `src/boss_agent_cli/api/models.py` | 响应数据 dataclass | 5 |
| `src/boss_agent_cli/api/client.py` | BossClient: httpx 请求 + Token 注入 + 重试上限 | 5 |
| `tests/test_api.py` | API 层测试 | 5 |
| `src/boss_agent_cli/auth/browser.py` | Playwright 登录 + stoken 提取 | 6 |
| `src/boss_agent_cli/auth/manager.py` | AuthManager: Token 生命周期（抛异常而非 sys.exit） | 6 |
| `src/boss_agent_cli/main.py` | Click CLI group + 全局选项 + 配置加载 | 7 |
| `src/boss_agent_cli/commands/__init__.py` | 包初始化 | 7 |
| `src/boss_agent_cli/commands/schema.py` | boss schema 命令 | 7 |
| `src/boss_agent_cli/commands/login.py` | boss login 命令 | 7 |
| `src/boss_agent_cli/commands/status.py` | boss status 命令 | 7 |
| `src/boss_agent_cli/commands/search.py` | boss search 命令 | 7 |
| `src/boss_agent_cli/commands/detail.py` | boss detail 命令 | 7 |
| `src/boss_agent_cli/commands/greet.py` | boss greet + batch-greet 命令 | 7 |
| `tests/test_commands.py` | 命令层测试（mock API） | 8 |
| `README.md` | 项目文档 | 9 |

---

## Chunk 1: 项目脚手架

### Task 1: 项目初始化

**Files:**
- Create: `pyproject.toml`
- Create: `src/boss_agent_cli/__init__.py`
- Create: `.gitignore`

- [ ] **Step 1: 创建 pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "boss-agent-cli"
version = "0.1.0"
description = "AI Agent 专用的 BOSS 直聘求职 CLI 工具"
readme = "README.md"
requires-python = ">=3.10"
license = "MIT"
dependencies = [
	"click>=8.0",
	"httpx>=0.27",
	"playwright>=1.40",
	"playwright-stealth>=1.0",
	"cryptography>=42.0",
]

[project.optional-dependencies]
dev = ["pytest>=7.0"]

[project.scripts]
boss = "boss_agent_cli.main:cli"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

- [ ] **Step 2: 创建包初始化文件**

`src/boss_agent_cli/__init__.py`:
```python
__version__ = "0.1.0"
```

- [ ] **Step 3: 初始化 uv 项目并安装依赖**

```bash
cd /Users/can4hou6joeng4/Documents/code/boss-agent-cli
uv sync --all-extras
uv run playwright install chromium
```

- [ ] **Step 4: 验证安装**

```bash
uv run python -c "import boss_agent_cli; print(boss_agent_cli.__version__)"
```

Expected: `0.1.0`

- [ ] **Step 5: 初始化 git 并提交**

```bash
cd /Users/can4hou6joeng4/Documents/code/boss-agent-cli
git init
cat > .gitignore << 'EOF'
__pycache__/
*.pyc
.venv/
*.egg-info/
dist/
build/
.pytest_cache/
EOF
git add .
git commit -m "chore: 初始化项目脚手架"
```

---

## Chunk 2: 输出层 + 配置

### Task 2: JSON 信封输出模块 + 配置文件

**Files:**
- Create: `src/boss_agent_cli/output.py`
- Create: `src/boss_agent_cli/config.py`
- Create: `tests/test_output.py`

- [ ] **Step 1: 编写 output.py 测试**

`tests/test_output.py`:
```python
import json

from boss_agent_cli.output import envelope_success, envelope_error, Logger


def test_envelope_success_minimal():
	result = envelope_success("status", {"logged_in": True})
	parsed = json.loads(result)
	assert parsed["ok"] is True
	assert parsed["schema_version"] == "1.0"
	assert parsed["command"] == "status"
	assert parsed["data"] == {"logged_in": True}
	assert parsed["pagination"] is None
	assert parsed["error"] is None
	assert parsed["hints"] is None


def test_envelope_success_with_pagination():
	result = envelope_success(
		"search",
		{"jobs": []},
		pagination={"page": 1, "total_pages": 5, "total_count": 50, "has_next": True},
		hints={"next_actions": ["boss search q --page 2"]},
	)
	parsed = json.loads(result)
	assert parsed["ok"] is True
	assert parsed["pagination"]["has_next"] is True
	assert parsed["hints"]["next_actions"][0] == "boss search q --page 2"


def test_envelope_error():
	result = envelope_error(
		"search",
		code="AUTH_EXPIRED",
		message="登录态已过期",
		recoverable=True,
		recovery_action="boss login",
	)
	parsed = json.loads(result)
	assert parsed["ok"] is False
	assert parsed["data"] is None
	assert parsed["error"]["code"] == "AUTH_EXPIRED"
	assert parsed["error"]["recoverable"] is True
	assert parsed["error"]["recovery_action"] == "boss login"


def test_logger_filters_by_level(capsys):
	logger = Logger("warning")
	logger.debug("debug msg")
	logger.info("info msg")
	logger.warning("warn msg")
	logger.error("error msg")
	captured = capsys.readouterr()
	assert "debug msg" not in captured.err
	assert "info msg" not in captured.err
	assert "warn msg" in captured.err
	assert "error msg" in captured.err


def test_config_defaults():
	from boss_agent_cli.config import load_config
	cfg = load_config(None)
	assert cfg["request_delay"] == [1.5, 3.0]
	assert cfg["batch_greet_max"] == 10
	assert cfg["log_level"] == "error"


def test_config_from_file(tmp_path):
	import json as json_mod
	from boss_agent_cli.config import load_config
	cfg_file = tmp_path / "config.json"
	cfg_file.write_text(json_mod.dumps({"default_city": "杭州", "log_level": "debug"}))
	cfg = load_config(cfg_file)
	assert cfg["default_city"] == "杭州"
	assert cfg["log_level"] == "debug"
	assert cfg["batch_greet_max"] == 10  # 默认值保留
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /Users/can4hou6joeng4/Documents/code/boss-agent-cli
uv run pytest tests/test_output.py -v
```

Expected: FAIL

- [ ] **Step 3: 实现 output.py**

`src/boss_agent_cli/output.py`:
```python
import json
import sys

_LEVEL_ORDER = {"debug": 0, "info": 1, "warning": 2, "error": 3}


def envelope_success(
	command: str,
	data,
	*,
	pagination: dict | None = None,
	hints: dict | None = None,
) -> str:
	return json.dumps(
		{
			"ok": True,
			"schema_version": "1.0",
			"command": command,
			"data": data,
			"pagination": pagination,
			"error": None,
			"hints": hints,
		},
		ensure_ascii=False,
	)


def envelope_error(
	command: str,
	*,
	code: str,
	message: str,
	recoverable: bool = False,
	recovery_action: str | None = None,
	hints: dict | None = None,
) -> str:
	return json.dumps(
		{
			"ok": False,
			"schema_version": "1.0",
			"command": command,
			"data": None,
			"pagination": None,
			"error": {
				"code": code,
				"message": message,
				"recoverable": recoverable,
				"recovery_action": recovery_action,
			},
			"hints": hints,
		},
		ensure_ascii=False,
	)


def emit_success(command: str, data, **kwargs) -> None:
	print(envelope_success(command, data, **kwargs))


def emit_error(command: str, **kwargs) -> None:
	print(envelope_error(command, **kwargs))
	sys.exit(1)


class Logger:
	def __init__(self, level: str = "error"):
		self._threshold = _LEVEL_ORDER.get(level, 3)

	def _log(self, level: str, message: str):
		if _LEVEL_ORDER.get(level, 0) >= self._threshold:
			print(message, file=sys.stderr)

	def debug(self, message: str):
		self._log("debug", message)

	def info(self, message: str):
		self._log("info", message)

	def warning(self, message: str):
		self._log("warning", message)

	def error(self, message: str):
		self._log("error", message)
```

- [ ] **Step 4: 实现 config.py**

`src/boss_agent_cli/config.py`:
```python
import json
from pathlib import Path

DEFAULTS = {
	"default_city": None,
	"default_salary": None,
	"request_delay": [1.5, 3.0],
	"batch_greet_delay": [2.0, 5.0],
	"batch_greet_max": 10,
	"log_level": "error",
	"login_timeout": 120,
}


def load_config(config_path: Path | None) -> dict:
	cfg = dict(DEFAULTS)
	if config_path and config_path.exists():
		with open(config_path) as f:
			user_cfg = json.load(f)
		cfg.update(user_cfg)
	return cfg
```

- [ ] **Step 5: 运行测试确认通过**

```bash
uv run pytest tests/test_output.py -v
```

Expected: 6 passed

- [ ] **Step 6: 提交**

```bash
git add src/boss_agent_cli/output.py src/boss_agent_cli/config.py tests/test_output.py
git commit -m "feat: 添加 JSON 信封输出模块和配置文件"
```

---

## Chunk 3: 缓存层

### Task 3: SQLite 缓存模块

**Files:**
- Create: `src/boss_agent_cli/cache/__init__.py`
- Create: `src/boss_agent_cli/cache/store.py`
- Create: `tests/test_cache.py`

- [ ] **Step 1: 编写缓存测试**

`tests/test_cache.py`:
```python
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
	# 最早的 5 条应被淘汰
	assert store.get_search({"query": "q0", "page": "1"}) is None
	assert store.get_search({"query": "q104", "page": "1"}) is not None
```

- [ ] **Step 2: 运行测试确认失败**

```bash
uv run pytest tests/test_cache.py -v
```

Expected: FAIL

- [ ] **Step 3: 实现 cache/store.py**

`src/boss_agent_cli/cache/__init__.py`:
```python
```

`src/boss_agent_cli/cache/store.py`:
```python
import hashlib
import json
import sqlite3
import time
from pathlib import Path

_SEARCH_TTL = 86400  # 24 hours
_MAX_SEARCH_CACHE = 100


class CacheStore:
	def __init__(self, db_path: Path, *, search_ttl_seconds: int = _SEARCH_TTL):
		self._db_path = db_path
		self._search_ttl = search_ttl_seconds
		db_path.parent.mkdir(parents=True, exist_ok=True)
		self._conn = sqlite3.connect(str(db_path))
		self._conn.execute("PRAGMA journal_mode=WAL")
		self._init_tables()

	def _init_tables(self):
		self._conn.executescript("""
			CREATE TABLE IF NOT EXISTS greet_records (
				security_id TEXT PRIMARY KEY,
				job_id TEXT NOT NULL,
				greeted_at REAL NOT NULL
			);
			CREATE TABLE IF NOT EXISTS search_cache (
				cache_key TEXT PRIMARY KEY,
				response TEXT NOT NULL,
				created_at REAL NOT NULL
			);
		""")

	@staticmethod
	def _make_search_key(params: dict) -> str:
		raw = json.dumps(params, sort_keys=True, ensure_ascii=False)
		return hashlib.sha256(raw.encode()).hexdigest()

	def is_greeted(self, security_id: str) -> bool:
		row = self._conn.execute(
			"SELECT 1 FROM greet_records WHERE security_id = ?",
			(security_id,),
		).fetchone()
		return row is not None

	def get_job_id(self, security_id: str) -> str | None:
		row = self._conn.execute(
			"SELECT job_id FROM greet_records WHERE security_id = ?",
			(security_id,),
		).fetchone()
		return row[0] if row else None

	def record_greet(self, security_id: str, job_id: str) -> None:
		self._conn.execute(
			"INSERT OR REPLACE INTO greet_records (security_id, job_id, greeted_at) VALUES (?, ?, ?)",
			(security_id, job_id, time.time()),
		)
		self._conn.commit()

	def get_search(self, params: dict) -> str | None:
		key = self._make_search_key(params)
		row = self._conn.execute(
			"SELECT response, created_at FROM search_cache WHERE cache_key = ?",
			(key,),
		).fetchone()
		if row is None:
			return None
		if time.time() - row[1] > self._search_ttl:
			self._conn.execute("DELETE FROM search_cache WHERE cache_key = ?", (key,))
			self._conn.commit()
			return None
		return row[0]

	def put_search(self, params: dict, response: str) -> None:
		key = self._make_search_key(params)
		self._conn.execute(
			"INSERT OR REPLACE INTO search_cache (cache_key, response, created_at) VALUES (?, ?, ?)",
			(key, response, time.time()),
		)
		self._conn.commit()
		self._evict_old_search_cache()

	def _evict_old_search_cache(self) -> None:
		count = self._conn.execute("SELECT COUNT(*) FROM search_cache").fetchone()[0]
		if count > _MAX_SEARCH_CACHE:
			excess = count - _MAX_SEARCH_CACHE
			self._conn.execute(
				"DELETE FROM search_cache WHERE cache_key IN "
				"(SELECT cache_key FROM search_cache ORDER BY created_at ASC LIMIT ?)",
				(excess,),
			)
			self._conn.commit()

	def close(self):
		self._conn.close()
```

- [ ] **Step 4: 运行测试确认通过**

```bash
uv run pytest tests/test_cache.py -v
```

Expected: 7 passed

- [ ] **Step 5: 提交**

```bash
git add src/boss_agent_cli/cache/ tests/test_cache.py
git commit -m "feat: 添加 SQLite 缓存模块（含 100 条上限）"
```

---

## Chunk 4: 认证存储层

### Task 4: Token 加密存储 + 文件锁

**Files:**
- Create: `src/boss_agent_cli/auth/__init__.py`
- Create: `src/boss_agent_cli/auth/token_store.py`
- Create: `tests/test_auth.py`

- [ ] **Step 1: 编写 token_store 测试**

`tests/test_auth.py`:
```python
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
```

- [ ] **Step 2: 运行测试确认失败**

```bash
uv run pytest tests/test_auth.py -v
```

Expected: FAIL

- [ ] **Step 3: 实现 token_store.py**

`src/boss_agent_cli/auth/__init__.py`:
```python
```

`src/boss_agent_cli/auth/token_store.py`:
```python
import hashlib
import json
import os
import platform
import subprocess
import time
from base64 import urlsafe_b64encode
from contextlib import contextmanager
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

_LOCK_TIMEOUT = 30


class TokenStore:
	def __init__(self, auth_dir: Path):
		self._auth_dir = auth_dir
		self._auth_dir.mkdir(parents=True, exist_ok=True)
		self._session_path = auth_dir / "session.enc"
		self._salt_path = auth_dir / "salt"
		self._lock_path = auth_dir / "refresh.lock"

	def _get_machine_id(self) -> str:
		system = platform.system()
		if system == "Darwin":
			result = subprocess.run(
				["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
				capture_output=True, text=True,
			)
			for line in result.stdout.splitlines():
				if "IOPlatformUUID" in line:
					return line.split('"')[-2]
		elif system == "Linux":
			machine_id = Path("/etc/machine-id")
			if machine_id.exists():
				return machine_id.read_text().strip()
		elif system == "Windows":
			result = subprocess.run(
				["reg", "query", r"HKLM\SOFTWARE\Microsoft\Cryptography", "/v", "MachineGuid"],
				capture_output=True, text=True,
			)
			for line in result.stdout.splitlines():
				if "MachineGuid" in line:
					return line.split()[-1]
		return "boss-agent-cli-fallback-id"

	def _get_salt(self) -> bytes:
		if self._salt_path.exists():
			return self._salt_path.read_bytes()
		salt = os.urandom(16)
		self._salt_path.write_bytes(salt)
		return salt

	def _derive_key(self) -> bytes:
		salt = self._get_salt()
		machine_id = self._get_machine_id()
		kdf = PBKDF2HMAC(
			algorithm=hashes.SHA256(),
			length=32,
			salt=salt,
			iterations=480000,
		)
		key = kdf.derive(machine_id.encode())
		return urlsafe_b64encode(key)

	def save(self, token_data: dict) -> None:
		fernet = Fernet(self._derive_key())
		plaintext = json.dumps(token_data, ensure_ascii=False).encode()
		encrypted = fernet.encrypt(plaintext)
		self._session_path.write_bytes(encrypted)

	def load(self) -> dict | None:
		if not self._session_path.exists():
			return None
		fernet = Fernet(self._derive_key())
		encrypted = self._session_path.read_bytes()
		plaintext = fernet.decrypt(encrypted)
		return json.loads(plaintext)

	@contextmanager
	def refresh_lock(self):
		deadline = time.time() + _LOCK_TIMEOUT
		while self._lock_path.exists():
			if time.time() > deadline:
				self._lock_path.unlink(missing_ok=True)
				break
			time.sleep(0.5)
		self._lock_path.touch()
		try:
			yield
		finally:
			self._lock_path.unlink(missing_ok=True)
```

- [ ] **Step 4: 运行测试确认通过**

```bash
uv run pytest tests/test_auth.py -v
```

Expected: 4 passed

- [ ] **Step 5: 提交**

```bash
git add src/boss_agent_cli/auth/ tests/test_auth.py
git commit -m "feat: 添加 Token 加密存储和文件锁"
```

---

## Chunk 5: API 层

### Task 5: 端点定义 + 数据模型 + BossClient

**Files:**
- Create: `src/boss_agent_cli/api/__init__.py`
- Create: `src/boss_agent_cli/api/endpoints.py`
- Create: `src/boss_agent_cli/api/models.py`
- Create: `src/boss_agent_cli/api/client.py`
- Create: `tests/test_api.py`

- [ ] **Step 1: 编写 API 层测试**

`tests/test_api.py`:
```python
from boss_agent_cli.api.endpoints import CITY_CODES, SALARY_CODES, EXPERIENCE_CODES
from boss_agent_cli.api.models import JobItem, JobDetail


def test_city_code_lookup():
	assert CITY_CODES["北京"] == "101010100"
	assert CITY_CODES["杭州"] == "101210100"
	assert "火星" not in CITY_CODES


def test_salary_code_lookup():
	assert SALARY_CODES["10-20K"] == "405"
	assert SALARY_CODES["20-50K"] == "406"


def test_experience_code_lookup():
	assert EXPERIENCE_CODES["应届"] == "108"
	assert EXPERIENCE_CODES["3-5年"] == "104"


def test_job_item_from_api():
	raw = {
		"encryptJobId": "abc123",
		"jobName": "Golang 工程师",
		"brandName": "字节跳动",
		"salaryDesc": "25-50K·15薪",
		"cityName": "北京",
		"jobExperience": "3-5年",
		"jobDegree": "本科",
		"bossName": "张先生",
		"bossTitle": "技术总监",
		"bossOnline": True,
		"securityId": "sec_xxx",
	}
	job = JobItem.from_api(raw)
	assert job.job_id == "abc123"
	assert job.title == "Golang 工程师"
	assert job.company == "字节跳动"
	assert job.security_id == "sec_xxx"


def test_job_item_to_dict():
	raw = {
		"encryptJobId": "abc123",
		"jobName": "Golang 工程师",
		"brandName": "字节跳动",
		"salaryDesc": "25-50K",
		"cityName": "北京",
		"jobExperience": "3-5年",
		"jobDegree": "本科",
		"bossName": "张先生",
		"bossTitle": "CTO",
		"bossOnline": False,
		"securityId": "sec_001",
	}
	job = JobItem.from_api(raw)
	d = job.to_dict()
	assert d["job_id"] == "abc123"
	assert d["boss_active"] == "离线"
	assert d["greeted"] is False
```

- [ ] **Step 2: 运行测试确认失败**

```bash
uv run pytest tests/test_api.py -v
```

Expected: FAIL

- [ ] **Step 3: 实现 endpoints.py**

`src/boss_agent_cli/api/__init__.py`:
```python
```

`src/boss_agent_cli/api/endpoints.py`:
```python
BASE_URL = "https://www.zhipin.com"

SEARCH_URL = f"{BASE_URL}/wapi/zpgeek/search/joblist.json"
RECOMMEND_URL = f"{BASE_URL}/wapi/zpgeek/pc/recommend/job/list.json"
DETAIL_URL = f"{BASE_URL}/wapi/zpgeek/job/detail.json"
GREET_URL = f"{BASE_URL}/wapi/zpgeek/friend/add.json"
USER_INFO_URL = f"{BASE_URL}/wapi/zpgeek/common/user/info.json"

CITY_CODES = {
	"北京": "101010100", "上海": "101020100", "广州": "101280100",
	"深圳": "101280600", "杭州": "101210100", "成都": "101270100",
	"南京": "101190100", "武汉": "101200100", "西安": "101110100",
	"苏州": "101190400", "长沙": "101250100", "郑州": "101180100",
	"重庆": "101040100", "天津": "101030100", "合肥": "101220100",
	"厦门": "101230200", "济南": "101120100", "青岛": "101120200",
	"大连": "101070200", "宁波": "101210400", "福州": "101230100",
	"东莞": "101281600", "珠海": "101280700", "佛山": "101280800",
	"昆明": "101290100", "贵阳": "101260100", "太原": "101100100",
	"南昌": "101240100", "南宁": "101300100", "石家庄": "101090100",
	"哈尔滨": "101050100", "长春": "101060100", "沈阳": "101070100",
	"海口": "101310100", "兰州": "101160100", "乌鲁木齐": "101130100",
	"无锡": "101190200", "常州": "101191100", "温州": "101210700",
	"惠州": "101280300",
}

SALARY_CODES = {
	"3K以下": "401", "3-5K": "402", "5-10K": "403",
	"10-15K": "404", "10-20K": "405", "20-50K": "406", "50K以上": "407",
}

EXPERIENCE_CODES = {
	"应届": "108", "1年以内": "101", "1-3年": "103",
	"3-5年": "104", "5-10年": "105", "10年以上": "106",
}

EDUCATION_CODES = {
	"大专": "202", "本科": "203", "硕士": "204", "博士": "205",
}

SCALE_CODES = {
	"0-20人": "301", "20-99人": "302", "100-499人": "303",
	"500-999人": "304", "1000-9999人": "305", "10000人以上": "306",
}
```

- [ ] **Step 4: 实现 models.py**

`src/boss_agent_cli/api/models.py`:
```python
from dataclasses import dataclass, field


@dataclass
class JobItem:
	job_id: str
	title: str
	company: str
	salary: str
	city: str
	experience: str
	education: str
	boss_name: str
	boss_title: str
	boss_active: str
	security_id: str
	greeted: bool = False

	@classmethod
	def from_api(cls, raw: dict) -> "JobItem":
		return cls(
			job_id=raw.get("encryptJobId", ""),
			title=raw.get("jobName", ""),
			company=raw.get("brandName", ""),
			salary=raw.get("salaryDesc", ""),
			city=raw.get("cityName", ""),
			experience=raw.get("jobExperience", ""),
			education=raw.get("jobDegree", ""),
			boss_name=raw.get("bossName", ""),
			boss_title=raw.get("bossTitle", ""),
			boss_active="在线" if raw.get("bossOnline") else "离线",
			security_id=raw.get("securityId", ""),
		)

	def to_dict(self) -> dict:
		return {
			"job_id": self.job_id,
			"title": self.title,
			"company": self.company,
			"salary": self.salary,
			"city": self.city,
			"experience": self.experience,
			"education": self.education,
			"boss_name": self.boss_name,
			"boss_title": self.boss_title,
			"boss_active": self.boss_active,
			"security_id": self.security_id,
			"greeted": self.greeted,
		}


@dataclass
class JobDetail:
	job_id: str
	title: str
	company: str
	salary: str
	city: str
	experience: str
	education: str
	description: str
	boss_name: str
	boss_title: str
	boss_active: str
	security_id: str
	company_info: dict = field(default_factory=dict)
	greeted: bool = False

	@classmethod
	def from_api(cls, raw: dict) -> "JobDetail":
		job_info = raw.get("jobInfo", {})
		boss_info = raw.get("bossInfo", {})
		brand_info = raw.get("brandComInfo", {})
		return cls(
			job_id=job_info.get("encryptJobId", ""),
			title=job_info.get("jobName", ""),
			company=brand_info.get("brandName", ""),
			salary=job_info.get("salaryDesc", ""),
			city=job_info.get("cityName", ""),
			experience=job_info.get("experienceName", ""),
			education=job_info.get("degreeName", ""),
			description=raw.get("jobDetail", ""),
			boss_name=boss_info.get("name", ""),
			boss_title=boss_info.get("title", ""),
			boss_active=boss_info.get("activeTimeDesc", "离线"),
			security_id=job_info.get("securityId", ""),
			company_info={
				"industry": brand_info.get("industryName", ""),
				"scale": brand_info.get("scaleName", ""),
				"stage": brand_info.get("stageName", ""),
			},
		)

	def to_dict(self) -> dict:
		return {
			"job_id": self.job_id,
			"title": self.title,
			"company": self.company,
			"salary": self.salary,
			"city": self.city,
			"experience": self.experience,
			"education": self.education,
			"description": self.description,
			"boss_name": self.boss_name,
			"boss_title": self.boss_title,
			"boss_active": self.boss_active,
			"security_id": self.security_id,
			"company_info": self.company_info,
			"greeted": self.greeted,
		}
```

- [ ] **Step 5: 实现 client.py（含重试上限）**

`src/boss_agent_cli/api/client.py`:
```python
import random
import time

import httpx

from boss_agent_cli.api import endpoints

_MAX_RETRIES = 2


class AuthError(Exception):
	pass


class BossClient:
	def __init__(self, auth_manager, *, delay: tuple[float, float] = (1.5, 3.0)):
		self._auth = auth_manager
		self._delay = delay
		self._client: httpx.Client | None = None

	def _get_client(self) -> httpx.Client:
		if self._client is None:
			token = self._auth.get_token()
			self._client = httpx.Client(
				base_url=endpoints.BASE_URL,
				cookies=token.get("cookies", {}),
				headers={
					"User-Agent": token.get("user_agent", "Mozilla/5.0"),
					"Referer": "https://www.zhipin.com/",
					"Accept": "application/json, text/plain, */*",
				},
				timeout=30,
			)
		return self._client

	def _wait(self):
		time.sleep(random.uniform(*self._delay))

	def _request(self, method: str, url: str, *, _retry_count: int = 0, **kwargs) -> dict:
		client = self._get_client()
		token = self._auth.get_token()
		stoken = token.get("stoken", "")

		if method == "GET":
			params = kwargs.get("params", {})
			params["__zp_stoken__"] = stoken
			kwargs["params"] = params

		self._wait()
		resp = client.request(method, url, **kwargs)

		if resp.status_code == 403 or "安全验证" in resp.text:
			if _retry_count >= _MAX_RETRIES:
				raise AuthError("Token 刷新后仍被拒绝，请重新登录")
			self._auth.force_refresh()
			self._client = None
			return self._request(method, url, _retry_count=_retry_count + 1, **kwargs)

		resp.raise_for_status()
		return resp.json()

	def search_jobs(self, query: str, **filters) -> dict:
		params = {"query": query, "page": filters.get("page", 1)}
		if city := filters.get("city"):
			code = endpoints.CITY_CODES.get(city)
			if code is None:
				raise ValueError(f"未知城市: {city}")
			params["city"] = code
		if salary := filters.get("salary"):
			code = endpoints.SALARY_CODES.get(salary)
			if code:
				params["salary"] = code
		if exp := filters.get("experience"):
			code = endpoints.EXPERIENCE_CODES.get(exp)
			if code:
				params["experience"] = code
		if edu := filters.get("education"):
			code = endpoints.EDUCATION_CODES.get(edu)
			if code:
				params["degree"] = code
		if scale := filters.get("scale"):
			code = endpoints.SCALE_CODES.get(scale)
			if code:
				params["scale"] = code
		if industry := filters.get("industry"):
			params["industry"] = industry
		return self._request("GET", endpoints.SEARCH_URL, params=params)

	def job_detail(self, job_id: str) -> dict:
		params = {"encryptJobId": job_id}
		return self._request("GET", endpoints.DETAIL_URL, params=params)

	def greet(self, security_id: str, job_id: str, message: str = "") -> dict:
		data = {
			"securityId": security_id,
			"jobId": job_id,
			"greeting": message or "您好，我对该岗位很感兴趣，希望能和您聊一聊。",
		}
		return self._request("POST", endpoints.GREET_URL, data=data)

	def user_info(self) -> dict:
		return self._request("GET", endpoints.USER_INFO_URL)
```

- [ ] **Step 6: 运行测试确认通过**

```bash
uv run pytest tests/test_api.py -v
```

Expected: 5 passed

- [ ] **Step 7: 提交**

```bash
git add src/boss_agent_cli/api/ tests/test_api.py
git commit -m "feat: 添加 API 层（端点、模型、客户端含重试上限）"
```

---

## Chunk 6: 浏览器登录 + AuthManager

### Task 6: Playwright 登录与 AuthManager

**Files:**
- Create: `src/boss_agent_cli/auth/browser.py`
- Create: `src/boss_agent_cli/auth/manager.py`

注意：AuthManager 中使用异常而非 sys.exit，让命令层统一处理错误输出。

- [ ] **Step 1: 实现 browser.py**

`src/boss_agent_cli/auth/browser.py`:
```python
import sys

from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

LOGIN_URL = "https://login.zhipin.com/?ka=header-login"
HOME_URL = "https://www.zhipin.com/"


def login_via_browser(*, timeout: int = 120) -> dict:
	with sync_playwright() as p:
		browser = p.chromium.launch(headless=False)
		context = browser.new_context()
		page = context.new_page()
		stealth_sync(page)

		page.goto(LOGIN_URL)
		print(f"请在浏览器中扫码登录（超时 {timeout} 秒）...", file=sys.stderr)

		page.wait_for_url(f"{HOME_URL}**", timeout=timeout * 1000)

		cookies_list = context.cookies()
		cookies = {c["name"]: c["value"] for c in cookies_list}
		user_agent = page.evaluate("navigator.userAgent")
		stoken = _extract_stoken(page)

		browser.close()

	return {
		"cookies": cookies,
		"stoken": stoken,
		"user_agent": user_agent,
	}


def refresh_stoken(cookies: dict, user_agent: str) -> str:
	with sync_playwright() as p:
		browser = p.chromium.launch(headless=True)
		context = browser.new_context(user_agent=user_agent)
		for name, value in cookies.items():
			context.add_cookies([{
				"name": name,
				"value": value,
				"domain": ".zhipin.com",
				"path": "/",
			}])
		page = context.new_page()
		stealth_sync(page)

		page.goto(HOME_URL)
		page.wait_for_load_state("networkidle")
		stoken = _extract_stoken(page)

		browser.close()

	return stoken


def _extract_stoken(page) -> str:
	try:
		stoken = page.evaluate("""
			() => {
				const match = document.cookie.match(/__zp_stoken__=([^;]+)/);
				return match ? match[1] : '';
			}
		""")
		if not stoken:
			stoken = page.evaluate("() => window.__zp_stoken__ || ''")
		return stoken
	except Exception:
		return ""
```

- [ ] **Step 2: 实现 manager.py（抛异常而非 sys.exit）**

`src/boss_agent_cli/auth/manager.py`:
```python
from pathlib import Path

from boss_agent_cli.auth.browser import login_via_browser, refresh_stoken
from boss_agent_cli.auth.token_store import TokenStore
from boss_agent_cli.output import Logger


class AuthRequired(Exception):
	pass


class TokenRefreshFailed(Exception):
	pass


class AuthManager:
	def __init__(self, data_dir: Path, *, logger: Logger | None = None):
		self._store = TokenStore(data_dir / "auth")
		self._token: dict | None = None
		self._logger = logger or Logger()

	def get_token(self) -> dict:
		if self._token is not None:
			return self._token
		self._token = self._store.load()
		if self._token is None:
			raise AuthRequired("未登录，请先执行 boss login")
		return self._token

	def login(self, *, timeout: int = 120) -> dict:
		token = login_via_browser(timeout=timeout)
		self._store.save(token)
		self._token = token
		return token

	def force_refresh(self) -> None:
		with self._store.refresh_lock():
			current = self._store.load()
			if current is None:
				raise TokenRefreshFailed("无法刷新 Token，请重新登录")
			self._logger.info("Token 过期，正在静默刷新...")
			try:
				new_stoken = refresh_stoken(
					current["cookies"],
					current.get("user_agent", ""),
				)
				current["stoken"] = new_stoken
				self._store.save(current)
				self._token = current
			except Exception as e:
				raise TokenRefreshFailed(f"Token 刷新失败: {e}") from e

	def check_status(self) -> dict | None:
		return self._store.load()
```

- [ ] **Step 3: 提交**

```bash
git add src/boss_agent_cli/auth/browser.py src/boss_agent_cli/auth/manager.py
git commit -m "feat: 添加 Playwright 登录和 AuthManager（异常驱动）"
```

---

## Chunk 7: CLI 命令层

### Task 7: 所有 CLI 命令

**Files:**
- Create: `src/boss_agent_cli/main.py`
- Create: `src/boss_agent_cli/commands/__init__.py`
- Create: `src/boss_agent_cli/commands/schema.py`
- Create: `src/boss_agent_cli/commands/login.py`
- Create: `src/boss_agent_cli/commands/status.py`
- Create: `src/boss_agent_cli/commands/search.py`
- Create: `src/boss_agent_cli/commands/detail.py`
- Create: `src/boss_agent_cli/commands/greet.py`

- [ ] **Step 1: 创建 commands/__init__.py**

`src/boss_agent_cli/commands/__init__.py`:
```python
```

- [ ] **Step 2: 实现 schema.py**

`src/boss_agent_cli/commands/schema.py`:
```python
import click

from boss_agent_cli.output import emit_success

SCHEMA_DATA = {
	"name": "boss-agent-cli",
	"description": "BOSS直聘求职工具。支持搜索职位、查看详情、向招聘者打招呼。",
	"commands": {
		"login": {
			"description": "扫码登录BOSS直聘，获取操作凭证。其他命令依赖登录态。",
			"args": {},
			"options": {
				"--timeout": {"type": "int", "default": 120, "description": "扫码等待超时（秒）"},
			},
		},
		"status": {
			"description": "检查当前登录态是否有效。",
			"args": {},
			"options": {},
		},
		"search": {
			"description": "按关键词和筛选条件搜索职位列表。",
			"args": {
				"query": {"type": "string", "required": True, "description": "搜索关键词，如 golang、产品经理"},
			},
			"options": {
				"--city": {"type": "string", "description": "城市名，如 北京、杭州"},
				"--salary": {"type": "string", "description": "薪资范围，如 20-50K"},
				"--experience": {"type": "string", "description": "经验要求", "enum": ["应届", "1年以内", "1-3年", "3-5年", "5-10年", "10年以上"]},
				"--education": {"type": "string", "description": "学历要求", "enum": ["大专", "本科", "硕士", "博士"]},
				"--industry": {"type": "string", "description": "行业，如 互联网、金融"},
				"--scale": {"type": "string", "description": "公司规模", "enum": ["0-20人", "20-99人", "100-499人", "500-999人", "1000-9999人", "10000人以上"]},
				"--page": {"type": "int", "default": 1, "description": "页码"},
				"--no-cache": {"type": "bool", "default": False, "description": "跳过缓存"},
			},
		},
		"detail": {
			"description": "查看指定职位的完整信息。",
			"args": {
				"job_id": {"type": "string", "required": True, "description": "职位ID，从search结果中获取"},
			},
			"options": {},
		},
		"greet": {
			"description": "向指定招聘者发送打招呼消息。",
			"args": {
				"security_id": {"type": "string", "required": True, "description": "招聘者ID，从search或detail结果中获取"},
				"job_id": {"type": "string", "required": True, "description": "职位ID，从search或detail结果中获取"},
			},
			"options": {
				"--message": {"type": "string", "description": "自定义打招呼内容"},
			},
		},
		"batch-greet": {
			"description": "搜索职位并批量向匹配的招聘者打招呼。",
			"args": {
				"query": {"type": "string", "required": True, "description": "搜索关键词"},
			},
			"options": {
				"--city": {"type": "string", "description": "城市名"},
				"--salary": {"type": "string", "description": "薪资范围"},
				"--count": {"type": "int", "default": 5, "description": "最多打招呼人数（上限10）"},
				"--dry-run": {"type": "bool", "default": False, "description": "预览模式，不实际发送"},
			},
		},
	},
	"global_options": {
		"--data-dir": {"type": "string", "default": "~/.boss-agent", "description": "数据存储目录"},
		"--delay": {"type": "string", "default": "1.5-3.0", "description": "请求间隔范围（秒）"},
		"--log-level": {"type": "string", "default": "error", "description": "日志级别", "enum": ["error", "warning", "info", "debug"]},
	},
	"error_codes": {
		"AUTH_EXPIRED": "登录态过期，需执行 boss login",
		"AUTH_REQUIRED": "未登录，需执行 boss login",
		"RATE_LIMITED": "请求频率过高，等待后重试",
		"TOKEN_REFRESH_FAILED": "Token刷新失败，需执行 boss login",
		"JOB_NOT_FOUND": "职位不存在或已下架",
		"ALREADY_GREETED": "已向该招聘者打过招呼",
		"GREET_LIMIT": "今日打招呼次数已用完",
		"NETWORK_ERROR": "网络请求失败",
		"INVALID_PARAM": "参数校验失败",
	},
	"conventions": {
		"stdout": "仅输出JSON结构化数据",
		"stderr": "日志和进度信息",
		"exit_code_0": "命令成功（ok=true）",
		"exit_code_1": "命令失败（ok=false）",
	},
}


@click.command("schema")
def schema_cmd():
	emit_success("schema", SCHEMA_DATA)
```

- [ ] **Step 3: 实现 login.py**

`src/boss_agent_cli/commands/login.py`:
```python
import click

from boss_agent_cli.auth.manager import AuthManager
from boss_agent_cli.output import emit_success, emit_error


@click.command("login")
@click.option("--timeout", default=120, help="扫码等待超时（秒）")
@click.pass_context
def login_cmd(ctx, timeout):
	auth = AuthManager(ctx.obj["data_dir"], logger=ctx.obj["logger"])
	try:
		token = auth.login(timeout=timeout)
		emit_success("login", {"message": "登录成功"})
	except Exception as e:
		emit_error(
			"login",
			code="AUTH_EXPIRED",
			message=f"登录失败: {e}",
			recoverable=True,
			recovery_action="boss login",
		)
```

- [ ] **Step 4: 实现 status.py**

`src/boss_agent_cli/commands/status.py`:
```python
import click

from boss_agent_cli.auth.manager import AuthManager, AuthRequired
from boss_agent_cli.api.client import BossClient
from boss_agent_cli.output import emit_success, emit_error


@click.command("status")
@click.pass_context
def status_cmd(ctx):
	auth = AuthManager(ctx.obj["data_dir"], logger=ctx.obj["logger"])
	token = auth.check_status()

	if token is None:
		emit_error(
			"status",
			code="AUTH_REQUIRED",
			message="未登录",
			recoverable=True,
			recovery_action="boss login",
			hints={"next_actions": ["boss login — 扫码登录"]},
		)

	try:
		client = BossClient(auth, delay=(0.1, 0.2))
		info = client.user_info()
		user = info.get("zpData", {}).get("user", {})
		emit_success("status", {
			"logged_in": True,
			"user_name": user.get("name", "未知"),
			"token_expires_in": None,
		})
	except Exception:
		emit_error(
			"status",
			code="AUTH_EXPIRED",
			message="登录态已过期",
			recoverable=True,
			recovery_action="boss login",
		)
```

- [ ] **Step 5: 实现 search.py**

`src/boss_agent_cli/commands/search.py`:
```python
import json as json_mod

import click

from boss_agent_cli.api.client import BossClient
from boss_agent_cli.api.endpoints import CITY_CODES
from boss_agent_cli.api.models import JobItem
from boss_agent_cli.auth.manager import AuthManager, AuthRequired, TokenRefreshFailed
from boss_agent_cli.cache.store import CacheStore
from boss_agent_cli.output import emit_success, emit_error


@click.command("search")
@click.argument("query")
@click.option("--city", default=None)
@click.option("--salary", default=None)
@click.option("--experience", default=None)
@click.option("--education", default=None)
@click.option("--industry", default=None)
@click.option("--scale", default=None)
@click.option("--page", default=1, type=int)
@click.option("--no-cache", is_flag=True, default=False)
@click.pass_context
def search_cmd(ctx, query, city, salary, experience, education, industry, scale, page, no_cache):
	if city and city not in CITY_CODES:
		emit_error("search", code="INVALID_PARAM", message=f"未知城市: {city}")

	data_dir = ctx.obj["data_dir"]
	cache = CacheStore(data_dir / "cache" / "boss_agent.db")

	cache_params = {
		k: v for k, v in {
			"query": query, "city": city, "salary": salary,
			"experience": experience, "education": education,
			"industry": industry, "scale": scale, "page": str(page),
		}.items() if v is not None
	}

	if not no_cache:
		cached = cache.get_search(cache_params)
		if cached is not None:
			emit_success("search", json_mod.loads(cached))
			return

	try:
		auth = AuthManager(data_dir, logger=ctx.obj["logger"])
		client = BossClient(auth, delay=ctx.obj["delay"])

		filters = {"page": page}
		for key, val in [("city", city), ("salary", salary), ("experience", experience),
						("education", education), ("scale", scale), ("industry", industry)]:
			if val:
				filters[key] = val

		raw = client.search_jobs(query, **filters)
		job_list = raw.get("zpData", {}).get("jobList", [])
		total = raw.get("zpData", {}).get("totalCount", 0)

		jobs = []
		for item in job_list:
			job = JobItem.from_api(item)
			job.greeted = cache.is_greeted(job.security_id)
			jobs.append(job.to_dict())

		total_pages = max(1, (total + 14) // 15)
		result = {"jobs": jobs}
		pagination = {
			"page": page,
			"total_pages": total_pages,
			"total_count": total,
			"has_next": page < total_pages,
		}

		cache.put_search(cache_params, json_mod.dumps(result, ensure_ascii=False))

		hints = {"next_actions": []}
		if pagination["has_next"]:
			hints["next_actions"].append(f"boss search {query} --page {page + 1} — 下一页")
		if jobs:
			hints["next_actions"].append("boss detail <job_id> — 查看职位详情")
			hints["next_actions"].append("boss greet <security_id> <job_id> — 向招聘者打招呼")

		emit_success("search", result, pagination=pagination, hints=hints)

	except AuthRequired:
		emit_error("search", code="AUTH_REQUIRED", message="未登录", recoverable=True, recovery_action="boss login")
	except TokenRefreshFailed as e:
		emit_error("search", code="TOKEN_REFRESH_FAILED", message=str(e), recoverable=True, recovery_action="boss login")
	except ValueError as e:
		emit_error("search", code="INVALID_PARAM", message=str(e))
	except Exception as e:
		emit_error("search", code="NETWORK_ERROR", message=str(e))
```

- [ ] **Step 6: 实现 detail.py**

`src/boss_agent_cli/commands/detail.py`:
```python
import click

from boss_agent_cli.api.client import BossClient
from boss_agent_cli.api.models import JobDetail
from boss_agent_cli.auth.manager import AuthManager, AuthRequired, TokenRefreshFailed
from boss_agent_cli.cache.store import CacheStore
from boss_agent_cli.output import emit_success, emit_error


@click.command("detail")
@click.argument("job_id")
@click.pass_context
def detail_cmd(ctx, job_id):
	data_dir = ctx.obj["data_dir"]
	cache = CacheStore(data_dir / "cache" / "boss_agent.db")

	try:
		auth = AuthManager(data_dir, logger=ctx.obj["logger"])
		client = BossClient(auth, delay=ctx.obj["delay"])

		raw = client.job_detail(job_id)
		zp_data = raw.get("zpData", {})
		detail = JobDetail.from_api(zp_data)
		detail.greeted = cache.is_greeted(detail.security_id)

		hints = {"next_actions": [
			f"boss greet {detail.security_id} {detail.job_id} — 向该招聘者打招呼",
		]}
		emit_success("detail", detail.to_dict(), hints=hints)

	except AuthRequired:
		emit_error("detail", code="AUTH_REQUIRED", message="未登录", recoverable=True, recovery_action="boss login")
	except TokenRefreshFailed as e:
		emit_error("detail", code="TOKEN_REFRESH_FAILED", message=str(e), recoverable=True, recovery_action="boss login")
	except Exception as e:
		emit_error("detail", code="JOB_NOT_FOUND", message=str(e))
```

- [ ] **Step 7: 实现 greet.py（含 batch-greet 上限 + NETWORK_ERROR 重试）**

`src/boss_agent_cli/commands/greet.py`:
```python
import random
import time

import click

from boss_agent_cli.api.client import BossClient
from boss_agent_cli.api.models import JobItem
from boss_agent_cli.auth.manager import AuthManager, AuthRequired, TokenRefreshFailed
from boss_agent_cli.cache.store import CacheStore
from boss_agent_cli.output import emit_success, emit_error

_BATCH_MAX = 10


@click.command("greet")
@click.argument("security_id")
@click.argument("job_id")
@click.option("--message", default=None, help="自定义打招呼内容")
@click.pass_context
def greet_cmd(ctx, security_id, job_id, message):
	data_dir = ctx.obj["data_dir"]
	cache = CacheStore(data_dir / "cache" / "boss_agent.db")

	if cache.is_greeted(security_id):
		emit_error("greet", code="ALREADY_GREETED", message="已向该招聘者打过招呼")

	try:
		auth = AuthManager(data_dir, logger=ctx.obj["logger"])
		client = BossClient(auth, delay=ctx.obj["delay"])
		client.greet(security_id, job_id, message or "")
		cache.record_greet(security_id, job_id)
		emit_success("greet", {"security_id": security_id, "job_id": job_id, "status": "sent"})
	except AuthRequired:
		emit_error("greet", code="AUTH_REQUIRED", message="未登录", recoverable=True, recovery_action="boss login")
	except TokenRefreshFailed as e:
		emit_error("greet", code="TOKEN_REFRESH_FAILED", message=str(e), recoverable=True, recovery_action="boss login")
	except Exception as e:
		error_msg = str(e)
		if "上限" in error_msg or "limit" in error_msg.lower():
			emit_error("greet", code="GREET_LIMIT", message="今日打招呼次数已用完")
		elif "频繁" in error_msg or "rate" in error_msg.lower():
			emit_error("greet", code="RATE_LIMITED", message="请求频率过高")
		else:
			emit_error("greet", code="NETWORK_ERROR", message=error_msg)


@click.command("batch-greet")
@click.argument("query")
@click.option("--city", default=None)
@click.option("--salary", default=None)
@click.option("--count", default=5, type=int, help="最多打招呼人数")
@click.option("--dry-run", is_flag=True, default=False, help="预览模式")
@click.pass_context
def batch_greet_cmd(ctx, query, city, salary, count, dry_run):
	count = min(count, _BATCH_MAX)
	data_dir = ctx.obj["data_dir"]
	logger = ctx.obj["logger"]
	cache = CacheStore(data_dir / "cache" / "boss_agent.db")

	try:
		auth = AuthManager(data_dir, logger=logger)
		client = BossClient(auth, delay=ctx.obj["delay"])

		filters = {"page": 1}
		if city:
			filters["city"] = city
		if salary:
			filters["salary"] = salary

		raw = client.search_jobs(query, **filters)
		job_list = raw.get("zpData", {}).get("jobList", [])

		targets = []
		for item in job_list:
			job = JobItem.from_api(item)
			if cache.is_greeted(job.security_id):
				continue
			targets.append(job)
			if len(targets) >= count:
				break

		if dry_run:
			emit_success("batch-greet", {
				"dry_run": True,
				"total": len(targets),
				"targets": [t.to_dict() for t in targets],
			})
			return

		results = []
		for job in targets:
			try:
				client.greet(job.security_id, job.job_id)
				cache.record_greet(job.security_id, job.job_id)
				results.append({
					"security_id": job.security_id,
					"job_title": job.title,
					"company": job.company,
					"status": "sent",
				})
				delay = random.uniform(2.0, 5.0)
				logger.info(f"已打招呼: {job.company} - {job.title}，等待 {delay:.1f}s...")
				time.sleep(delay)
			except Exception as e:
				error_msg = str(e)
				if "上限" in error_msg or "limit" in error_msg.lower():
					results.append({"security_id": job.security_id, "job_title": job.title, "status": "failed", "error": "GREET_LIMIT"})
					break
				elif "频繁" in error_msg or "rate" in error_msg.lower():
					results.append({"security_id": job.security_id, "job_title": job.title, "status": "failed", "error": "RATE_LIMITED"})
					break
				else:
					# NETWORK_ERROR: 重试一次
					try:
						time.sleep(2)
						client.greet(job.security_id, job.job_id)
						cache.record_greet(job.security_id, job.job_id)
						results.append({"security_id": job.security_id, "job_title": job.title, "status": "sent"})
					except Exception:
						results.append({"security_id": job.security_id, "job_title": job.title, "status": "failed", "error": "NETWORK_ERROR"})
						continue

		succeeded = sum(1 for r in results if r["status"] == "sent")
		failed = sum(1 for r in results if r["status"] == "failed")

		emit_success("batch-greet", {
			"total": len(results),
			"succeeded": succeeded,
			"failed": failed,
			"results": results,
		})

	except AuthRequired:
		emit_error("batch-greet", code="AUTH_REQUIRED", message="未登录", recoverable=True, recovery_action="boss login")
	except TokenRefreshFailed as e:
		emit_error("batch-greet", code="TOKEN_REFRESH_FAILED", message=str(e), recoverable=True, recovery_action="boss login")
	except ValueError as e:
		emit_error("batch-greet", code="INVALID_PARAM", message=str(e))
	except Exception as e:
		emit_error("batch-greet", code="NETWORK_ERROR", message=str(e))
```

- [ ] **Step 8: 实现 main.py（加载配置 + Logger）**

`src/boss_agent_cli/main.py`:
```python
from pathlib import Path

import click

from boss_agent_cli.commands import schema, login, status, search, detail, greet
from boss_agent_cli.config import load_config
from boss_agent_cli.output import Logger


@click.group()
@click.option("--data-dir", default="~/.boss-agent", help="数据存储目录")
@click.option("--delay", default=None, help="请求间隔范围（秒），如 1.5-3.0")
@click.option("--log-level", default=None, type=click.Choice(["error", "warning", "info", "debug"]))
@click.pass_context
def cli(ctx, data_dir, delay, log_level):
	ctx.ensure_object(dict)
	data_dir = Path(data_dir).expanduser()
	data_dir.mkdir(parents=True, exist_ok=True)
	ctx.obj["data_dir"] = data_dir

	cfg = load_config(data_dir / "config.json")

	if delay:
		low, high = delay.split("-")
		ctx.obj["delay"] = (float(low), float(high))
	else:
		ctx.obj["delay"] = tuple(cfg["request_delay"])

	level = log_level or cfg["log_level"]
	ctx.obj["log_level"] = level
	ctx.obj["logger"] = Logger(level)


cli.add_command(schema.schema_cmd, "schema")
cli.add_command(login.login_cmd, "login")
cli.add_command(status.status_cmd, "status")
cli.add_command(search.search_cmd, "search")
cli.add_command(detail.detail_cmd, "detail")
cli.add_command(greet.greet_cmd, "greet")
cli.add_command(greet.batch_greet_cmd, "batch-greet")
```

- [ ] **Step 9: 提交**

```bash
git add src/boss_agent_cli/main.py src/boss_agent_cli/commands/
git commit -m "feat: 添加全部 CLI 命令"
```

---

## Chunk 8: 命令层测试

### Task 8: CLI 命令测试（mock API）

**Files:**
- Create: `tests/test_commands.py`

- [ ] **Step 1: 编写命令层测试**

`tests/test_commands.py`:
```python
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


@patch("boss_agent_cli.commands.search.BossClient")
@patch("boss_agent_cli.commands.search.AuthManager")
def test_search_invalid_city(mock_auth_cls, mock_client_cls):
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
	assert parsed["data"]["total"] == 1
```

- [ ] **Step 2: 运行测试**

```bash
uv run pytest tests/test_commands.py -v
```

Expected: 5 passed

- [ ] **Step 3: 运行全部测试**

```bash
uv run pytest tests/ -v
```

Expected: 所有测试通过（21+ tests）

- [ ] **Step 4: 提交**

```bash
git add tests/test_commands.py
git commit -m "test: 添加命令层测试"
```

---

## Chunk 9: 集成验证 + README

### Task 9: 端到端验证 + 文档

**Files:**
- Create: `README.md`

- [ ] **Step 1: 验证 CLI 入口**

```bash
cd /Users/can4hou6joeng4/Documents/code/boss-agent-cli
uv run boss schema | python -m json.tool
```

Expected: 格式化 JSON 输出含所有命令定义

- [ ] **Step 2: 验证 --help**

```bash
uv run boss --help
uv run boss search --help
```

Expected: 正确显示所有命令和选项

- [ ] **Step 3: 创建 README.md**

`README.md`:
````markdown
# boss-agent-cli

专为 AI Agent 设计的 BOSS 直聘求职 CLI 工具。所有输出为结构化 JSON，通过 stdout 输出。

## 安装

```bash
uv tool install boss-agent-cli
playwright install chromium
```

## AI Agent 集成

Agent 首次接触工具时调用 `boss schema` 获取完整能力描述：

```bash
boss schema
```

典型调用链：

```bash
boss schema                                    # 理解工具能力
boss status                                    # 检查登录态
boss login                                     # 扫码登录（需用户手动扫码）
boss search "golang" --city 杭州 --salary 20-50K  # 搜索职位
boss detail <job_id>                           # 查看详情
boss greet <security_id> <job_id>              # 打招呼
boss batch-greet "golang" --city 杭州 --count 5   # 批量打招呼
```

## 输出格式

```json
{
  "ok": true,
  "schema_version": "1.0",
  "command": "search",
  "data": {},
  "pagination": null,
  "error": null,
  "hints": {"next_actions": ["boss detail <job_id> — 查看详情"]}
}
```

- `stdout`: JSON 数据
- `stderr`: 日志（通过 `--log-level` 控制）
- `exit 0`: 成功
- `exit 1`: 失败

## 配置

`~/.boss-agent/config.json`:

```json
{
  "default_city": null,
  "default_salary": null,
  "request_delay": [1.5, 3.0],
  "batch_greet_delay": [2.0, 5.0],
  "batch_greet_max": 10,
  "log_level": "error",
  "login_timeout": 120
}
```

## 许可证

MIT
````

- [ ] **Step 4: 最终提交**

```bash
git add README.md
git commit -m "docs: 添加 README"
```
