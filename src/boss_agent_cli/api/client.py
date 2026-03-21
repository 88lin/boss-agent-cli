import random
import time

import httpx

from boss_agent_cli.api import endpoints

_MAX_RETRIES = 2


class AuthError(Exception):
	pass


class BossClient:
	def __init__(self, auth_manager, *, delay: tuple[float, float] = (1.5, 3.0)):
		self._auth = auth_manager
		self._delay = delay
		self._client: httpx.Client | None = None

	def _get_client(self) -> httpx.Client:
		if self._client is None:
			token = self._auth.get_token()
			self._client = httpx.Client(
				base_url=endpoints.BASE_URL,
				cookies=token.get("cookies", {}),
				headers={
					"User-Agent": token.get("user_agent", "Mozilla/5.0"),
					"Referer": "https://www.zhipin.com/",
					"Accept": "application/json, text/plain, */*",
				},
				timeout=30,
			)
		return self._client

	def _wait(self):
		time.sleep(random.uniform(*self._delay))

	def _request(self, method: str, url: str, *, _retry_count: int = 0, **kwargs) -> dict:
		client = self._get_client()
		token = self._auth.get_token()
		stoken = token.get("stoken", "")

		if method == "GET":
			params = kwargs.get("params", {})
			params["__zp_stoken__"] = stoken
			kwargs["params"] = params

		self._wait()
		resp = client.request(method, url, **kwargs)

		if resp.status_code == 403 or "安全验证" in resp.text:
			if _retry_count >= _MAX_RETRIES:
				raise AuthError("Token 刷新后仍被拒绝，请重新登录")
			self._auth.force_refresh()
			self._client = None
			return self._request(method, url, _retry_count=_retry_count + 1, **kwargs)

		resp.raise_for_status()
		return resp.json()

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
		return self._request("GET", endpoints.SEARCH_URL, params=params)

	def job_detail(self, job_id: str) -> dict:
		params = {"encryptJobId": job_id}
		return self._request("GET", endpoints.DETAIL_URL, params=params)

	def job_card(self, security_id: str, lid: str = "") -> dict:
		"""获取职位卡片详情（含职位描述 postDescription）"""
		params = {"securityId": security_id, "lid": lid}
		return self._request("GET", endpoints.JOB_CARD_URL, params=params)

	def greet(self, security_id: str, job_id: str, message: str = "") -> dict:
		data = {
			"securityId": security_id,
			"jobId": job_id,
			"greeting": message or "您好，我对该岗位很感兴趣，希望能和您聊一聊。",
		}
		return self._request("POST", endpoints.GREET_URL, data=data)

	def user_info(self) -> dict:
		return self._request("GET", endpoints.USER_INFO_URL)
