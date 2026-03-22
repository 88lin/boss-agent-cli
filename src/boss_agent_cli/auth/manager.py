from pathlib import Path

from boss_agent_cli.auth.browser import login_via_browser, refresh_stoken
from boss_agent_cli.auth.cookie_extract import extract_cookies
from boss_agent_cli.auth.token_store import TokenStore
from boss_agent_cli.output import Logger


class AuthRequired(Exception):
	pass


class TokenRefreshFailed(Exception):
	pass


class AuthManager:
	def __init__(self, data_dir: Path, *, logger: Logger | None = None):
		self._store = TokenStore(data_dir / "auth")
		self._token: dict | None = None
		self._logger = logger or Logger()

	def get_token(self) -> dict:
		if self._token is not None:
			return self._token
		self._token = self._store.load()
		if self._token is None:
			raise AuthRequired("未登录，请先执行 boss login")
		return self._token

	def login(self, *, timeout: int = 120, cookie_source: str | None = None) -> dict:
		"""Cookie 提取优先，失败降级到 patchright 扫码"""
		# 第一步：尝试从本地浏览器提取 Cookie
		self._logger.info("尝试从本地浏览器提取 Cookie...")
		token = extract_cookies(cookie_source)
		if token and token.get("cookies", {}).get("wt2"):
			# 有 wt2 说明浏览器已登录，先保存 Cookie
			# stoken 可能为空——没关系，首次 API 调用 403 时 force_refresh 会自动补充
			if self._verify_cookie(token):
				self._store.save(token)
				self._token = token
				self._logger.info("Cookie 提取成功，已保存")
				return token
			self._logger.info("提取的 Cookie 已失效，降级到扫码登录")
		else:
			self._logger.info("未能从浏览器提取 Cookie，降级到扫码登录")

		# 第二步：降级到 patchright 扫码
		token = login_via_browser(timeout=timeout)
		self._store.save(token)
		self._token = token
		return token

	def _verify_cookie(self, token: dict) -> bool:
		"""验证 Cookie 是否有效（不依赖 stoken，直接用 Cookie 请求用户信息）"""
		try:
			import httpx
			from boss_agent_cli.api import endpoints
			# 不传 stoken——user_info 接口即使 stoken 为空/错误也能返回用户信息
			# 只要 Cookie（wt2）有效就会返回 code=0
			resp = httpx.get(
				endpoints.USER_INFO_URL,
				cookies=token.get("cookies", {}),
				headers={
					"User-Agent": token.get("user_agent") or "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
					"Referer": "https://www.zhipin.com/",
				},
				timeout=10,
			)
			data = resp.json()
			return data.get("code") == 0
		except Exception:
			return False

	def force_refresh(self) -> None:
		with self._store.refresh_lock():
			current = self._store.load()
			if current is None:
				raise TokenRefreshFailed("无法刷新 Token，请重新登录")
			self._logger.info("Token 过期，正在静默刷新...")
			try:
				new_stoken = refresh_stoken(
					current["cookies"],
					current.get("user_agent", ""),
				)
				current["stoken"] = new_stoken
				self._store.save(current)
				self._token = current
			except Exception as e:
				raise TokenRefreshFailed(f"Token 刷新失败: {e}") from e

	def check_status(self) -> dict | None:
		return self._store.load()
