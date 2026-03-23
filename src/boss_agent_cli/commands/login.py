import click

from boss_agent_cli.auth.manager import AuthManager
from boss_agent_cli.output import emit_error, emit_success


@click.command("login")
@click.option("--timeout", default=120, help="扫码登录超时时间（秒）")
@click.option("--cookie-source", default=None, help="指定浏览器提取 Cookie（如 chrome/firefox/edge），不指定则自动检测")
@click.option("--cdp", is_flag=True, default=False, help="在 CDP Chrome 中打开登录页（需先 boss-chrome 启动）")
@click.pass_context
def login_cmd(ctx, timeout, cookie_source, cdp):
	"""登录 BOSS 直聘（优先从浏览器提取 Cookie，失败则扫码）"""
	data_dir = ctx.obj["data_dir"]
	logger = ctx.obj["logger"]
	cdp_url = ctx.obj.get("cdp_url")

	if cdp or cdp_url:
		_login_via_cdp(data_dir, logger, cdp_url, timeout)
		return

	auth = AuthManager(data_dir, logger=logger)
	try:
		token = auth.login(timeout=timeout, cookie_source=cookie_source)
		method = "Cookie 提取" if not token.get("stoken") and token.get("cookies") else "扫码登录"
		emit_success("login", {"message": f"登录成功（{method}）"}, hints={
			"next_actions": [
				"boss status — 验证登录态",
				"boss search <query> — 搜索职位",
				"boss recommend — 获取个性化推荐",
			],
		})
	except Exception as e:
		emit_error(
			"login",
			code="NETWORK_ERROR",
			message=f"登录失败: {e}",
			recoverable=True,
			recovery_action="boss login",
		)


def _login_via_cdp(data_dir, logger, cdp_url, timeout):
	"""在 CDP Chrome 中打开 BOSS 直聘登录页，等待用户扫码。"""
	import sys
	import time

	try:
		import httpx
		from patchright.sync_api import sync_playwright

		# 获取 WS URL
		base_url = cdp_url or "http://localhost:9222"
		try:
			resp = httpx.get(f"{base_url}/json/version", timeout=3)
			ws_url = resp.json().get("webSocketDebuggerUrl")
		except Exception:
			emit_error("login", code="NETWORK_ERROR",
				message="CDP 不可用，请先运行 boss-chrome 启动带调试端口的 Chrome",
				recoverable=True, recovery_action="boss-chrome")
			return

		print("[boss] 正在 CDP Chrome 中打开登录页...", file=sys.stderr)
		pw = sync_playwright().start()
		browser = pw.chromium.connect_over_cdp(ws_url)
		ctx = browser.contexts[0] if browser.contexts else browser.new_context()
		page = ctx.new_page()

		try:
			page.goto("https://www.zhipin.com/web/user/?ka=header-login", wait_until="commit", timeout=15000)
		except Exception:
			pass

		print("[boss] 请在 Chrome 中扫码登录，等待中...", file=sys.stderr)

		# 等待登录成功
		for i in range(timeout):
			time.sleep(1)
			cookies = ctx.cookies()
			wt2 = [c for c in cookies if c["name"] == "wt2" and "zhipin" in c.get("domain", "")]
			if wt2:
				print("[boss] 检测到登录成功！", file=sys.stderr)
				break
			if i > 0 and i % 15 == 0:
				print(f"[boss] 等待中... {i}s", file=sys.stderr)
		else:
			page.close()
			pw.stop()
			emit_error("login", code="NETWORK_ERROR",
				message=f"登录超时（{timeout}s），请重试",
				recoverable=True, recovery_action="boss login --cdp")
			return

		# 保存 token
		all_cookies = {c["name"]: c["value"] for c in ctx.cookies() if "zhipin" in c.get("domain", "")}
		ua = page.evaluate("navigator.userAgent")

		from boss_agent_cli.auth.token_store import TokenStore
		store = TokenStore(data_dir / "auth")
		store.save({"cookies": all_cookies, "stoken": "", "user_agent": ua})

		page.close()
		pw.stop()

		emit_success("login", {"message": "登录成功（CDP 扫码）"}, hints={
			"next_actions": [
				"boss status — 验证登录态",
				"boss search <query> — 搜索职位",
			],
		})
	except Exception as e:
		emit_error("login", code="NETWORK_ERROR",
			message=f"CDP 登录失败: {e}",
			recoverable=True, recovery_action="boss login")

