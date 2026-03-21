import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

HOME_URL = "https://www.zhipin.com/"
_DEBUG_PORT = 9223


def _find_chromium_path() -> str:
	"""查找 Playwright 安装的 Chromium 路径（独立于系统 Chrome，不会冲突）"""
	system = platform.system()
	base = None

	if system == "Darwin":
		base = Path.home() / "Library" / "Caches" / "ms-playwright"
		# Playwright 在 macOS 上安装为 "Google Chrome for Testing.app" 或 "Chromium.app"
		app_names = [
			"Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
			"Chromium.app/Contents/MacOS/Chromium",
		]
		dir_patterns = ["chrome-mac-arm64", "chrome-mac"]
	elif system == "Linux":
		base = Path.home() / ".cache" / "ms-playwright"
		app_names = ["chrome"]
		dir_patterns = ["chrome-linux"]
	else:
		raise RuntimeError("当前平台暂不支持")

	if base and base.exists():
		for d in sorted(base.iterdir(), reverse=True):
			if d.name.startswith("chromium"):
				for sub in dir_patterns:
					for app in app_names:
						binary = d / sub / app
						if binary.exists():
							return str(binary)

	raise RuntimeError(
		"未找到 Playwright Chromium。请运行:\n"
		"  uv run playwright install chromium"
	)


def _kill_old_debug_chrome(port: int):
	"""杀死可能占用调试端口的旧进程"""
	try:
		subprocess.run(
			["pkill", "-f", f"remote-debugging-port={port}"],
			capture_output=True, timeout=3,
		)
		time.sleep(1)
	except Exception:
		pass


def _wait_for_cdp(port: int, max_wait: int = 15) -> str | None:
	"""等待 CDP 端口可用，返回 WebSocket URL"""
	import json as json_mod
	import urllib.request
	deadline = time.time() + max_wait
	while time.time() < deadline:
		try:
			resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2)
			data = json_mod.loads(resp.read())
			return data.get("webSocketDebuggerUrl", "")
		except Exception:
			time.sleep(1)
	return None


def login_via_browser(*, timeout: int = 120) -> dict:
	"""
	启动 Playwright 的 Chromium（独立于系统 Chrome，不会冲突），
	通过 CDP 连接读取 cookie 数据。
	"""
	chromium_path = _find_chromium_path()

	_kill_old_debug_chrome(_DEBUG_PORT)

	profile_dir = tempfile.mkdtemp(prefix="boss-agent-login-")

	# 启动 Chromium（不是系统 Chrome，不会和用户的 Chrome 冲突）
	proc = subprocess.Popen(
		[
			chromium_path,
			f"--remote-debugging-port={_DEBUG_PORT}",
			f"--user-data-dir={profile_dir}",
			"--remote-allow-origins=*",
			"--disable-blink-features=AutomationControlled",
			"--no-first-run",
			"--no-default-browser-check",
			HOME_URL,
		],
		stdout=subprocess.DEVNULL,
		stderr=subprocess.DEVNULL,
		start_new_session=True,
	)

	print("已启动浏览器并打开 BOSS 直聘主站。", file=sys.stderr)
	print(f"请点击页面右上角「登录」按钮，然后扫码登录（超时 {timeout} 秒）...", file=sys.stderr)

	ws_url = _wait_for_cdp(_DEBUG_PORT)
	if not ws_url:
		proc.terminate()
		raise RuntimeError("浏览器启动失败，CDP 端口未就绪")

	try:
		with sync_playwright() as p:
			browser = p.chromium.connect_over_cdp(ws_url)
			context = browser.contexts[0]

			# 轮询检测 wt2 cookie 出现
			deadline = time.time() + timeout
			logged_in = False
			while time.time() < deadline:
				cookies_list = context.cookies()
				if any(c["name"] == "wt2" for c in cookies_list):
					logged_in = True
					break
				time.sleep(1)

			if not logged_in:
				raise TimeoutError(f"扫码登录超时（{timeout}秒）")

			time.sleep(2)

			cookies_list = context.cookies()
			cookies = {c["name"]: c["value"] for c in cookies_list}

			page = context.pages[0] if context.pages else context.new_page()
			user_agent = page.evaluate("navigator.userAgent")

			# 跳转主站提取 stoken
			page.goto(HOME_URL, wait_until="domcontentloaded")
			page.wait_for_load_state("networkidle")
			stoken = _extract_stoken(page)

			browser.close()
	finally:
		try:
			proc.terminate()
			proc.wait(timeout=5)
		except Exception:
			proc.kill()

	return {
		"cookies": cookies,
		"stoken": stoken,
		"user_agent": user_agent,
	}


def refresh_stoken(cookies: dict, user_agent: str) -> str:
	"""用 headless Chromium 刷新 stoken"""
	chromium_path = _find_chromium_path()
	port = _DEBUG_PORT + 1
	_kill_old_debug_chrome(port)

	with tempfile.TemporaryDirectory() as tmpdir:
		proc = subprocess.Popen(
			[
				chromium_path,
				f"--remote-debugging-port={port}",
				f"--user-data-dir={tmpdir}",
				"--remote-allow-origins=*",
				"--disable-blink-features=AutomationControlled",
				"--headless=new",
				"--no-first-run",
				HOME_URL,
			],
			stdout=subprocess.DEVNULL,
			stderr=subprocess.DEVNULL,
			start_new_session=True,
		)

		ws_url = _wait_for_cdp(port)
		if not ws_url:
			proc.terminate()
			raise RuntimeError("Chromium headless 启动失败")

		try:
			with sync_playwright() as p:
				browser = p.chromium.connect_over_cdp(ws_url)
				context = browser.contexts[0]

				context.add_cookies([
					{"name": name, "value": value, "domain": ".zhipin.com", "path": "/"}
					for name, value in cookies.items()
				])

				page = context.pages[0] if context.pages else context.new_page()
				page.goto(HOME_URL)
				page.wait_for_load_state("networkidle")
				stoken = _extract_stoken(page)

				browser.close()
		finally:
			try:
				proc.terminate()
				proc.wait(timeout=5)
			except Exception:
				proc.kill()

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
