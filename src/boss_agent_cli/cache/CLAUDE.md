[根目录](../../CLAUDE.md) > [src/boss_agent_cli](..) > **cache**

# cache 模块

## 模块职责

SQLite WAL 模式轻量缓存，存储搜索历史和已打招呼记录。支持多进程并发读取。

## 入口与启动

- **CacheStore** (`store.py`)：唯一对外接口
  - 初始化时自动创建目录、数据库文件、表结构
  - 自动开启 `PRAGMA journal_mode=WAL`

## 对外接口

### CacheStore 公开方法

```python
class CacheStore:
    def __init__(self, db_path: Path, *, search_ttl_seconds: int = 86400)

    # 打招呼记录
    def is_greeted(self, security_id: str) -> bool
    def get_job_id(self, security_id: str) -> str | None
    def record_greet(self, security_id: str, job_id: str) -> None

    # 搜索缓存
    def get_search(self, params: dict) -> str | None
    def put_search(self, params: dict, response: str) -> None

    def close(self) -> None
```

## 关键依赖与配置

- `sqlite3`（标准库）
- 搜索缓存 TTL: 24 小时 (86400s)
- 搜索缓存上限: 100 条（LRU 淘汰最早条目）
- 缓存键: `sha256(json.dumps(params, sort_keys=True))`

## 数据模型

### 表结构

```sql
-- 打招呼记录（永久保留）
CREATE TABLE greet_records (
    security_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    greeted_at REAL NOT NULL
);

-- 搜索缓存（24h 过期，上限 100 条）
CREATE TABLE search_cache (
    cache_key TEXT PRIMARY KEY,
    response TEXT NOT NULL,
    created_at REAL NOT NULL
);
```

**存储路径**: `~/.boss-agent/cache/boss_agent.db`

## 测试与质量

- 测试文件: `tests/test_cache.py`
- 覆盖: 打招呼记录 CRUD、搜索缓存命中/未命中/过期/不同参数、100 条上限淘汰
- 共 7 个测试用例

## 常见问题 (FAQ)

**Q: 搜索缓存键如何计算？**
A: `sha256(query + city + salary + experience + education + industry + scale + page)` -- 不同筛选条件组合、不同页码视为不同条目。

**Q: 如何跳过缓存？**
A: `boss search <query> --no-cache`

## 相关文件清单

| 文件 | 职责 |
|------|------|
| `__init__.py` | 包初始化 |
| `store.py` | CacheStore: SQLite WAL 缓存 + LRU 淘汰 |

## 变更记录 (Changelog)

| 日期 | 操作 | 说明 |
|------|------|------|
| 2026-03-20 | 初始创建 | 基于设计规范生成，预实现阶段 |
