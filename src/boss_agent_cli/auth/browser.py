import sys
import time

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

_stealth = Stealth()

LOGIN_URL = "https://login.zhipin.com/?ka=header-login"
HOME_URL = "https://www.zhipin.com/"

# 尝试使用系统 Chrome，失败则回退到 Playwright Chromium
_LAUNCH_OPTIONS = [
	{"channel": "chrome"},   # 系统 Chrome（最难被检测）
	{"channel": "msedge"},   # 系统 Edge
	{},                      # Playwright 自带 Chromium（兜底）
]


def _launch_browser(playwright, *, headless: bool = False):
	for opts in _LAUNCH_OPTIONS:
		try:
			browser = playwright.chromium.launch(
				headless=headless,
				args=[
					"--disable-blink-features=AutomationControlled",
					"--no-first-run",
					"--no-default-browser-check",
				],
				**opts,
			)
			channel = opts.get("channel", "chromium")
			print(f"使用浏览器: {channel}", file=sys.stderr)
			return browser
		except Exception:
			continue
	raise RuntimeError("未找到可用的浏览器，请安装 Chrome 或运行 playwright install chromium")


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
		browser = _launch_browser(p, headless=False)
		context = _make_context(browser)
		page = context.new_page()
		_stealth.apply_stealth_sync(page)

		page.goto(LOGIN_URL, wait_until="domcontentloaded")
		page.wait_for_load_state("networkidle")
		print(f"请在浏览器中扫码登录（超时 {timeout} 秒）...", file=sys.stderr)

		# 轮询 context.cookies() 检测 wt2 出现
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
		browser = _launch_browser(p, headless=True)
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
