# Changelog

本项目遵循 [Semantic Versioning](https://semver.org/)。

## [1.0.0] - 2026-03-23

首个正式版本发布。

### Added
- 新增 `boss me` 命令 — 获取当前登录用户的基本信息、简历、求职期望、投递记录
- 新增跨平台 Agent Skill 体系 — 支持 Codex / Claude Code / Gemini CLI / OpenCode / OpenClaw
- 新增 `.agents/skills/` symlink 供 Codex / OpenCode 发现 skill
- pyproject.toml 补全 authors、keywords、classifiers、urls 元数据

### Fixed
- 修复 `boss me` 命令 AuthManager 路径拼接和 emit_error 参数问题
- 消息模板标准化 — hints 补全 + 参数引用修正 + recovery_action 统一

### Changed
- SKILL.md 重构为 AgentSkills 标准格式（跨平台兼容 frontmatter + OpenClaw metadata）
- skill 目录从 `skills/SKILL.md` 迁移到 `skills/boss-agent-cli/SKILL.md`

## [0.1.0] - 2026-03-20

### Added
- 新增 `boss me` 命令 — 获取当前登录用户的基本信息、简历、求职期望、投递记录
- 新增跨平台 Agent Skill 体系 — 支持 Codex / Claude Code / Gemini CLI / OpenCode / OpenClaw
- 新增 `.agents/skills/` symlink 供 Codex / OpenCode 发现 skill
- pyproject.toml 补全 authors、keywords、classifiers、urls 元数据

### Fixed
- 修复 `boss me` 命令 AuthManager 路径拼接和 emit_error 参数问题
- 消息模板标准化 — hints 补全 + 参数引用修正 + recovery_action 统一

### Changed
- SKILL.md 重构为 AgentSkills 标准格式（跨平台兼容 frontmatter + OpenClaw metadata）
- skill 目录从 `skills/SKILL.md` 迁移到 `skills/boss-agent-cli/SKILL.md`

## [0.1.0] - 2026-03-20

### Added
- 核心 CLI 框架（Click）+ JSON 信封输出协议
- `boss login` — patchright 反检测浏览器扫码登录 + 本地浏览器 Cookie 自动提取
- `boss status` — 检查登录态
- `boss search` — 职位搜索（支持城市 / 薪资 / 经验 / 学历 / 规模筛选）
- `boss search --welfare` — 福利精准筛选（双休、五险一金等，逗号分隔 AND 逻辑，自动翻页）
- `boss recommend` — 基于简历的个性化职位推荐
- `boss detail` — 职位完整详情（描述、地址、招聘者信息）
- `boss greet` — 向招聘者打招呼
- `boss batch-greet` — 批量打招呼（上限 10，支持 dry-run 预览）
- `boss export` — 导出搜索结果为 CSV / JSON
- `boss cities` — 列出 40 个支持城市
- `boss schema` — 工具能力自描述 JSON（Agent 调用入口）
- Token 加密存储（Fernet + PBKDF2 机器绑定密钥）
- SQLite WAL 缓存（搜索历史 100 条上限 + 已打招呼记录）
- 高斯分布请求延迟 + 指数退避 403 重试
- GitHub Actions CI（多 OS + 多 Python 版本）
