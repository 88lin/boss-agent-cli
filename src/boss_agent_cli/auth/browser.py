import sys
import time

from playwright.sync_api import sync_playwright

LOGIN_PAGE_URL = "https://www.zhipin.com/web/user/"
HOME_URL = "https://www.zhipin.com/"

# 登录成功的 API 响应 URL 前缀
_LOGIN_SUCCESS_URLS = [
	"https://www.zhipin.com/wapi/zppassport/qrcode/loginConfirm",
	"https://www.zhipin.com/wapi/zppassport/qrcode/dispatcher",
	"https://www.zhipin.com/wapi/zppassport/login/phoneV2",
]

# CDP 注入脚本：在页面 JS 运行之前执行，修补所有自动化检测点
_STEALTH_SCRIPT = """
// 隐藏 navigator.webdriver
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
// 伪造 chrome 对象
window.chrome = {runtime: {}, loadTimes: () => ({}), csi: () => ({})};
// 伪造 plugins
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
// 伪造 languages
Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
// 阻止 window.close
window.close = () => {};
// 拦截 about:blank 重定向
const _origAssign = window.location.assign?.bind(window.location);
const _origReplace = window.location.replace?.bind(window.location);
if (_origAssign) window.location.assign = (url) => { if (url === 'about:blank') return; _origAssign(url); };
if (_origReplace) window.location.replace = (url) => { if (url === 'about:blank') return; _origReplace(url); };
"""


def login_via_browser(*, timeout: int = 120) -> dict:
	with sync_playwright() as p:
		browser = p.chromium.launch(headless=False)
		context = browser.new_context(
			viewport={"width": 1280, "height": 800},
			locale="zh-CN",
			timezone_id="Asia/Shanghai",
		)
		page = context.new_page()

		# 通过 CDP 在页面 JS 之前注入反检测脚本（比 add_init_script 更早）
		cdp = context.new_cdp_session(page)
		cdp.send("Page.addScriptToEvaluateOnNewDocument", {"source": _STEALTH_SCRIPT})

		# 路由层拦截非 zhipin.com 导航
		def _handle_route(route):
			url = route.request.url
			if route.request.is_navigation_request() and not url.startswith("https://www.zhipin.com"):
				route.abort()
			else:
				route.fallback()

		context.route("**/*", _handle_route)

		# 监控页面导航，如果到了 about:blank 立即跳回登录页
		def _on_navigated(frame):
			if frame == page.main_frame and frame.url == "about:blank":
				try:
					page.goto(LOGIN_PAGE_URL, wait_until="domcontentloaded")
				except Exception:
					pass

		page.on("framenavigated", _on_navigated)

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
