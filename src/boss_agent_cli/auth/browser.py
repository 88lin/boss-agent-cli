import sys
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

HOME_URL = "https://www.zhipin.com/"


def login_via_browser(*, timeout: int = 120) -> dict:
	"""
	用 Playwright 自带的 Chromium 打开 BOSS 直聘主站，
	用户手动点击登录并扫码，程序检测到 wt2 cookie 后提取数据。
	"""
	with sync_playwright() as p:
		browser = p.chromium.launch(headless=False)
		context = browser.new_context(
			viewport={"width": 1280, "height": 800},
			locale="zh-CN",
			timezone_id="Asia/Shanghai",
		)
		page = context.new_page()

		# 拦截 BOSS 直聘的反自动化：阻止 window.close() 和跳转 about:blank
		page.add_init_script("""
			window.close = () => {};
			Object.defineProperty(window, 'location', {
				configurable: false,
				get() { return document.location; },
				set(url) {
					if (url === 'about:blank' || url === '') return;
					document.location = url;
				}
			});
		""")
		# 路由层面也拦截 about:blank
		context.route("about:blank", lambda route: route.abort())

		page.goto(HOME_URL, wait_until="domcontentloaded")
		print("已打开 BOSS 直聘主站。", file=sys.stderr)
		print(f"请点击右上角「登录」按钮，扫码登录（超时 {timeout} 秒）...", file=sys.stderr)

		# 轮询 context.cookies() 检测 wt2 cookie
		deadline = time.time() + timeout
		logged_in = False
		while time.time() < deadline:
			try:
				cookies_list = context.cookies()
				if any(c["name"] == "wt2" for c in cookies_list):
					logged_in = True
					break
			except Exception:
				break
			time.sleep(1)

		if not logged_in:
			browser.close()
			raise TimeoutError(f"扫码登录超时（{timeout}秒）")

		time.sleep(2)
		cookies_list = context.cookies()
		cookies = {c["name"]: c["value"] for c in cookies_list}
		user_agent = page.evaluate("navigator.userAgent")

		# 提取 stoken
		stoken = _extract_stoken(page)

		browser.close()

	return {
		"cookies": cookies,
		"stoken": stoken,
		"user_agent": user_agent,
	}


def refresh_stoken(cookies: dict, user_agent: str) -> str:
	"""用 headless Chromium 刷新 stoken"""
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
