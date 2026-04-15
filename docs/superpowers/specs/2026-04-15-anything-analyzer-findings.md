# anything-analyzer 协议分析成果与改进建议

> 基于 [Mouseww/anything-analyzer](https://github.com/Mouseww/anything-analyzer) 的 JS Hook、MITM 代理、加密代码提取能力，结合公开逆向情报和竞品项目（jackwener/boss-cli、tianhhe/boss-zhipin-cli、ufownl/auto-zhipin）的端点对比分析。

## 一、stoken 纯 Python 实现评估

### 结论：不可行，当前方案已是最佳实践

`__zp_stoken__` 基于 JSVMP（JS 虚拟机保护），核心特征：

- **每日代码轮换**：加密 JS 文件每天更新，算法动态变化
- **7+ 环境检测点**：window 对象关系、prototype 检测、navigator 属性、document.all 等
- **控制流混淆**：类阿里风格，真假函数包裹 + 多层 switch 嵌套

生成公式：`code = new ABC().z(seed, parseInt(ts) + (480 + new Date().getTimezoneOffset()) * 60 * 1000)`

业界三种路线（补环境/纯算法还原/JSRPC）均需持续维护，不适合 CLI 工具。boss-agent-cli 当前的浏览器通道方案（CDP 优先 + patchright 降级）是最稳定的选择。

### 参考资料

- [CSDN: stoken 逆向分析](https://blog.csdn.net/weixin_44697518/article/details/138172770)
- [CSDN: 纯算法还原](https://blog.csdn.net/weixin_52001594/article/details/139412528)
- [GitHub: boss_zhipin_spider](https://github.com/leiyugithub/boss_zhipin_spider)

## 二、apply/投递端点验证

### 结论：当前实现正确，friend/add.json 就是投递入口

通过对比 jackwener/boss-cli、tianhhe/boss-zhipin-cli、ufownl/auto-zhipin 三个项目：

- 所有项目的"打招呼"和"投递/立即沟通"均指向 `/wapi/zpgeek/friend/add.json`
- BOSS 直聘的产品逻辑是"立即沟通 = 建立好友关系 = 投递"，不存在独立的投递/简历提交端点
- boss-agent-cli 的 `apply` 命令复用 `greet` 的 `GREET_URL` 是正确行为

## 三、缺失端点发现

通过与 jackwener/boss-cli（constants.py）对比，发现以下 boss-agent-cli 未实现但有价值的端点：

### 高价值缺失端点

| 端点 | 路径 | 用途 | 建议优先级 |
|------|------|------|-----------|
| 简历状态 | `/wapi/zpgeek/resume/status.json` | 查询简历完整度/在线状态 | P1 — 配合现有 resume 模块 |
| 互动关系 | `/wapi/zprelation/interaction/geekGetJob` | 查询与某招聘者的互动关系 | P1 — 避免重复打招呼 |
| 二维码登录 API | `/wapi/zppassport/qrcode/*` | 程序化二维码登录（无需 Playwright） | P2 — 可实现轻量登录 |

### QR 登录端点族（boss-cli 已实现）

```
/wapi/zppassport/captcha/randkey       — 获取随机密钥
/wapi/zpweixin/qrcode/getqrcode       — 获取二维码图片
/wapi/zppassport/qrcode/scan          — 轮询扫码状态
/wapi/zppassport/qrcode/scanLogin     — 确认扫码登录
/wapi/zppassport/qrcode/dispatcher    — 登录调度
```

这组端点可以实现**纯 httpx 的二维码登录**，无需启动 Playwright 浏览器。流程：生成二维码 → 终端显示 → 轮询扫码状态 → 获取 Cookie。

## 四、Cookie 完整性问题

### 发现

boss-cli 要求 4 个关键 Cookie：`{"__zp_stoken__", "wt2", "wbg", "zp_at"}`

boss-agent-cli 当前仅检查 `wt2` + `stoken`，未关注 `wbg` 和 `zp_at`。

### 建议

在 `doctor` 命令的 `auth_token_quality` 检查中增加 `wbg` 和 `zp_at` 的检测，降低因 Cookie 不完整导致的隐性失败。

## 五、风控 code 36 分析

### 触发条件（综合公开资料）

| 触发因素 | 说明 |
|----------|------|
| **Headless 检测** | `navigator.webdriver=true` 或自动化标记（patchright 已处理） |
| **指纹不一致** | UA/platform/屏幕分辨率与 Cookie 来源环境不匹配 |
| **行为异常** | 短时间内高频操作（当前 throttle 已处理） |
| **新设备/新 IP** | 首次在新环境登录后立即高频请求 |

### 当前防护评估

boss-agent-cli 的防护已相当完善：
- `RequestThrottle`：高斯延迟 + 5% 随机长停顿 + 突发惩罚
- CDP 优先：复用用户真实 Chrome，指纹天然一致
- `sec-ch-ua-platform` 动态适配

### 可优化点

1. **首次请求预热**：登录后先做 1-2 次低风险请求（status/user_info）再发起高风险操作
2. **Referer 链真实性**：高风险操作前先"浏览"一下对应页面（在浏览器通道中加载 referer 页面）
3. **请求间 Cookie 同步**：httpx 通道的 `_merge_cookies` 已实现，确认浏览器通道也同步更新

## 六、端点通道分配优化

### 当前分配

| 通道 | 端点 | 原因 |
|------|------|------|
| 浏览器 | search, recommend, greet, apply, job_card, exchange | 高风险，需 stoken |
| httpx | detail, user_info, resume_*, deliver_list, friend_list, interview_data, job_history, chat_history, friend_label_*, | 低风险，Cookie 即可 |

### 可降级评估

| 端点 | 当前通道 | 能否降级为 httpx | 原因 |
|------|---------|-----------------|------|
| `job_card` | 浏览器 | **可能** | 本质是 GET 请求查看卡片信息，风险等级存疑 |
| `exchange` | 浏览器 | **不建议** | 敏感操作，触碰隐私数据 |
| `search` | 浏览器 | **不可** | stoken 必需 |
| `recommend` | 浏览器 | **不可** | stoken 必需 |
| `greet/apply` | 浏览器 | **不可** | 核心交互操作 |

`job_card` 是唯一可能降级的端点。可以在 httpx 通道尝试请求，失败时降级回浏览器通道（与 detail 的三级降级策略一致）。

## 七、移动端 API 评估

### 结论：当前阶段不建议投入

- 移动端使用独立的 token/签名机制（非 stoken），与 Web 端完全不同
- 逆向门槛高：需要 APK 反编译 + 可能的 SSL Pinning 绕过 + Frida Hook
- 公开资料极少，投入产出比低
- Web 端 `/wapi` 接口已覆盖所有求职者核心功能

### anything-analyzer MITM 代理的适用场景

如果未来需要移动端 API，anything-analyzer 的 MITM 代理是最佳工具：
1. 在 App 端配置 `http://127.0.0.1:8888` 为代理
2. 安装 CA 证书到手机
3. 操作 App 完成抓包
4. AI 自动分析移动端协议

## 八、建议实施路线

### 短期（可直接实施）

1. **boss.yaml 补充** `resume_status` 和 `geek_get_job` 端点定义
2. **doctor 命令增强** Cookie 完整性检查（wbg/zp_at）
3. **job_card httpx 降级尝试** 在 BossClient 中增加 httpx 优先 + 浏览器兜底

### 中期（需设计评审）

4. **QR 纯 httpx 登录** 实现 `/wapi/zppassport/qrcode/*` 端点族，终端显示二维码
5. **首次请求预热策略** 在 `BossClient.__init__` 后自动执行 `user_info()` 暖机

### 长期（路线图储备）

6. **移动端 API 分析** 使用 anything-analyzer MITM 代理抓取移动端流量
7. **anything-analyzer MCP 集成** 双 MCP Server 组合自动化协议分析
