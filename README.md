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
boss schema                                        # 理解工具能力
boss status                                        # 检查登录态
boss login                                         # 扫码登录（需用户手动扫码）
boss search "golang" --city 杭州 --salary 20-50K    # 搜索职位
boss detail <job_id>                               # 查看详情
boss greet <security_id> <job_id>                  # 打招呼
boss batch-greet "golang" --city 杭州 --count 5     # 批量打招呼
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
