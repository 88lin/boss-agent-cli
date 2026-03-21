import sys
import time

from patchright.sync_api import sync_playwright

LOGIN_PAGE_URL = "https://www.zhipin.com/web/user/"
HOME_URL = "https://www.zhipin.com/"

# 登录成功的 API 响应 URL 前缀
_LOGIN_SUCCESS_URLS = [
	"https://www.zhipin.com/wapi/zppassport/qrcode/loginConfirm",
	"https://www.zhipin.com/wapi/zppassport/qrcode/dispatcher",
	"https://www.zhipin.com/wapi/zppassport/login/phoneV2",
]


def login_via_browser(*, timeout: int = 120) -> dict:
	"""
	使用 patchright（Playwright 反检测 fork）打开登录页。
	patchright 从浏览器二进制层面修补了自动化标记，BOSS 直聘无法检测。
	"""
	with sync_playwright() as p:
		browser = p.chromium.launch(headless=False)
		context = browser.new_context(
			viewport={"width": 1280, "height": 800},
			locale="zh-CN",
			timezone_id="Asia/Shanghai",
		)
		page = context.new_page()

		page.goto(LOGIN_PAGE_URL, wait_until="domcontentloaded")
		print("已打开 BOSS 直聘登录页。", file=sys.stderr)
		print(f"请扫码或手机号登录（超时 {timeout} 秒）...", file=sys.stderr)

		# 监听登录成功的 API 响应
		login_detected = False

		def _on_response(response):
			nonlocal login_detected
			for prefix in _LOGIN_SUCCESS_URLS:
				if response.url.startswith(prefix):
					login_detected = True
					break

		page.on("response", _on_response)

		# 等待登录成功
		deadline = time.time() + timeout
		while time.time() < deadline and not login_detected:
			time.sleep(0.5)

		if not login_detected:
			browser.close()
			raise TimeoutError(f"扫码登录超时（{timeout}秒）")

		print("检测到登录成功，正在提取凭证...", file=sys.stderr)
		time.sleep(3)

		# 跳转主站提取 cookies 和 stoken
		page.goto(HOME_URL, wait_until="domcontentloaded")
		page.wait_for_load_state("networkidle")

		cookies_list = context.cookies()
		cookies = {c["name"]: c["value"] for c in cookies_list}
		user_agent = page.evaluate("navigator.userAgent")
		stoken = _extract_stoken(page)

		browser.close()

	return {
		"cookies": cookies,
		"stoken": stoken,
		"user_agent": user_agent,
	}


def refresh_stoken(cookies: dict, user_agent: str) -> str:
	with sync_playwright() as p:
		browser = p.chromium.launch(headless=True)
		context = browser.new_context(user_agent=user_agent)
		context.add_cookies([
			{"name": name, "value": value, "domain": ".zhipin.com", "path": "/"}
			for name, value in cookies.items()
		])
		page = context.new_page()
		page.goto(HOME_URL)
		page.wait_for_load_state("networkidle")
		stoken = _extract_stoken(page)
		browser.close()

	return stoken


def _extract_stoken(page) -> str:
	try:
		stoken = page.evaluate("""
			() => {
				const match = document.cookie.match(/__zp_stoken__=([^;]+)/);
				return match ? match[1] : '';
			}
		""")
		if not stoken:
			stoken = page.evaluate("() => window.__zp_stoken__ || ''")
		return stoken
	except Exception:
		return ""
