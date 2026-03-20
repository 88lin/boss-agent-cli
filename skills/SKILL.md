---
name: boss-agent-cli
description: BOSS 直聘求职工具 — 搜索职位、查看详情、向招聘者打招呼。所有输出为结构化 JSON。
prerequisites:
  - uv tool install boss-agent-cli
  - playwright install chromium
---

# boss-agent-cli

BOSS 直聘求职 CLI 工具，专为 AI Agent 设计。通过 Bash 调用 `boss` 命令，读取 stdout JSON 输出完成操作。

## 安装前置

用户需先安装 CLI 工具和浏览器：

```bash
uv tool install boss-agent-cli
playwright install chromium
```

如未安装，提示用户执行以上命令。

## 输出协议

所有命令输出 JSON 到 stdout，格式固定：

```json
{
  "ok": true,
  "schema_version": "1.0",
  "command": "命令名",
  "data": {},
  "pagination": null,
  "error": null,
  "hints": {"next_actions": ["下一步建议"]}
}
```

- `ok=false` 时读 `error.code` 判断错误类型
- `error.recoverable=true` 时按 `error.recovery_action` 执行修复
- `hints.next_actions` 包含下一步可执行的命令建议
- stderr 为日志，忽略即可
- exit code 0 成功，1 失败

## 调用流程

**必须按此顺序操作：**

```
1. boss status          → 检查登录态
2. boss login           → 若未登录，提示用户在弹出的浏览器中扫码
3. boss search <关键词>  → 搜索职位
4. boss detail <job_id> → 查看详情（可选）
5. boss greet <security_id> <job_id> → 打招呼
```

## 命令参考

### boss status

检查当前是否已登录。

```bash
boss status
```

### boss login

启动浏览器扫码登录。需要用户手动扫码，不可自动完成。

```bash
boss login [--timeout 120]
```

登录成功后 Token 自动缓存到本地，后续命令无需重复登录。

### boss search

搜索职位，支持多维度筛选。

```bash
boss search "golang" \
  --city 杭州 \
  --salary 20-50K \
  --experience 3-5年 \
  --education 本科 \
  --scale 100-499人 \
  --page 1 \
  --no-cache
```

所有筛选参数可选。返回的每个职位包含 `job_id` 和 `security_id`，用于后续 detail 和 greet。

**city 可选值**：北京、上海、广州、深圳、杭州、成都、南京、武汉、西安、苏州、长沙、郑州、重庆、天津、合肥、厦门、济南、青岛、大连、宁波、福州、东莞、珠海、佛山、昆明、贵阳、太原、南昌、南宁、石家庄、哈尔滨、长春、沈阳、海口、兰州、乌鲁木齐、无锡、常州、温州、惠州

**salary 可选值**：3K以下、3-5K、5-10K、10-15K、10-20K、20-50K、50K以上

**experience 可选值**：应届、1年以内、1-3年、3-5年、5-10年、10年以上

**education 可选值**：大专、本科、硕士、博士

**scale 可选值**：0-20人、20-99人、100-499人、500-999人、1000-9999人、10000人以上

### boss detail

查看职位完整信息（含职位描述和公司信息）。

```bash
boss detail <job_id>
```

`job_id` 从 search 结果的 `data.jobs[].job_id` 获取。

### boss greet

向指定招聘者打招呼。

```bash
boss greet <security_id> <job_id> [--message "自定义内容"]
```

`security_id` 和 `job_id` 从 search 或 detail 结果中获取。

### boss batch-greet

搜索后批量打招呼（单次上限 10 个）。

```bash
boss batch-greet "golang" \
  --city 杭州 \
  --count 5 \
  --dry-run
```

`--dry-run` 仅预览不发送。建议先 dry-run 让用户确认。

## 错误处理

| 错误码 | 含义 | 处理方式 |
|--------|------|----------|
| AUTH_REQUIRED | 未登录 | 执行 `boss login` |
| AUTH_EXPIRED | 登录过期 | 执行 `boss login` |
| RATE_LIMITED | 频率过高 | 等待后重试 |
| TOKEN_REFRESH_FAILED | Token 刷新失败 | 执行 `boss login` |
| INVALID_PARAM | 参数错误 | 修正参数重试 |
| ALREADY_GREETED | 已打过招呼 | 跳过 |
| GREET_LIMIT | 今日次数用完 | 告知用户明天再试 |
| JOB_NOT_FOUND | 职位不存在 | 告知用户 |
| NETWORK_ERROR | 网络错误 | 重试一次 |

## 行为规则

1. **每次操作前先检查登录态**：调用 `boss status`，失败则引导 `boss login`
2. **不要连续快速调用**：工具内置了请求延迟，无需额外 sleep
3. **批量打招呼前先 dry-run**：让用户确认候选列表
4. **解析 JSON 而非文本**：所有输出都是结构化 JSON，用 `ok` 字段判断成败
5. **登录需要用户介入**：`boss login` 会弹出浏览器，必须提示用户扫码
