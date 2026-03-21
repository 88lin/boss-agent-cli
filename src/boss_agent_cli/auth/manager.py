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
		if token:
			# 验证 Cookie 是否有效
			if self._verify_token(token):
				self._store.save(token)
				self._token = token
				self._logger.info("Cookie 提取成功，已验证有效")
				return token
			self._logger.info("提取的 Cookie 已失效，降级到扫码登录")
		else:
			self._logger.info("未能从浏览器提取 Cookie，降级到扫码登录")

		# 第二步：降级到 patchright 扫码
		token = login_via_browser(timeout=timeout)
		self._store.save(token)
		self._token = token
		return token

	def _verify_token(self, token: dict) -> bool:
		"""通过 user_info API 验证 Token 是否有效"""
		try:
			import httpx
			from boss_agent_cli.api import endpoints
			resp = httpx.get(
				endpoints.USER_INFO_URL,
				cookies=token.get("cookies", {}),
				headers={
					"User-Agent": token.get("user_agent") or "Mozilla/5.0",
					"Referer": "https://www.zhipin.com/",
				},
				params={"__zp_stoken__": token.get("stoken", "")},
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
