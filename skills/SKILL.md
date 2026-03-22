---
name: boss-agent-cli
description: BOSS 直聘求职工具 — 搜索职位（支持福利筛选）、个性化推荐、查看详情、向招聘者打招呼、导出结果。所有输出为结构化 JSON。
prerequisites:
  - uv tool install boss-agent-cli
  - patchright install chromium
---

# boss-agent-cli

BOSS 直聘求职 CLI 工具，专为 AI Agent 设计。通过 Bash 调用 `boss` 命令，读取 stdout JSON 输出完成操作。

## 安装前置

用户需先安装 CLI 工具和浏览器：

```bash
uv tool install boss-agent-cli
patchright install chromium
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
- stderr 为日志/进度信息，忽略即可
- exit code 0 成功，1 失败

## 调用流程

**必须按此顺序操作：**

```
1. boss status            -> 检查登录态
2. boss login             -> 若未登录（优先自动提取浏览器 Cookie，失败则弹出浏览器扫码）
3. boss search <关键词>    -> 搜索职位
   boss recommend         -> 或获取个性化推荐
4. boss detail <security_id> -> 查看详情（可选）
5. boss greet <security_id> <job_id> -> 打招呼
```

## 命令参考

### boss status

检查当前是否已登录。

```bash
boss status
```

### boss login

登录 BOSS 直聘。优先从本地浏览器（Chrome/Firefox/Edge 等）自动提取 Cookie（免扫码），失败则弹出浏览器扫码。

```bash
boss login [--timeout 120] [--cookie-source chrome]
```

- `--cookie-source`：指定从哪个浏览器提取 Cookie（如 chrome/firefox/edge/brave），不指定则自动检测
- 登录成功后 Token 自动缓存到本地，后续命令无需重复登录

### boss search

搜索职位，支持多维度筛选和福利过滤。

```bash
boss search "golang" \
  --city 杭州 \
  --salary 20-50K \
  --experience 3-5年 \
  --education 本科 \
  --scale 100-499人 \
  --welfare "双休,五险一金" \
  --page 1 \
  --no-cache
```

所有筛选参数可选。返回的每个职位包含 `job_id`、`security_id`、`welfare`（福利列表）、`skills`（技能标签）等字段。

**--welfare 福利筛选**（重要功能）：
- 当用户要求筛选特定福利（如"双休"、"五险一金"）时，使用 `--welfare` 参数
- 支持逗号分隔的多福利组合筛选：`--welfare "双休,五险一金"` 表示两个条件都必须满足（AND 逻辑）
- 工具会自动逐个检查每个职位的福利标签和职位描述，只返回匹配的结果
- 自动翻页（最多 5 页），直到找到所有匹配职位
- 匹配结果带 `welfare_match` 字段说明匹配来源（标签匹配 / 描述提及）
- 搜索过程中进度信息输出到 stderr
- 常用福利关键词：双休、五险一金、年终奖、餐补、住房补贴、定期体检、股票期权、加班补助

**city 可选值**：使用 `boss cities` 查看完整列表（40 个城市）

**salary 可选值**：3K以下、3-5K、5-10K、10-15K、10-20K、20-50K、50K以上

**experience 可选值**：应届、1年以内、1-3年、3-5年、5-10年、10年以上

**education 可选值**：大专、本科、硕士、博士

**scale 可选值**：0-20人、20-99人、100-499人、500-999人、1000-9999人、10000人以上

**搜索结果字段说明**：
- `job_id`: 职位 ID
- `security_id`: 安全 ID，用于 detail 和 greet 命令
- `title`: 职位名称
- `company`: 公司名称
- `salary`: 薪资描述
- `city` / `district`: 城市 / 区域
- `experience` / `education`: 经验 / 学历要求
- `skills`: 技能标签列表
- `welfare`: 福利标签列表（如 五险一金、带薪年假等）
- `industry` / `scale` / `stage`: 行业 / 公司规模 / 融资阶段
- `boss_name` / `boss_title` / `boss_active`: 招聘者信息
- `greeted`: 是否已打过招呼
- `welfare_match`: 福利匹配说明（仅 --welfare 筛选时出现）

### boss recommend

基于用户简历的个性化职位推荐。返回结构与 search 相同。

```bash
boss recommend [--page 1]
```

### boss detail

查看职位完整信息（含完整职位描述、办公地址、技能标签）。

```bash
boss detail <security_id>
```

`security_id` 从 search 或 recommend 结果中获取。

### boss greet

向指定招聘者打招呼。

```bash
boss greet <security_id> <job_id> [--message "自定义内容"]
```

`security_id` 和 `job_id` 从 search、recommend 或 detail 结果中获取。

### boss batch-greet

搜索后批量打招呼（单次上限 10 个）。

```bash
boss batch-greet "golang" \
  --city 杭州 \
  --count 5 \
  --dry-run
```

`--dry-run` 仅预览不发送。建议先 dry-run 让用户确认。

### boss export

导出搜索结果为 CSV 或 JSON 文件。自动翻页收集指定数量的职位。

```bash
boss export "golang" --city 广州 --count 50 --format csv --output jobs.csv
```

- `--format`：csv 或 json（默认 csv）
- `--output`：输出文件路径，不指定则输出到 stdout JSON 信封
- `--count`：导出数量（默认 50）

### boss cities

列出所有支持的城市（40 个），无需登录。

```bash
boss cities
```

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
2. **用户提到福利要求时使用 --welfare**：如"要双休"、"要五险一金"，传入 `--welfare "双休,五险一金"`（逗号分隔，AND 逻辑）
3. **不要连续快速调用**：工具内置了高斯分布请求延迟，无需额外 sleep
4. **批量打招呼前先 dry-run**：让用户确认候选列表
5. **解析 JSON 而非文本**：所有输出都是结构化 JSON，用 `ok` 字段判断成败
6. **登录优先免扫码**：`boss login` 会先尝试从浏览器提取 Cookie，仅提取失败时才弹出浏览器扫码
7. **展示搜索结果时包含福利信息**：welfare 字段是列表，向用户展示时应列出
8. **推荐用户未指定关键词时用 recommend**：用户说"推荐职位"或"有什么适合我的"时使用 `boss recommend`
9. **导出大量数据时用 export**：用户说"导出"、"下载列表"时使用 `boss export`
