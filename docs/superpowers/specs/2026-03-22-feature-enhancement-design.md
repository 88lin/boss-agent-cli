# boss-agent-cli 功能增强设计规范

## 概述

融入 boss-cli 和 opencli 的优势功能，增强 boss-agent-cli：认证免扫码、反爬优化、5 个新命令。

## 1. 认证增强：Cookie 提取优先

新依赖：`browser-cookie3`

login 流程：
1. 尝试 browser-cookie3 提取 zhipin.com Cookie
2. 调用 user_info API 验证有效性
3. 有效则保存，输出"登录成功（Cookie 提取）"
4. 无效则降级到 patchright 扫码登录

新增文件：`src/boss_agent_cli/auth/cookie_extract.py`
- `extract_cookies(source: str | None) -> dict | None`
- 返回 `{"cookies": {...}, "user_agent": "...", "stoken": ""}` 或 None
- stoken 为空，首次 API 调用时 403 触发 force_refresh 补充

改造：`auth/manager.py` login() 先调 extract_cookies()，失败再调 login_via_browser()
改造：`commands/login.py` 新增 `--cookie-source` 选项

## 2. 反爬增强：高斯抖动 + 指数退避

改造：`api/client.py`

_wait() 改为高斯分布延迟：
- mean = (delay_low + delay_high) / 2
- std = (delay_high - delay_low) / 4
- 最小值不低于 delay_low

403 重试改为指数退避：
- backoff = 2^retry_count + random(0, 1)
- 退避后再 force_refresh

## 3. 新增 API 端点

endpoints.py 新增：
- RECOMMEND_URL = /wapi/zpgeek/pc/recommend/job/list.json
- APPLIED_URL = /wapi/zpgeek/applied/positions.json
- CHAT_LIST_URL = /wapi/zpgeek/chat/friendlist.json

client.py 新增方法：
- recommend_jobs(page=1) -> dict
- applied_list(page=1) -> dict
- chat_list(page=1) -> dict

## 4. 新命令

### boss recommend [--page 1]
基于简历的个性化推荐。返回与 search 相同结构的职位列表（复用 JobItem.from_api）。

### boss applied [--page 1]
已投递职位列表，含投递时间和状态。

### boss chat [--page 1]
已沟通的招聘者列表。

### boss export <query> [--city] [--salary] [--count 50] [--format csv] [--output jobs.csv]
导出搜索结果。自动翻页收集。支持 csv/json。--output 指定文件，不指定则 stdout。

### boss cities
输出所有支持的城市列表。直接输出 CITY_CODES 键列表，无需 API。

## 5. 文件变更

| 文件 | 操作 |
|------|------|
| pyproject.toml | 修改：新增 browser-cookie3 |
| auth/cookie_extract.py | 新增 |
| auth/manager.py | 修改：login 加入 Cookie 提取 |
| api/endpoints.py | 修改：3 个新 URL |
| api/client.py | 修改：高斯抖动 + 指数退避 + 3 个新方法 |
| commands/recommend.py | 新增 |
| commands/applied.py | 新增 |
| commands/chat.py | 新增 |
| commands/export.py | 新增 |
| commands/cities.py | 新增 |
| commands/login.py | 修改：--cookie-source |
| commands/schema.py | 修改：注册新命令 |
| main.py | 修改：注册 5 个新命令 |
| tests/ | 修改：新增测试 |

## 6. schema 更新

boss schema 输出中新增 5 个命令定义。
