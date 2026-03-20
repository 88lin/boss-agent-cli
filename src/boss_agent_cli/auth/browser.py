import sys
import time

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

_stealth = Stealth()

LOGIN_URL = "https://login.zhipin.com/?ka=header-login"
HOME_URL = "https://www.zhipin.com/"


def _make_context(browser, *, user_agent: str | None = None):
	params = {
		"viewport": {"width": 1280, "height": 800},
		"locale": "zh-CN",
		"timezone_id": "Asia/Shanghai",
	}
	if user_agent:
		params["user_agent"] = user_agent
	return browser.new_context(**params)


def login_via_browser(*, timeout: int = 120) -> dict:
	with sync_playwright() as p:
		browser = p.chromium.launch(
			headless=False,
			args=[
				"--disable-blink-features=AutomationControlled",
				"--no-first-run",
				"--no-default-browser-check",
			],
		)
		context = _make_context(browser)
		page = context.new_page()
		_stealth.apply_stealth_sync(page)

		# 直接访问登录页
		page.goto(LOGIN_URL, wait_until="domcontentloaded")
		page.wait_for_load_state("networkidle")
		print(f"请在浏览器中扫码登录（超时 {timeout} 秒）...", file=sys.stderr)

		# 轮询 context.cookies() 检测 wt2 出现（避免跨域 document.cookie 限制）
		deadline = time.time() + timeout
		logged_in = False
		while time.time() < deadline:
			cookies_list = context.cookies()
			if any(c["name"] == "wt2" for c in cookies_list):
				logged_in = True
				break
			time.sleep(1)

		if not logged_in:
			browser.close()
			raise TimeoutError(f"扫码登录超时（{timeout}秒）")

		# 登录成功后等一下让页面稳定
		page.wait_for_timeout(2000)

		cookies_list = context.cookies()
		cookies = {c["name"]: c["value"] for c in cookies_list}
		user_agent = page.evaluate("navigator.userAgent")

		# 登录成功后访问主站提取 stoken
		page.goto(HOME_URL, wait_until="domcontentloaded")
		page.wait_for_load_state("networkidle")
		stoken = _extract_stoken(page)

		browser.close()

	return {
		"cookies": cookies,
		"stoken": stoken,
		"user_agent": user_agent,
	}


def refresh_stoken(cookies: dict, user_agent: str) -> str:
	with sync_playwright() as p:
		browser = p.chromium.launch(
			headless=True,
			args=["--disable-blink-features=AutomationControlled"],
		)
		context = _make_context(browser, user_agent=user_agent)
		for name, value in cookies.items():
			context.add_cookies([{
				"name": name,
				"value": value,
				"domain": ".zhipin.com",
				"path": "/",
			}])
		page = context.new_page()
		_stealth.apply_stealth_sync(page)

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
