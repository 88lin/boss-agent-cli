import platform
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

LOGIN_URL = "https://login.zhipin.com/?ka=header-login"
HOME_URL = "https://www.zhipin.com/"
_DEBUG_PORT = 9223


def _find_chrome() -> str:
	"""查找系统 Chrome 可执行文件路径"""
	system = platform.system()
	if system == "Darwin":
		candidates = [
			"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
			"/Applications/Chromium.app/Contents/MacOS/Chromium",
		]
	elif system == "Linux":
		candidates = [
			"google-chrome", "google-chrome-stable",
			"chromium", "chromium-browser",
		]
	elif system == "Windows":
		candidates = [
			r"C:\Program Files\Google\Chrome\Application\chrome.exe",
			r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
		]
	else:
		candidates = []

	for c in candidates:
		if Path(c).exists() or shutil.which(c):
			return c

	raise RuntimeError(
		"未找到系统 Chrome 浏览器。\n"
		"请安装 Google Chrome: https://www.google.com/chrome/"
	)


def _get_profile_dir() -> Path:
	d = Path.home() / ".boss-agent" / "chrome-profile"
	d.mkdir(parents=True, exist_ok=True)
	return d


def _kill_old_debug_chrome(port: int):
	"""杀死可能占用调试端口的旧 Chrome 进程"""
	try:
		subprocess.run(
			["pkill", "-f", f"remote-debugging-port={port}"],
			capture_output=True, timeout=3,
		)
		time.sleep(1)
	except Exception:
		pass


def _wait_for_cdp(port: int, max_wait: int = 10):
	"""等待 CDP 端口可用"""
	import urllib.request
	deadline = time.time() + max_wait
	while time.time() < deadline:
		try:
			urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2)
			return True
		except Exception:
			time.sleep(1)
	return False


def login_via_browser(*, timeout: int = 120) -> dict:
	"""
	直接启动系统 Chrome 进程（非 Playwright 控制），
	Playwright 仅通过 CDP 连接读取数据，不注入自动化标记。
	"""
	chrome_path = _find_chrome()
	profile_dir = _get_profile_dir()

	# 清理可能残留的旧进程
	_kill_old_debug_chrome(_DEBUG_PORT)

	# 启动 Chrome 进程，打开登录页
	proc = subprocess.Popen(
		[
			chrome_path,
			f"--remote-debugging-port={_DEBUG_PORT}",
			f"--user-data-dir={profile_dir}",
			"--remote-allow-origins=*",
			"--no-first-run",
			"--no-default-browser-check",
			LOGIN_URL,
		],
		stdout=subprocess.DEVNULL,
		stderr=subprocess.PIPE,
	)

	print(f"已启动 Chrome，请在浏览器中扫码登录（超时 {timeout} 秒）...", file=sys.stderr)

	# 等待 CDP 端口就绪
	if not _wait_for_cdp(_DEBUG_PORT):
		proc.terminate()
		raise RuntimeError("Chrome 启动失败，CDP 端口未就绪")

	try:
		with sync_playwright() as p:
			# 连接到已运行的 Chrome（只读，不注入自动化标记）
			browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{_DEBUG_PORT}")
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

			# 获取 user_agent
			page = context.pages[0] if context.pages else context.new_page()
			user_agent = page.evaluate("navigator.userAgent")

			# 跳转主站提取 stoken
			page.goto(HOME_URL, wait_until="domcontentloaded")
			page.wait_for_load_state("networkidle")
			stoken = _extract_stoken(page)

			browser.close()
	finally:
		# 关闭 Chrome 进程
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
	"""用临时 Chrome 进程刷新 stoken"""
	chrome_path = _find_chrome()
	port = _DEBUG_PORT + 1
	_kill_old_debug_chrome(port)

	with tempfile.TemporaryDirectory() as tmpdir:
		proc = subprocess.Popen(
			[
				chrome_path,
				f"--remote-debugging-port={port}",
				f"--user-data-dir={tmpdir}",
				"--remote-allow-origins=*",
				"--headless=new",
				"--no-first-run",
				HOME_URL,
			],
			stdout=subprocess.DEVNULL,
			stderr=subprocess.PIPE,
		)

		if not _wait_for_cdp(port):
			proc.terminate()
			raise RuntimeError("Chrome headless 启动失败")

		try:
			with sync_playwright() as p:
				browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
				context = browser.contexts[0]

				# 注入 cookies
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
