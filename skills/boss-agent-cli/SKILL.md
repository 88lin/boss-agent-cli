---
name: boss-agent-cli
description: >-
  BOSS Zhipin (BOSS直聘) job search CLI for AI agents — search jobs with welfare
  filtering (--welfare), personalized recommendations, view details, greet recruiters,
  batch-greet, and export results. All output is structured JSON via stdout.
  Trigger: 找工作, 投简历, boss直聘, 招聘, 搜索职位, 打招呼, 福利筛选, 双休,
  job search, recruitment, greet recruiter, batch-greet, welfare filter, BOSS Zhipin.
metadata: {"openclaw":{"requires":{"bins":["boss"]},"emoji":"💼","homepage":"https://github.com/can4hou6joeng4/boss-agent-cli"}}
---

# boss-agent-cli

BOSS 直聘求职 CLI，专为 AI Agent 设计。通过 Bash 调用 `boss` 命令，解析 stdout JSON 完成求职操作链。

## 安装前置

运行此 skill 需要 `boss` 命令可用。若不可用，提示用户执行：

```bash
uv tool install boss-agent-cli
patchright install chromium
```

验证安装：`boss schema`（应返回 JSON 能力描述）。

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

- `ok=false` 时读 `error.code` 判断错误类型，`error.recovery_action` 包含修复命令
- `hints.next_actions` 包含 Agent 可直接执行的下一步命令
- stderr 为日志/进度信息，忽略即可
- exit code 0 = 成功，1 = 失败

## 调用流程

**必须按此顺序操作：**

```
1. boss status              → 检查登录态
2. boss login               → 若未登录（优先免扫码提取 Cookie，失败弹出浏览器）
3. boss search <关键词>      → 搜索职位
   boss recommend           → 或获取个性化推荐
4. boss detail <security_id> → 查看详情（可选）
5. boss greet <security_id> <job_id> → 打招呼
```

## 命令速查

运行 `boss schema` 获取完整命令定义（参数、可选值、返回字段）。运行 `boss <cmd> --help` 查看单个命令帮助。

| 命令 | 用途 | 关键参数 |
|------|------|----------|
| `boss schema` | 能力自描述（10 个业务命令） | 无 |
| `boss status` | 检查登录态 | 无 |
| `boss login` | 登录（Cookie 优先，失败扫码） | `--timeout` `--cookie-source` |
| `boss me` | 我的信息（用户/简历/期望/投递） | `--section` `--deliver-page` |
| `boss search <query>` | 搜索职位 | `--city` `--salary` `--welfare` `--experience` |
| `boss recommend` | 个性化推荐 | `--page` |
| `boss detail <security_id>` | 职位详情 | 无 |
| `boss greet <sid> <jid>` | 打招呼 | `--message` |
| `boss batch-greet <query>` | 批量打招呼（上限 10） | `--count` `--dry-run` |
| `boss export <query>` | 导出结果 | `--format csv/json` `--output` `--count` |
| `boss cities` | 列出 40 个支持城市 | 无 |

## 福利筛选（核心功能）

用户提到福利要求（如"要双休"、"五险一金"）时，使用 `--welfare` 参数：

```bash
boss search "golang" --city 广州 --welfare "双休,五险一金"
```

- 逗号分隔 = AND 逻辑，所有条件都必须满足
- 自动翻页逐个检查职位福利标签和描述
- 结果带 `welfare_match` 字段说明匹配来源
- 常用关键词：双休、五险一金、年终奖、餐补、住房补贴、定期体检、股票期权、加班补助

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

1. **先检查登录态**：每次操作前调用 `boss status`，失败则 `boss login`
2. **福利要求用 --welfare**：用户说"要双休"→ `--welfare "双休"`
3. **无需额外 sleep**：工具内置高斯分布请求延迟
4. **批量打招呼先 dry-run**：`boss batch-greet ... --dry-run` 让用户确认
5. **解析 JSON 不解析文本**：用 `ok` 字段判断成败
6. **未指定关键词用 recommend**：用户说"推荐职位"→ `boss recommend`
7. **导出用 export**：用户说"导出"、"下载列表"→ `boss export`
8. **展示结果含福利**：welfare 字段是列表，向用户展示时列出
