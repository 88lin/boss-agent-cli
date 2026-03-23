import random
import time
from collections import deque

import httpx

from boss_agent_cli.api import endpoints

_MAX_RETRIES = 3


class AuthError(Exception):
	pass


class BossClient:
	"""Hybrid API client: browser channel for high-risk ops, httpx for low-risk ops."""

	def __init__(self, auth_manager, *, delay: tuple[float, float] = (1.5, 3.0)):
		self._auth = auth_manager
		self._delay = delay
		self._client: httpx.Client | None = None
		self._browser_session = None
		self._last_request_time = 0.0
		self._recent_times: deque[float] = deque(maxlen=12)

	def _get_client(self) -> httpx.Client:
		if self._client is None:
			token = self._auth.get_token()
			headers = dict(endpoints.DEFAULT_HEADERS)
			if ua := token.get("user_agent"):
				headers["User-Agent"] = ua
			self._client = httpx.Client(
				base_url=endpoints.BASE_URL,
				cookies=token.get("cookies", {}),
				headers=headers,
				follow_redirects=True,
				timeout=30,
			)
		return self._client

	def _get_browser(self):
		if self._browser_session is None:
			from boss_agent_cli.api.browser_client import BrowserSession
			token = self._auth.get_token()
			self._browser_session = BrowserSession(
				cookies=token.get("cookies", {}),
				user_agent=token.get("user_agent", ""),
				delay=self._delay,
			)
		return self._browser_session

	# ── Anti-detection delays (httpx channel) ────────────────────────

	def _wait(self):
		elapsed = time.time() - self._last_request_time
		mean = sum(self._delay) / 2
		std = (self._delay[1] - self._delay[0]) / 4
		base_sleep = max(0, random.gauss(mean, std) - elapsed)

		if random.random() < 0.05:
			base_sleep += random.uniform(2.0, 5.0)

		burst = self._burst_penalty()
		total = max(0, base_sleep + burst)
		if total > 0:
			time.sleep(total)

	def _burst_penalty(self) -> float:
		if not self._recent_times:
			return 0.0
		now = time.time()
		recent_15s = sum(1 for ts in self._recent_times if now - ts <= 15)
		recent_45s = sum(1 for ts in self._recent_times if now - ts <= 45)
		if recent_45s >= 6:
			return random.uniform(4.0, 7.0)
		if recent_15s >= 3:
			return random.uniform(1.2, 2.8)
		return 0.0

	def _mark_request(self):
		now = time.time()
		self._last_request_time = now
		self._recent_times.append(now)

	def _headers_for(self, url: str) -> dict[str, str]:
		referer = endpoints.REFERER_MAP.get(url, f"{endpoints.BASE_URL}/")
		return {"Referer": referer}

	def _merge_cookies(self, resp: httpx.Response):
		for name, value in resp.cookies.items():
			if value:
				self._get_client().cookies.set(name, value)

	# ── httpx request (low-risk ops) ─────────────────────────────────

	def _request(self, method: str, url: str, *, _retry_count: int = 0, **kwargs) -> dict:
		client = self._get_client()
		token = self._auth.get_token()
		stoken = token.get("stoken", "")

		if method == "GET":
			params = kwargs.get("params", {})
			params["__zp_stoken__"] = stoken
			kwargs["params"] = params

		self._wait()

		extra_headers = self._headers_for(url)
		resp = client.request(method, url, headers=extra_headers, **kwargs)
		self._mark_request()
		self._merge_cookies(resp)

		if resp.status_code == 403 or "安全验证" in resp.text:
			if _retry_count >= _MAX_RETRIES:
				raise AuthError("Token 刷新后仍被拒绝，请重新登录")
			backoff = (2 ** _retry_count) + random.uniform(0.5, 1.5)
			time.sleep(backoff)
			self._auth.force_refresh()
			self._client = None
			return self._request(method, url, _retry_count=_retry_count + 1, **kwargs)

		resp.raise_for_status()
		data = resp.json()
		code = data.get("code")

		if code == 37 and _retry_count < _MAX_RETRIES:
			backoff = (2 ** _retry_count) + random.uniform(0.5, 1.5)
			time.sleep(backoff)
			self._auth.force_refresh()
			self._client = None
			return self._request(method, url, _retry_count=_retry_count + 1, **kwargs)

		if code == 9 and _retry_count < _MAX_RETRIES:
			cooldown = min(60, 10 * (2 ** _retry_count))
			time.sleep(cooldown)
			return self._request(method, url, _retry_count=_retry_count + 1, **kwargs)

		return data

	# ── Browser request (high-risk ops) ──────────────────────────────

	def _browser_request(self, method: str, url: str, *, params: dict | None = None, data: dict | None = None) -> dict:
		return self._get_browser().request(method, url, params=params, data=data)

	# ── Public API ───────────────────────────────────────────────────
	# High-risk: search, recommend, greet, job_card → browser channel
	# Low-risk: status, me, cities, schema, detail → httpx channel

	def search_jobs(self, query: str, **filters) -> dict:
		params = {"query": query, "page": filters.get("page", 1)}
		if city := filters.get("city"):
			code = endpoints.CITY_CODES.get(city)
			if code is None:
				raise ValueError(f"未知城市: {city}")
			params["city"] = code
		if salary := filters.get("salary"):
			code = endpoints.SALARY_CODES.get(salary)
			if code:
				params["salary"] = code
		if exp := filters.get("experience"):
			code = endpoints.EXPERIENCE_CODES.get(exp)
			if code:
				params["experience"] = code
		if edu := filters.get("education"):
			code = endpoints.EDUCATION_CODES.get(edu)
			if code:
				params["degree"] = code
		if scale := filters.get("scale"):
			code = endpoints.SCALE_CODES.get(scale)
			if code:
				params["scale"] = code
		if industry := filters.get("industry"):
			params["industry"] = industry
		return self._browser_request("GET", endpoints.SEARCH_URL, params=params)

	def recommend_jobs(self, page: int = 1) -> dict:
		params = {"page": page}
		return self._browser_request("GET", endpoints.RECOMMEND_URL, params=params)

	def greet(self, security_id: str, job_id: str, message: str = "") -> dict:
		data = {
			"securityId": security_id,
			"jobId": job_id,
			"greeting": message or "您好，我对该岗位很感兴趣，希望能和您聊一聊。",
		}
		return self._browser_request("POST", endpoints.GREET_URL, data=data)

	def job_card(self, security_id: str, lid: str = "") -> dict:
		params = {"securityId": security_id, "lid": lid}
		return self._browser_request("GET", endpoints.JOB_CARD_URL, params=params)

	# ── Low-risk: httpx channel ──────────────────────────────────────

	def job_detail(self, job_id: str) -> dict:
		params = {"encryptJobId": job_id}
		return self._request("GET", endpoints.DETAIL_URL, params=params)

	def user_info(self) -> dict:
		return self._request("GET", endpoints.USER_INFO_URL)

	def resume_baseinfo(self) -> dict:
		return self._request("GET", endpoints.RESUME_BASEINFO_URL)

	def resume_expect(self) -> dict:
		return self._request("GET", endpoints.RESUME_EXPECT_URL)

	def deliver_list(self, page: int = 1) -> dict:
		params = {"page": page}
		return self._request("GET", endpoints.DELIVER_LIST_URL, params=params)
