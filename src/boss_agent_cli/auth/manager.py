from pathlib import Path

from boss_agent_cli.auth.browser import login_via_browser, refresh_stoken
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

	def login(self, *, timeout: int = 120) -> dict:
		token = login_via_browser(timeout=timeout)
		self._store.save(token)
		self._token = token
		return token

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
