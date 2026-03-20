[根目录](../../CLAUDE.md) > [src/boss_agent_cli](..) > **commands**

# commands 模块

## 模块职责

Click CLI 命令实现层。每个命令文件封装一个 CLI 子命令，统一通过 `emit_success` / `emit_error` 输出 JSON 信封。命令层负责捕获底层异常并转为结构化错误响应。

## 入口与启动

- 所有命令通过 `main.py` 的 `cli.add_command()` 注册到 Click group
- 全局上下文 `ctx.obj` 传递：`data_dir`、`delay`、`logger`、`log_level`

## 对外接口

### 命令列表

| 命令 | 文件 | 说明 |
|------|------|------|
| `boss schema` | `schema.py` | 返回工具完整能力描述 JSON |
| `boss login` | `login.py` | 启动 Playwright 浏览器扫码登录 |
| `boss status` | `status.py` | 检查当前登录态（调用 user_info 接口验证） |
| `boss search <query>` | `search.py` | 按关键词和筛选条件搜索职位列表 |
| `boss detail <job_id>` | `detail.py` | 查看职位完整信息 |
| `boss greet <security_id> <job_id>` | `greet.py` | 向指定招聘者打招呼 |
| `boss batch-greet <query>` | `greet.py` | 搜索后批量打招呼（上限 10，间隔 2-5s） |

### 全局选项（定义在 main.py）

| 选项 | 默认值 | 说明 |
|------|--------|------|
| `--data-dir` | `~/.boss-agent` | 数据存储目录 |
| `--delay` | `1.5-3.0` | 请求间隔范围（秒） |
| `--log-level` | `error` | 日志级别 (error/warning/info/debug) |

### search 命令选项

`--city`, `--salary`, `--experience`, `--education`, `--industry`, `--scale`, `--page`, `--no-cache`

### batch-greet 错误处理策略

- `ALREADY_GREETED`: 跳过，继续下一个
- `RATE_LIMITED`: 停止剩余，返回已完成结果
- `GREET_LIMIT`: 停止剩余，返回已完成结果
- `NETWORK_ERROR`: 重试一次，仍失败则跳过继续

## 关键依赖与配置

- `click`: CLI 框架
- `auth/manager.py`: AuthManager, AuthRequired, TokenRefreshFailed
- `api/client.py`: BossClient
- `cache/store.py`: CacheStore
- `output.py`: emit_success, emit_error

## 测试与质量

- 测试文件: `tests/test_commands.py`
- 覆盖: schema 输出完整性、status 未登录、search 无效城市、greet 已打招呼、batch-greet dry-run
- Mock 策略: patch AuthManager、BossClient、CacheStore

## 相关文件清单

| 文件 | 职责 |
|------|------|
| `__init__.py` | 包初始化 |
| `schema.py` | `boss schema` -- 工具自描述 JSON |
| `login.py` | `boss login` -- Playwright 扫码登录 |
| `status.py` | `boss status` -- 检查登录态 |
| `search.py` | `boss search` -- 搜索职位 |
| `detail.py` | `boss detail` -- 职位详情 |
| `greet.py` | `boss greet` + `boss batch-greet` -- 打招呼 / 批量打招呼 |

## 变更记录 (Changelog)

| 日期 | 操作 | 说明 |
|------|------|------|
| 2026-03-20 | 初始创建 | 基于设计规范生成，预实现阶段 |
