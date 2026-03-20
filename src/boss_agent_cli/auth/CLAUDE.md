[根目录](../../CLAUDE.md) > [src/boss_agent_cli](..) > **auth**

# auth 模块

## 模块职责

Token 生命周期管理：加密存储 Cookie/stoken、Playwright 浏览器登录、stoken 静默刷新、多进程文件锁。

## 入口与启动

- **AuthManager** (`manager.py`)：对外暴露的统一入口
  - `get_token()` -> 获取当前有效 Token（无则抛 `AuthRequired`）
  - `login(timeout)` -> 启动 Playwright 浏览器登录
  - `force_refresh()` -> 带文件锁的 stoken 静默刷新
  - `check_status()` -> 检查本地是否有已存储的 Token

## 对外接口

### 异常类（命令层统一捕获）

| 异常 | 含义 | 对应错误码 |
|------|------|-----------|
| `AuthRequired` | 未登录，本地无 Token | AUTH_REQUIRED |
| `TokenRefreshFailed` | stoken 刷新失败 | TOKEN_REFRESH_FAILED |

### AuthManager 公开方法

```python
class AuthManager:
    def __init__(self, data_dir: Path, *, logger: Logger | None = None)
    def get_token(self) -> dict          # 获取 Token，无则抛 AuthRequired
    def login(self, *, timeout: int = 120) -> dict  # Playwright 登录
    def force_refresh(self) -> None      # 带锁的 stoken 刷新
    def check_status(self) -> dict | None  # 本地 Token 检查
```

## 关键依赖与配置

- `cryptography` (Fernet + PBKDF2HMAC): Token 加密
- `playwright` + `playwright-stealth`: 浏览器自动化
- 密钥派生：机器 UUID + PBKDF2-HMAC-SHA256 (480000 迭代) + 随机 salt

## 数据模型

**Token 数据结构**（存储在 `session.enc`）：
```python
{
    "cookies": {"wt2": "...", ...},  # BOSS 直聘 Cookie
    "stoken": "...",                  # __zp_stoken__ 防爬 Token
    "user_agent": "..."               # 浏览器 UA
}
```

**存储路径**：`~/.boss-agent/auth/`
- `session.enc` - Fernet 加密的 Token 数据
- `salt` - PBKDF2 salt（16 字节，首次随机生成）
- `refresh.lock` - 文件锁（刷新时临时创建，超时 30s 自动释放）

## 测试与质量

- 测试文件：`tests/test_auth.py`
- 覆盖：save/load、空加载、覆盖写入、文件锁生命周期
- 注意：浏览器登录 (`browser.py`) 依赖外部服务，无单元测试

## 常见问题 (FAQ)

**Q: 换机器后为什么需要重新登录？**
A: 密钥基于机器 UUID 派生，不同机器无法解密旧 session。

**Q: stoken 刷新机制是什么？**
A: 惰性策略 -- 不主动判断过期，API 返回 403 或安全验证时才触发。BossClient 调用 `auth_manager.force_refresh()`，AuthManager 内部启动 Playwright 无头实例加载已登录页面提取新 stoken。

**Q: 多进程并发刷新如何处理？**
A: 文件锁 (`refresh.lock`)，其他进程检测到锁存在时等待最多 30s，锁超时自动释放防止死锁。

## 相关文件清单

| 文件 | 职责 |
|------|------|
| `__init__.py` | 包初始化 |
| `manager.py` | AuthManager: Token 生命周期管理（异常驱动） |
| `browser.py` | Playwright 登录 + stoken 提取/刷新 |
| `token_store.py` | Fernet 加密 Token 持久化 + 文件锁 |

## 变更记录 (Changelog)

| 日期 | 操作 | 说明 |
|------|------|------|
| 2026-03-20 | 初始创建 | 基于设计规范生成，预实现阶段 |
