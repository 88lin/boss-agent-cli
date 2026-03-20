# boss-agent-cli 设计规范

## 概述

结合 geekgeekrun（浏览器自动化 + 反检测）和 boss-cli（CLI + 结构化输出）的优势，构建一个专为 AI Agent 设计的 BOSS 直聘求职 CLI 工具。

**核心定位**：AI Agent 通过 subprocess 调用 CLI，读取 stdout JSON 输出，完成求职操作链。

## 技术选型

| 类别 | 选型 | 理由 |
|------|------|------|
| 语言 | Python >=3.10 | 生态成熟，Playwright 原生支持 |
| CLI 框架 | Click | Python CLI 标准选择 |
| HTTP 客户端 | httpx | 异步友好，Cookie 管理优秀 |
| 浏览器自动化 | Playwright + playwright-stealth | 登录 + Token 刷新 |
| 数据库 | sqlite3（标准库） | 轻量缓存，零额外依赖 |
| 包管理 | uv + hatchling | 现代 Python 构建工具链 |

## 项目结构

```
boss-agent-cli/
├── pyproject.toml
├── README.md
├── src/boss_agent_cli/
│   ├── __init__.py
│   ├── main.py                 # CLI 入口 (Click group)
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── login.py            # boss login
│   │   ├── status.py           # boss status
│   │   ├── search.py           # boss search
│   │   ├── detail.py           # boss detail
│   │   ├── greet.py            # boss greet / boss batch-greet
│   │   └── schema.py           # boss schema
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── manager.py          # AuthManager — Token 生命周期
│   │   ├── browser.py          # Playwright 无头浏览器登录
│   │   └── token_store.py      # Token/Cookie 加密持久化
│   ├── api/
│   │   ├── __init__.py
│   │   ├── client.py           # BossClient — httpx 统一请求入口
│   │   ├── endpoints.py        # wapi 端点常量定义
│   │   └── models.py           # 响应数据模型 (dataclass)
│   ├── cache/
│   │   ├── __init__.py
│   │   └── store.py            # SQLite 缓存（搜索历史、已打招呼记录）
│   └── output.py               # 结构化 JSON 信封
└── tests/
    ├── test_auth.py
    ├── test_api.py
    ├── test_commands.py
    ├── test_cache.py
    └── test_output.py
```

## 架构

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  CLI 入口    │────>│  AuthManager     │────>│  Playwright      │
│  (Click)    │     │  (Token 生命周期)  │     │  (Headless)      │
└──────┬──────┘     └────────┬─────────┘     └──────────────────┘
       │                     │ Cookie + Token
       v                     v
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  BossClient  │────>│  BOSS 直聘    │     │  SQLite      │
│  (httpx)     │     │  wapi 接口    │     │  (轻量缓存)   │
└──────┬───────┘     └──────────────┘     └──────────────┘
       │
       v
┌──────────────┐
│  output.py   │──── JSON 信封 ──── stdout
│  (信封格式)   │
└──────────────┘
```

**数据流**：CLI 命令 -> AuthManager 确保有效 Token -> BossClient 发起 API 请求 -> output.py 格式化为 JSON 信封 -> stdout

## 结构化输出协议

### 信封格式

所有命令输出统一格式：

```json
{
  "ok": true,
  "schema_version": "1.0",
  "command": "search",
  "data": {},
  "pagination": null,
  "error": null,
  "hints": null
}
```

### 字段定义

| 字段 | 类型 | 说明 |
|------|------|------|
| ok | bool | 是否成功 |
| schema_version | string | 输出格式版本 |
| command | string | 当前命令名 |
| data | object/list/null | 业务数据 |
| pagination | object/null | 分页（仅列表命令） |
| error | object/null | 错误详情 |
| hints | object/null | Agent 行动建议 |

### 分页对象

```json
{
  "page": 1,
  "total_pages": 12,
  "total_count": 120,
  "has_next": true
}
```

### 错误对象

```json
{
  "code": "AUTH_EXPIRED",
  "message": "登录态已过期",
  "recoverable": true,
  "recovery_action": "boss login"
}
```

### 错误码枚举

| 错误码 | 说明 |
|--------|------|
| AUTH_EXPIRED | 登录态过期，需执行 boss login |
| AUTH_REQUIRED | 未登录，需执行 boss login |
| RATE_LIMITED | 请求频率过高，等待后重试 |
| TOKEN_REFRESH_FAILED | Token 刷新失败，需执行 boss login |
| JOB_NOT_FOUND | 职位不存在或已下架 |
| ALREADY_GREETED | 已向该招聘者打过招呼 |
| GREET_LIMIT | 今日打招呼次数已用完 |
| NETWORK_ERROR | 网络请求失败 |
| INVALID_PARAM | 参数校验失败（无效城市、格式错误等） |

### hints 示例

搜索无结果时：
```json
{
  "next_actions": [
    "boss search <query> --salary 15-25K — 尝试放宽薪资范围",
    "boss search <query> --city 上海 — 尝试其他城市"
  ]
}
```

搜索成功时：
```json
{
  "next_actions": [
    "boss detail <job_id> — 查看职位详情",
    "boss search <query> --page 2 — 下一页",
    "boss greet <security_id> — 向招聘者打招呼"
  ]
}
```

### 输出约定

- stdout：仅 JSON 结构化数据
- stderr：日志和进度信息（通过 --log-level 控制级别：error/warning/info/debug，默认 error）
- exit code 0：命令成功（ok=true）
- exit code 1：命令失败（ok=false）

## Agent 自描述协议

`boss schema` 命令返回工具完整能力描述，Agent 调用一次即可理解所有命令、参数、错误码和约定。包含：

- commands：所有命令及其参数、选项、类型、默认值、描述
- error_codes：所有错误码及说明
- conventions：stdout/stderr/exit_code 约定

Agent 典型调用链：
```
boss schema   -> 理解能力
boss status   -> 检查登录态
boss login    -> 若未登录，提示用户扫码
boss search   -> 搜索职位（返回含 security_id 的列表）
boss detail   -> 查看详情（可选步骤，返回也含 security_id）
boss greet    -> 打招呼（security_id 可从 search 或 detail 获取）
```

注意：`boss detail` 不是 `boss greet` 的必要前置步骤。Agent 可从 `boss search` 结果中直接获取 `security_id` 进行打招呼。

## 命令定义

### boss login

扫码登录 BOSS 直聘。

```
boss login [--timeout 120]
```

启动 Playwright Chromium 打开登录页，终端输出二维码 URL，等待用户扫码。登录成功后提取 Cookie/Token 并加密存储到本地。

### boss status

检查当前登录态。

```
boss status
```

返回 logged_in、user_name、token_expires_in。

### boss search

按关键词和筛选条件搜索职位。

```
boss search <query> [--city] [--salary] [--experience] [--education] [--industry] [--scale] [--page] [--no-cache]
```

参数格式说明：
- `--city`：城市名中文字符串，如 "北京"、"杭州"、"深圳"。CLI 内部维护城市名到城市编码的映射表。无效城市名返回 INVALID_PARAM 错误
- `--salary`：格式为 "下限-上限K"，如 "10-20K"、"20-50K"。CLI 内部映射到 BOSS 直聘薪资编码
- `--experience`：枚举值 "应届"、"1年以内"、"1-3年"、"3-5年"、"5-10年"、"10年以上"
- `--education`：枚举值 "大专"、"本科"、"硕士"、"博士"
- `--industry`：行业名中文字符串，如 "互联网"、"金融"
- `--scale`：枚举值 "0-20人"、"20-99人"、"100-499人"、"500-999人"、"1000-9999人"、"10000人以上"
- `--page`：整数页码，默认 1
- `--no-cache`：跳过缓存，强制请求 BOSS 直聘 API

返回职位列表，每个职位包含 job_id、title、company、salary、city、experience、education、boss_name、boss_title、boss_active、security_id、greeted 字段。

### boss detail

查看职位完整信息。

```
boss detail <job_id>
```

返回职位详情，包含 description、company_info、security_id 等完整字段。security_id 可直接用于 greet 命令。

### boss greet

向指定招聘者打招呼。

```
boss greet <security_id> [--message]
```

发送打招呼消息，记录到本地缓存。security_id 可从 search 或 detail 结果中获取。

### boss batch-greet

批量打招呼。

```
boss batch-greet <query> [--city] [--salary] [--count 5] [--dry-run]
```

搜索职位后逐个打招呼，每个间隔 2-5s 随机延迟。dry-run 模式仅预览不发送。

**批量错误处理策略**：
- 遇到 ALREADY_GREETED：跳过该条，继续下一个
- 遇到 RATE_LIMITED：停止剩余操作，返回已完成的结果
- 遇到 GREET_LIMIT：停止剩余操作，返回已完成的结果
- 遇到 NETWORK_ERROR：重试一次，仍失败则跳过继续
- 结果逐条报告，每条含独立的 status 字段（sent/skipped/failed）

### boss schema

返回工具完整能力描述的 JSON。

```
boss schema
```

## 登录态管理

### Token 体系

BOSS 直聘的认证涉及以下 Token：
- **Cookie（wt2 等）**：核心身份凭证，登录后由服务端设置，有效期通常数天
- **`__zp_stoken__`**：前端 JS 运行时生成的防爬 Token，附加在 API 请求参数中。每次页面加载时由 JS 生成，有效期较短（分钟级别）

### __zp_stoken__ 获取策略

`__zp_stoken__` 不是每次 API 请求都需要浏览器生成。采用以下策略：

1. **登录时批量提取**：登录成功后，Playwright 在浏览器环境中执行 JS 提取当前 stoken，连同 Cookie 一起缓存
2. **按需刷新**：当 API 返回 403 或响应中包含安全验证标记时，判定 stoken 过期
3. **静默刷新流程**：启动 Playwright 无头实例 -> 加载 BOSS 直聘任意已登录页面（如首页） -> 等待 JS 执行完成 -> 从页面中提取新 stoken -> 更新本地缓存 -> 关闭浏览器实例
4. **刷新不需要用户介入**：因为 Cookie（wt2）仍有效，浏览器打开页面时自动处于登录态

**AuthManager 与 BossClient 的交互**：
- BossClient 每次请求前调用 `auth_manager.get_token()` 获取 Cookie + stoken
- AuthManager 内部判断 stoken 是否需要刷新，对 BossClient 透明
- BossClient 收到 403 时调用 `auth_manager.force_refresh()` 强制刷新后重试

### 登录流程

1. 检查 `~/.boss-agent/auth/session.enc` 是否存在且有效
2. 有效则直接使用
3. 无效则启动 Playwright Chromium（stealth 模式），打开 BOSS 直聘登录页
4. 输出二维码 URL 到 JSON（Agent 提示用户扫码）
5. 登录成功后提取 Cookie + stoken
6. 加密存储到本地

### Token 有效性判断

- **Cookie 有效性**：调用 BOSS 直聘用户信息接口（如 /wapi/zpgeek/common/user/info），返回 200 且含用户数据则有效
- **stoken 有效性**：不主动判断过期时间，而是在 API 调用返回 403 或安全验证页面时触发刷新（惰性策略）

### 并发锁机制

多个 CLI 进程可能同时触发 Token 刷新。采用文件锁避免冲突：
- 刷新时创建 `~/.boss-agent/auth/refresh.lock` 文件锁
- 其他进程检测到锁存在时等待（最多 30s），锁释放后重新读取缓存
- 锁超时自动释放（防止死锁）

### 密钥管理

Token 加密存储使用 Fernet 对称加密（cryptography 库），密钥派生方案：
- 使用机器唯一标识（macOS: IOPlatformUUID, Linux: /etc/machine-id, Windows: MachineGuid 注册表项）作为输入
- 通过 PBKDF2-HMAC-SHA256（迭代 480000 次）派生 256 位密钥
- 固定 salt 存储在 `~/.boss-agent/auth/salt`（首次生成随机 16 字节）
- 换机器后需重新登录（因为机器标识不同，无法解密旧 session）

### 本地存储

```
~/.boss-agent/
├── auth/
│   ├── session.enc          # Fernet 加密的 Cookie/Token/stoken
│   ├── salt                 # PBKDF2 salt（16 字节随机值）
│   └── refresh.lock         # 文件锁（刷新时临时创建）
├── cache/
│   └── boss_agent.db        # SQLite（WAL 模式）
└── config.json              # 用户配置
```

## 反爬策略

| 层级 | 措施 | 说明 |
|------|------|------|
| 浏览器指纹 | playwright-stealth | 隐藏自动化特征 |
| 请求头 | 真实浏览器 UA/Referer/Accept | 从 Playwright 提取请求头模板 |
| Token 来源 | 浏览器 JS 运行时生成 | __zp_stoken__ 天然合法 |
| 请求频率 | 随机延迟 1-3s | 人类级别间隔 |
| 批量上限 | 单次 batch-greet 最多 10 个 | 间隔 2-5s 随机 |

## 缓存策略

SQLite 使用 WAL 模式，支持多进程并发读取。

**缓存键规则**：
- 搜索缓存键 = `sha256(query + city + salary + experience + education + industry + scale + page)`
- 不同筛选条件组合视为不同缓存条目
- 相同查询不同页码视为不同缓存条目

**存储内容**：
- **搜索缓存**：最近 100 条搜索结果，24 小时过期。可通过 `--no-cache` 跳过
- **已打招呼记录**：security_id + 时间戳，永久保留。search 结果中 greeted 字段据此标记

## 配置文件

`~/.boss-agent/config.json` 可配置项：

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

所有配置项均可通过对应的 CLI 选项覆盖。

## 依赖清单

```
click>=8.0
httpx>=0.27
playwright>=1.40
playwright-stealth>=1.0
cryptography>=42.0       # Fernet 加密 + PBKDF2 密钥派生
```

## 版本策略

- CLI 版本：语义化版本（SemVer），初始 0.1.0
- schema_version：仅在信封格式发生不兼容变更时递增（1.0 -> 2.0）
- 向后兼容的字段新增不递增 schema_version

## 不在 MVP 范围内

- AI 驱动的职位匹配/评分
- 已读不回跟进
- 聊天记录管理
- MCP Server 模式
- 简历管理
- 多平台支持（拉勾、猎聘等）
