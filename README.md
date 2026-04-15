<div align="center">

# boss-agent-cli

**专为 AI Agent 设计的 BOSS 直聘求职 CLI 工具**

> 搜索职位 · 福利筛选 · 个性化推荐 · 自动打招呼 · 求职流水线 · 增量监控 · AI 简历优化

[![CI](https://github.com/can4hou6joeng4/boss-agent-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/can4hou6joeng4/boss-agent-cli/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-≥3.10-3776AB?logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub Release](https://img.shields.io/github/v/release/can4hou6joeng4/boss-agent-cli)](https://github.com/can4hou6joeng4/boss-agent-cli/releases)
[![Tests](https://img.shields.io/badge/Tests-666%20passed-brightgreen)](https://github.com/can4hou6joeng4/boss-agent-cli)

[安装](#安装) · [快速开始](#快速开始) · [AI Agent 集成](#ai-agent-集成) · [命令参考](#命令参考) · [技术架构](#技术架构)

<img src="demo.gif" alt="boss-agent-cli 终端演示" width="100%">

</div>

> **English** | A CLI tool designed for AI Agents to interact with [BOSS Zhipin](https://www.zhipin.com/) (China's largest recruitment platform). All output is structured JSON, 32 commands, 4-tier login fallback (cookie → CDP → QR httpx → patchright). Install: `uv tool install boss-agent-cli && patchright install chromium`

---

## 为什么用 boss-agent-cli？

传统求职流程：打开网页 → 搜索 → 翻几十页 → 逐个看详情 → 手动打招呼 → 忘了跟进谁。

**boss-agent-cli 让 AI Agent 替你完成全部操作**：

```bash
boss search "Golang" --city 广州 --welfare "双休,五险一金"   # Agent 搜索
boss detail <security_id>                                    # Agent 看详情
boss greet <security_id> <job_id>                            # Agent 打招呼
boss pipeline                                                # Agent 追踪进度
boss digest                                                  # Agent 每日汇报
```

所有输出为结构化 JSON，Agent 一调用就能理解。

---

## 核心能力

### 求职全链路

| 能力 | 说明 | 命令 |
|------|------|------|
| **职位发现** | 关键词搜索 + 福利筛选 + 个性化推荐 | `search` `recommend` |
| **智能筛选** | `--welfare "双休,五险一金"` 自动翻页逐条匹配 | `search --welfare` |
| **主动出击** | 单个/批量打招呼、立即沟通投递 | `greet` `batch-greet` `apply` |
| **进度管理** | 求职流水线 + 跟进提醒 + 每日摘要 | `pipeline` `follow-up` `digest` |
| **增量监控** | 保存搜索条件、定期执行、标出新职位 | `watch` `shortlist` `preset` |
| **沟通管理** | 聊天记录、结构化摘要、联系人标签 | `chat` `chatmsg` `chat-summary` `mark` |
| **AI 优化** | 岗位分析 + 简历润色 + 匹配优化 | `ai analyze-jd` `ai polish` `ai optimize` |
| **数据导出** | CSV / JSON / HTML / Markdown 多格式 | `export` `chat --export` |

### 四级登录降级

```
boss login
  ├─ 1. Cookie 提取 — 从本地 Chrome/Firefox/Edge 等 10+ 浏览器免扫码提取
  ├─ 2. CDP 登录 — 复用带调试端口的 Chrome，保持真实浏览器指纹
  ├─ 3. QR httpx 登录 — 纯 HTTP 二维码扫码，无需安装任何浏览器
  └─ 4. patchright 扫码 — 反检测 Chromium 兜底
```

### Agent 友好设计

- **自描述协议** — `boss schema` 一次调用返回 32 个命令的完整能力描述
- **JSON 信封** — 所有 stdout 输出统一 `{ok, data, error, hints}` 格式
- **错误自愈** — 每个错误包含 `recovery_action`，Agent 可自动修复
- **智能反爬** — 高斯分布延迟 + 突发惩罚 + stoken 浏览器环境自动生成

---

## 安装

```bash
# 推荐：通过 uv 安装（秒级，自动隔离）
uv tool install boss-agent-cli

# 安装浏览器（用于登录）
patchright install chromium
```

<details>
<summary>其他安装方式</summary>

```bash
# pipx 安装（隔离环境）
pipx install boss-agent-cli
patchright install chromium

# pip 安装
pip install boss-agent-cli
patchright install chromium

# 从源码安装（开发用）
git clone https://github.com/can4hou6joeng4/boss-agent-cli.git
cd boss-agent-cli
uv sync --all-extras
uv run patchright install chromium
```

</details>

---

## 快速开始

```bash
# 0. 环境自检
boss doctor

# 1. 登录（自动四级降级：Cookie → CDP → QR → patchright）
boss login

# 2. 验证登录态
boss status

# 3. 搜索广州的 Golang 职位，要求双休+五险一金
boss search "Golang" --city 广州 --welfare "双休,五险一金"

# 4. 查看职位详情
boss detail <security_id>

# 5. 向招聘者打招呼 / 发起投递
boss greet <security_id> <job_id>
boss apply <security_id> <job_id>

# 6. 获取个性化推荐
boss recommend

# 7. 导出搜索结果
boss export "Golang" --city 广州 --count 50 -o jobs.csv

# 8. 求职流水线 + 每日摘要
boss pipeline
boss digest

# 9. 增量监控新职位
boss watch add my-golang "Golang" --city 广州 --welfare "双休"
boss watch run my-golang
```

---

## 登录链路说明

`boss login` 采用四级降级策略，适配不同环境：

| 级别 | 方式 | 适用场景 | 需要浏览器？ |
|------|------|---------|-------------|
| 1 | **Cookie 提取** | 已在本机浏览器登录过 BOSS 直聘 | 否 |
| 2 | **CDP 登录** | 带 `--remote-debugging-port` 的 Chrome | 需要 Chrome |
| 3 | **QR httpx 登录** | 纯 HTTP 扫码，无需安装浏览器 | 否 |
| 4 | **patchright 扫码** | 兜底方案 | 需要 Chromium |

### CDP 启动示例

```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 --user-data-dir=/tmp/boss-chrome

# Linux
google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/boss-chrome

# 使用 CDP 登录
boss --cdp-url http://localhost:9222 login --cdp
```

---

## AI Agent 集成

推荐先阅读：[Agent Quickstart](docs/agent-quickstart.md) · [Agent Host Examples](docs/agent-hosts.md) · [Capability Matrix](docs/capability-matrix.md)

### 方式一：Skill 安装（推荐）

```bash
npx skills add can4hou6joeng4/boss-agent-cli
```

安装后 Agent 自动获得调用 `boss` 命令的能力，无需手动配置。

### 方式二：手动配置

在 AI Agent 的规则文件中添加：

```markdown
当用户要求搜索职位、投递、打招呼等 BOSS 直聘操作时，通过 Bash 调用 `boss` CLI：
1. 运行 `boss status` 检查登录态
2. 若未登录，运行 `boss login` 提示用户扫码
3. 根据用户意图调用 search / recommend / detail / greet
4. 解析 stdout JSON，`ok` 字段判断成败
5. 用户提到福利要求时使用 `--welfare` 参数
```

### 输出协议

```json
{
  "ok": true,
  "schema_version": "1.0",
  "command": "search",
  "data": [...],
  "pagination": {"page": 1, "has_more": true, "total": 15},
  "error": null,
  "hints": {"next_actions": ["boss detail <security_id>"]}
}
```

| 约定 | 说明 |
|------|------|
| `stdout` | 仅 JSON 结构化数据 |
| `stderr` | 日志和进度信息 |
| `exit 0` | 命令成功 (`ok=true`) |
| `exit 1` | 命令失败 (`ok=false`) |

---

## 命令参考

### 基础操作

| 命令 | 说明 |
|------|------|
| `boss schema` | 输出 32 个命令的完整能力描述（Agent 首先调用） |
| `boss login` | 四级降级登录（Cookie → CDP → QR → patchright） |
| `boss logout` | 退出登录 |
| `boss status` | 检查登录态 |
| `boss doctor` | 诊断环境、依赖、登录态、Cookie 完整性和网络 |
| `boss me` | 我的信息（用户/简历/期望/投递记录） |

### 职位搜索与发现

| 命令 | 说明 |
|------|------|
| `boss search <query>` | 搜索职位（支持 `--welfare` 福利筛选和 `--preset` 预设） |
| `boss recommend` | 个性化推荐 |
| `boss detail <security_id>` | 职位详情（`--job-id` 走快速通道） |
| `boss show <#>` | 按编号查看上次搜索结果 |
| `boss cities` | 列出支持的 40 个城市 |

### 求职动作

| 命令 | 说明 |
|------|------|
| `boss greet <sid> <jid>` | 向招聘者打招呼 |
| `boss batch-greet <query>` | 批量打招呼（上限 10） |
| `boss apply <sid> <jid>` | 发起投递/立即沟通（幂等，不重复投递） |
| `boss exchange <sid>` | 请求交换手机/微信 |

### 沟通与跟进

| 命令 | 说明 |
|------|------|
| `boss chat` | 沟通列表（支持筛选和导出 html/md/csv/json） |
| `boss chatmsg <sid>` | 查看聊天消息历史 |
| `boss chat-summary <sid>` | 沟通摘要（阶段/待办/关键事实/风险标记） |
| `boss mark <sid> --label X` | 联系人标签管理（9 种标签） |
| `boss interviews` | 面试邀请列表 |
| `boss history` | 浏览历史 |

### 流水线与监控

| 命令 | 说明 |
|------|------|
| `boss pipeline` | 求职流水线（汇总沟通+面试，标记各阶段状态） |
| `boss follow-up` | 跟进提醒（筛选超时未推进的联系人） |
| `boss digest` | 每日摘要（综合流水线、跟进、统计） |
| `boss watch add/list/remove/run` | 搜索订阅与增量监控 |
| `boss shortlist add/list/remove` | 职位候选池管理 |
| `boss preset add/list/remove` | 搜索预设管理 |

### 简历与 AI

| 命令 | 说明 |
|------|------|
| `boss resume init/list/show/edit/delete/export/import/clone/diff` | 本地简历管理 |
| `boss ai config` | 配置 AI 服务（OpenAI / Anthropic / 兼容 API） |
| `boss ai analyze-jd` | 分析岗位要求 |
| `boss ai polish` | AI 润色简历 |
| `boss ai optimize` | 针对目标岗位优化简历 |
| `boss ai suggest` | 获取求职建议 |

### 系统管理

| 命令 | 说明 |
|------|------|
| `boss config list/set/reset` | 查看和修改配置 |
| `boss clean` | 清理过期缓存和临时文件 |
| `boss export <query>` | 导出搜索结果（CSV / JSON） |

### 搜索筛选参数

```bash
boss search "golang" \
  --city 广州 \             # 城市（40 个可选，用 boss cities 查看）
  --salary 20-50K \         # 薪资范围
  --experience 3-5年 \      # 经验要求
  --education 本科 \        # 学历要求
  --scale 100-499人 \       # 公司规模
  --welfare "双休,五险一金"  # 福利筛选（逗号分隔，AND 逻辑）
```

### 福利筛选

`--welfare` 是本工具的核心特色功能：

```bash
# 单条件
boss search "Python" --welfare 双休

# 多条件组合（AND 逻辑，所有条件都必须满足）
boss search "Golang" --city 广州 --welfare "双休,五险一金,年终奖"
```

工作原理：
1. 先检查职位的福利标签（`welfareList`）
2. 标签不匹配时自动调用 `card.json` 获取职位描述全文搜索
3. 自动翻页（最多 5 页）直到找到所有匹配结果
4. 每个结果带 `welfare_match` 字段说明匹配来源

---

## 诊断与排障

```bash
boss doctor
```

诊断项一览：

| 检查项 | 说明 |
|--------|------|
| `python` | Python 版本是否 >= 3.10 |
| `patchright` | CLI 是否已安装 |
| `patchright_chromium` | Chromium 内核是否已安装 |
| `cookie_extract` | 是否能从本地浏览器提取 zhipin Cookie |
| `auth_session` | 本地登录态是否存在、是否可解密 |
| `auth_token_quality` | 核心凭据质量（wt2 / stoken） |
| `cookie_completeness` | 辅助凭据完整性（wbg / zp_at） |
| `cdp` | Chrome 远程调试端口是否可连 |
| `network` | 是否可访问 zhipin.com |

常见修复：

```bash
patchright install chromium    # 安装浏览器内核
boss logout && boss login      # 重建登录态
boss --cdp-url http://localhost:9222 doctor   # CDP 诊断
```

---

## 错误处理

| 错误码 | 含义 | Agent 自动修复 |
|--------|------|---------------|
| `AUTH_REQUIRED` | 未登录 | `boss login` |
| `AUTH_EXPIRED` | 登录过期 | `boss login` |
| `RATE_LIMITED` | 频率过高 | 等待后重试 |
| `TOKEN_REFRESH_FAILED` | Token 刷新失败 | `boss login` |
| `ACCOUNT_RISK` | 风控拦截 | CDP Chrome 重试 |
| `INVALID_PARAM` | 参数错误 | 修正参数 |
| `ALREADY_GREETED` | 已打过招呼 | 跳过 |
| `GREET_LIMIT` | 今日次数用完 | 告知用户 |
| `NETWORK_ERROR` | 网络错误 | 重试 |
| `AI_NOT_CONFIGURED` | AI 未配置 | `boss ai config` |

---

## 配置

`~/.boss-agent/config.json`：

```json
{
  "default_city": null,
  "default_salary": null,
  "request_delay": [1.5, 3.0],
  "batch_greet_delay": [2.0, 5.0],
  "batch_greet_max": 10,
  "log_level": "error",
  "login_timeout": 120,
  "cdp_url": null,
  "export_dir": null
}
```

| 配置项 | 说明 |
|--------|------|
| `default_city` | 搜索时的默认城市 |
| `default_salary` | 搜索时的默认薪资范围 |
| `request_delay` | 请求间隔范围（秒），`[min, max]` |
| `batch_greet_delay` | 批量打招呼间隔范围（秒） |
| `batch_greet_max` | 批量打招呼上限 |
| `log_level` | 日志级别（error/warning/info/debug） |
| `login_timeout` | 登录超时时间（秒） |
| `cdp_url` | Chrome CDP 地址（如 `http://localhost:9222`） |
| `export_dir` | 导出文件默认保存目录 |

运行时修改配置：

```bash
boss config list            # 查看所有配置
boss config set default_city 广州   # 设置默认城市
boss config reset           # 恢复默认
```

---

## 技术架构

```
CLI (Click)
    │
    ├── AuthManager ── Cookie 提取 / CDP / QR httpx / patchright
    │       │
    │       └── TokenStore (Fernet + PBKDF2 机器绑定加密)
    │
    ├── BossClient ── httpx (低风险) + 浏览器 (高风险) 混合通道
    │       │
    │       ├── RequestThrottle (高斯延迟 + 突发惩罚)
    │       ├── BrowserSession (CDP 优先 / Bridge / patchright 降级)
    │       └── BOSS 直聘 wapi (18+ 端点)
    │
    ├── CacheStore (SQLite WAL)
    │
    ├── AIService (OpenAI / Anthropic / 兼容 API)
    │
    └── output.py → JSON 信封 → stdout
```

| 层级 | 选型 |
|------|------|
| 语言 | Python >= 3.10 |
| CLI | Click |
| HTTP | httpx |
| 浏览器 | patchright（Playwright 反检测 fork） |
| Cookie | browser-cookie3（10+ 浏览器） |
| 加密 | cryptography (Fernet + PBKDF2) |
| 数据库 | sqlite3 (WAL 模式) |
| 渲染 | rich |
| AI | OpenAI / Anthropic Chat Completions API |
| 测试 | pytest（666 项） |

---

## 致谢

本项目参考了以下优秀开源项目的设计理念：

- [geekgeekrun](https://github.com/geekgeekrun/geekgeekrun) — 浏览器自动化 + 反检测策略
- [boss-cli](https://github.com/jackwener/boss-cli) — CLI 结构化输出 + Agent 友好设计
- [opencli](https://github.com/jackwener/opencli) — Browser Bridge 架构理念

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=can4hou6joeng4/boss-agent-cli&type=Date)](https://star-history.com/#can4hou6joeng4/boss-agent-cli&Date)

## 许可证

[MIT](LICENSE)
