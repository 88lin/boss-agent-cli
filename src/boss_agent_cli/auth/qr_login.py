"""QR code login via pure httpx — no browser needed.

Flow: randkey → getqrcode → poll scan → scanLogin/dispatcher → extract cookies.
"""

import sys
from typing import Any
import time

import httpx

from boss_agent_cli.api import endpoints
from boss_agent_cli.api.client import AccountRiskError
from boss_agent_cli.api.zhipin_errors import platform_risk_page_response, raise_platform_risk_response

_POLL_INTERVAL = 2
_DEFAULT_TIMEOUT = 120


def _checked_response(resp: httpx.Response, *, allow_non_json: bool = False) -> dict[str, Any]:
	"""每个认证步骤先分类风险，禁止把安全页当作二维码状态继续轮询。"""
	try:
		payload = resp.json()
	except ValueError:
		payload = None
	if isinstance(payload, dict):
		raise_platform_risk_response(payload)
	try:
		final_url = str(resp.url)
	except (AttributeError, RuntimeError):
		final_url = ""
	page_risk = platform_risk_page_response(
		url=final_url,
		content_type=str(getattr(resp, "headers", {}).get("content-type", "")),
		body=resp.text if isinstance(resp.text, str) else "",
	)
	if page_risk is not None:
		raise_platform_risk_response(page_risk)
	if resp.status_code == 403:
		raise AccountRiskError("二维码登录遇到平台安全验证，请停止并回到官方页面处理", details={"platform_code": None})
	resp.raise_for_status()
	if not isinstance(payload, dict):
		if allow_non_json:
			return {}
		raise RuntimeError("二维码登录响应不是 JSON 对象")
	return payload


def qr_login_httpx(*, timeout: int = _DEFAULT_TIMEOUT) -> dict[str, Any]:
	"""Execute QR login flow via httpx only.

	Returns token dict: {"cookies": {...}, "stoken": "", "user_agent": ua}
	Raises TimeoutError if user doesn't scan in time.
	Raises RuntimeError on unexpected API response.
	"""
	ua = endpoints.DEFAULT_HEADERS.get("User-Agent", "")
	headers = dict(endpoints.DEFAULT_HEADERS)

	with httpx.Client(base_url=endpoints.BASE_URL, headers=headers, follow_redirects=True, timeout=30) as client:
		# Step 1: Get random key for QR code
		resp = client.get(endpoints.QR_RANDKEY_URL)
		data = _checked_response(resp)
		if data.get("code") != 0:
			raise RuntimeError(f"randkey 请求失败: {data}")
		rand_key = data.get("zpData", {}).get("randKey", "")
		if not rand_key:
			raise RuntimeError(f"randkey 返回为空: {data}")

		# Step 2: Get QR code image URL
		resp = client.get(endpoints.QR_GETQRCODE_URL, params={"content": rand_key})
		data = _checked_response(resp)
		qr_id = data.get("zpData", {}).get("qrId", "")
		if not qr_id:
			raise RuntimeError(f"getqrcode 返回为空: {data}")

		# Display QR info for user
		print("[boss] 请使用 BOSS 直聘 App 扫描二维码登录", file=sys.stderr)
		print(f"[boss] 二维码 ID: {qr_id}", file=sys.stderr)
		print(f"[boss] 等待扫码中...（超时 {timeout}s）", file=sys.stderr)

		# Step 3: Poll scan status
		deadline = time.time() + timeout
		scan_confirmed = False
		while time.time() < deadline:
			time.sleep(_POLL_INTERVAL)
			resp = client.get(endpoints.QR_SCAN_URL, params={"qrId": qr_id})
			scan_data = _checked_response(resp)
			scan_code = scan_data.get("code", -1)

			if scan_code == 1:
				# Scanned, waiting for confirm
				print("[boss] 已扫码，等待确认...", file=sys.stderr)
			elif scan_code == 2:
				# Confirmed
				print("[boss] 扫码确认成功！", file=sys.stderr)
				scan_confirmed = True
				break
			elif scan_code == 3:
				raise RuntimeError("二维码已过期，请重新执行 boss login --qr")
			# code 0 = not scanned yet, continue polling

			remaining = int(deadline - time.time())
			if remaining > 0 and remaining % 15 == 0:
				print(f"[boss] 等待中... 剩余 {remaining}s", file=sys.stderr)

		if not scan_confirmed:
			raise TimeoutError(f"QR 登录超时（{timeout}s）")

		# Step 4: Complete login via dispatcher
		resp = client.get(endpoints.QR_DISPATCHER_URL, params={"qrId": qr_id})
		_checked_response(resp, allow_non_json=True)

		# Extract all cookies
		all_cookies = {}
		for cookie in client.cookies.jar:
			if "zhipin" in cookie.domain:
				all_cookies[cookie.name] = cookie.value

		if not all_cookies.get("wt2"):
			raise RuntimeError("QR 登录完成但未获取到 wt2 Cookie，登录可能失败")

		print("[boss] QR 纯 httpx 登录成功！", file=sys.stderr)
		return {
			"cookies": all_cookies,
			"stoken": "",
			"user_agent": ua,
		}
