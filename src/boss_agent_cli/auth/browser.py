import sys
import time
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

_stealth = Stealth()

LOGIN_URL = "https://login.zhipin.com/?ka=header-login"
HOME_URL = "https://www.zhipin.com/"

# 浏览器 channel 优先级：系统 Chrome > Edge > Playwright Chromium
_CHANNELS = ["chrome", "msedge", None]


def _get_user_data_dir() -> Path:
	d = Path.home() / ".boss-agent" / "browser-profile"
	d.mkdir(parents=True, exist_ok=True)
	return d


def _launch_persistent(playwright, *, headless: bool = False, user_data_dir: Path | None = None):
	"""使用 persistent context 启动浏览器（真实 profile，最难被检测）"""
	if user_data_dir is None:
		user_data_dir = _get_user_data_dir()

	args = [
		"--disable-blink-features=AutomationControlled",
		"--no-first-run",
		"--no-default-browser-check",
	]

	for channel in _CHANNELS:
		try:
			kwargs = {
				"headless": headless,
				"args": args,
				"viewport": {"width": 1280, "height": 800},
				"locale": "zh-CN",
				"timezone_id": "Asia/Shanghai",
			}
			if channel:
				kwargs["channel"] = channel
			context = playwright.chromium.launch_persistent_context(
				str(user_data_dir),
				**kwargs,
			)
			label = channel or "chromium"
			print(f"使用浏览器: {label}", file=sys.stderr)
			return context
		except Exception:
			continue

	raise RuntimeError("未找到可用的浏览器，请安装 Chrome 或运行 playwright install chromium")


def login_via_browser(*, timeout: int = 120) -> dict:
	with sync_playwright() as p:
		context = _launch_persistent(p, headless=False)
		page = context.pages[0] if context.pages else context.new_page()
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
			context.close()
			raise TimeoutError(f"扫码登录超时（{timeout}秒）")

		page.wait_for_timeout(2000)

		cookies_list = context.cookies()
		cookies = {c["name"]: c["value"] for c in cookies_list}
		user_agent = page.evaluate("navigator.userAgent")

		# 登录成功后访问主站提取 stoken
		page.goto(HOME_URL, wait_until="domcontentloaded")
		page.wait_for_load_state("networkidle")
		stoken = _extract_stoken(page)

		context.close()

	return {
		"cookies": cookies,
		"stoken": stoken,
		"user_agent": user_agent,
	}


def refresh_stoken(cookies: dict, user_agent: str) -> str:
	with sync_playwright() as p:
		# stoken 刷新用临时 profile，注入已有 cookies
		with tempfile.TemporaryDirectory() as tmpdir:
			context = _launch_persistent(
				p,
				headless=True,
				user_data_dir=Path(tmpdir) / "profile",
			)
			# 注入 cookies
			context.add_cookies([
				{"name": name, "value": value, "domain": ".zhipin.com", "path": "/"}
				for name, value in cookies.items()
			])
			page = context.pages[0] if context.pages else context.new_page()
			_stealth.apply_stealth_sync(page)

			page.goto(HOME_URL)
			page.wait_for_load_state("networkidle")
			stoken = _extract_stoken(page)

			context.close()

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
