[根目录](../../CLAUDE.md) > [src/boss_agent_cli](..) > **api**

# api 模块

## 模块职责

BOSS 直聘 wapi 接口封装层：端点常量定义、城市/薪资/经验/学历/规模编码映射、响应数据模型 (dataclass)、httpx 统一请求入口（含 stoken 注入和 403 重试）。

## 入口与启动

- **BossClient** (`client.py`)：对外暴露的统一请求入口
  - 通过 AuthManager 获取 Token，自动注入 Cookie 和 `__zp_stoken__`
  - 403 响应或"安全验证"触发 `auth_manager.force_refresh()` 并重试（最多 2 次）
  - 每次请求前随机延迟 1-3s（反爬）

## 对外接口

### BossClient 公开方法

```python
class BossClient:
    def __init__(self, auth_manager, *, delay: tuple[float, float] = (1.5, 3.0))
    def search_jobs(self, query: str, **filters) -> dict
    def job_detail(self, job_id: str) -> dict
    def greet(self, security_id: str, job_id: str, message: str = "") -> dict
    def user_info(self) -> dict
```

### 异常类

| 异常 | 含义 |
|------|------|
| `AuthError` | Token 刷新后仍被拒绝，需重新登录 |

### 端点常量 (`endpoints.py`)

| 常量 | URL |
|------|-----|
| `SEARCH_URL` | `/wapi/zpgeek/search/joblist.json` |
| `DETAIL_URL` | `/wapi/zpgeek/job/detail.json` |
| `GREET_URL` | `/wapi/zpgeek/friend/add.json` |
| `USER_INFO_URL` | `/wapi/zpgeek/common/user/info.json` |

### 编码映射表

- `CITY_CODES`: 35+ 城市名 -> 编码
- `SALARY_CODES`: 7 档薪资范围 -> 编码
- `EXPERIENCE_CODES`: 6 档经验要求 -> 编码
- `EDUCATION_CODES`: 4 档学历要求 -> 编码
- `SCALE_CODES`: 6 档公司规模 -> 编码

## 关键依赖与配置

- `httpx`: HTTP 客户端
- `auth/manager.py` 的 `AuthManager`: Token 提供者
- 重试上限 `_MAX_RETRIES = 2`

## 数据模型

### JobItem (搜索结果)

```python
@dataclass
class JobItem:
    job_id, title, company, salary, city, experience,
    education, boss_name, boss_title, boss_active,
    security_id, greeted
```

- `from_api(raw: dict) -> JobItem`: 从 API 原始数据构造
- `to_dict() -> dict`: 序列化为输出字典

### JobDetail (职位详情)

```python
@dataclass
class JobDetail:
    job_id, title, company, salary, city, experience,
    education, description, boss_name, boss_title,
    boss_active, security_id, company_info, greeted
```

- `company_info` 包含 `industry`, `scale`, `stage` 三个字段

## 测试与质量

- 测试文件：`tests/test_api.py`
- 覆盖：城市编码查找、薪资编码查找、经验编码查找、JobItem.from_api、JobItem.to_dict
- 注意：BossClient 依赖外部 API，未做单元测试（命令层测试中通过 mock 覆盖）

## 相关文件清单

| 文件 | 职责 |
|------|------|
| `__init__.py` | 包初始化 |
| `endpoints.py` | wapi 端点常量 + 城市/薪资/经验/学历/规模映射表 |
| `models.py` | JobItem / JobDetail dataclass |
| `client.py` | BossClient: httpx 请求 + Token 注入 + 403 重试 |

## 变更记录 (Changelog)

| 日期 | 操作 | 说明 |
|------|------|------|
| 2026-03-20 | 初始创建 | 基于设计规范生成，预实现阶段 |
