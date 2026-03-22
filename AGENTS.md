# boss-agent-cli

AI Agent 专用的 BOSS 直聘求职 CLI 工具。

## 项目概览

- **语言**：Python >=3.10
- **技术栈**：Click (CLI) / httpx (HTTP) / patchright (反检测浏览器) / SQLite (缓存) / Fernet (加密)
- **入口点**：`boss = boss_agent_cli.main:cli`（定义在 `pyproject.toml`）

## 架构

```
CLI (Click) → AuthManager → BossClient (httpx) → BOSS 直聘 wapi
                  ↓                ↓
            TokenStore        CacheStore (SQLite WAL)
          (Fernet 加密)             ↓
                              output.py → JSON 信封 → stdout
```

**模块**：`auth/`（Token 生命周期）· `api/`（端点常量 + 数据模型）· `cache/`（SQLite WAL）· `commands/`（Click 命令）· `output.py`（JSON 信封）· `config.py`（配置读取）

## 开发环境

```bash
uv sync --all-extras
uv run patchright install chromium
uv run boss --help          # 验证安装
uv run pytest tests/ -v     # 运行测试
```

## 编码约束

- 缩进使用 tab，不使用空格
- Python >=3.10 联合类型语法（`X | Y`）
- 所有命令通过 `emit_success` / `emit_error` 输出 JSON 信封到 stdout
- 不可变数据优先（`dataclass` + 纯函数）
- 模块层抛异常（`AuthRequired`、`TokenRefreshFailed`），命令层统一捕获转 JSON 错误信封

## CLI 不变量契约

开发时必须保持以下不变量，违反即为 breaking change：

- **stdout** 仅输出 JSON 信封 `{ok, schema_version, command, data, pagination, error, hints}`
- **stderr** 仅输出日志和进度信息（通过 `--log-level` 控制）
- **exit code** 0 = `ok:true`，1 = `ok:false`
- **error** 必须包含 `code` + `recoverable` + `recovery_action` 字段
- **`--welfare`** 福利筛选为核心差异化功能，不得移除
- **`boss schema`** 返回完整能力自描述（9 个业务命令），是 Agent 的能力真源

## 测试

- 框架：pytest
- 目录：`tests/`
- Mock 策略：命令层通过 `unittest.mock.patch` 替换 AuthManager、BossClient、CacheStore
- 测试映射：`test_output.py` → output.py + config.py · `test_cache.py` → cache/ · `test_auth.py` → auth/ · `test_api.py` → api/ · `test_commands.py` → commands/ + main.py

## Git 规范

- commit 格式：`type: 中文描述`
- type：feat / fix / refactor / perf / docs / test / chore / ci
- 构建验证后再提交，暂不推送远程
