import sys

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

_stealth = Stealth()

LOGIN_URL = "https://login.zhipin.com/?ka=header-login"
HOME_URL = "https://www.zhipin.com/"


def login_via_browser(*, timeout: int = 120) -> dict:
	with sync_playwright() as p:
		browser = p.chromium.launch(headless=False)
		context = browser.new_context()
		page = context.new_page()
		_stealth.apply_stealth_sync(page)

		page.goto(LOGIN_URL)
		print(f"请在浏览器中扫码登录（超时 {timeout} 秒）...", file=sys.stderr)

		page.wait_for_url(f"{HOME_URL}**", timeout=timeout * 1000)

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
