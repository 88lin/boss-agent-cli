from unittest.mock import patch, MagicMock

from boss_agent_cli.api.browser_client import BrowserSession


def test_browser_session_defaults():
	session = BrowserSession(cookies={"wt2": "abc"}, user_agent="test-ua")
	assert session._is_cdp is False
	assert session._started is False
	assert session._cookies == {"wt2": "abc"}


def test_fetch_ws_url_success():
	with patch("httpx.get") as mock_get:
		mock_resp = MagicMock()
		mock_resp.json.return_value = {"webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/browser/abc"}
		mock_get.return_value = mock_resp
		ws = BrowserSession._fetch_ws_url("http://127.0.0.1:9222")
		assert ws == "ws://127.0.0.1:9222/devtools/browser/abc"


def test_fetch_ws_url_failure():
	with patch("httpx.get", side_effect=Exception("connection refused")):
		ws = BrowserSession._fetch_ws_url("http://127.0.0.1:9222")
		assert ws is None


def test_read_devtools_active_port_missing(tmp_path):
	with patch("boss_agent_cli.api.browser_client._CHROME_USER_DATA_CANDIDATES", [tmp_path / "nonexistent"]):
		ws = BrowserSession._read_devtools_active_port()
		assert ws is None


def test_read_devtools_active_port_found(tmp_path):
	port_file = tmp_path / "DevToolsActivePort"
	port_file.write_text("9222\n/devtools/browser/test-id\n")
	with patch("boss_agent_cli.api.browser_client._CHROME_USER_DATA_CANDIDATES", [tmp_path]):
		ws = BrowserSession._read_devtools_active_port()
		assert ws == "ws://127.0.0.1:9222/devtools/browser/test-id"


def test_close_cdp_mode_closes_page_and_own_context():
	"""CDP 模式下 close() 关闭 page 和自建 context，不关闭 browser"""
	session = BrowserSession(cookies={}, user_agent="")
	session._is_cdp = True
	session._own_context = True
	session._started = True
	session._page = MagicMock()
	session._context = MagicMock()
	session._browser = MagicMock()
	session._pw = MagicMock()

	session.close()

	session._page.close.assert_called_once()
	session._context.close.assert_called_once()
	session._browser.close.assert_not_called()


def test_close_headless_mode_closes_browser():
	"""Headless 模式下 close() 关闭整个 browser"""
	session = BrowserSession(cookies={}, user_agent="")
	session._is_cdp = False
	session._started = True
	session._page = MagicMock()
	session._browser = MagicMock()
	session._pw = MagicMock()

	session.close()

	session._browser.close.assert_called_once()


def test_try_connect_creates_isolated_context():
	"""CDP 连接应从用户 context 提取 Cookie 后创建隔离 context"""
	session = BrowserSession(cookies={}, user_agent="")
	session._pw = MagicMock()

	mock_browser = MagicMock()
	mock_user_context = MagicMock()
	mock_user_context.cookies.return_value = [
		{"name": "wt2", "value": "abc", "domain": ".zhipin.com", "path": "/"},
	]
	mock_browser.contexts = [mock_user_context]
	mock_new_context = MagicMock()
	mock_browser.new_context.return_value = mock_new_context
	mock_page = MagicMock()
	mock_new_context.new_page.return_value = mock_page

	session._pw.chromium.connect_over_cdp.return_value = mock_browser

	result = session._try_connect("ws://localhost:9222/test")

	assert result is True
	assert session._is_cdp is True
	assert session._own_context is True
	# 验证：从用户 context 提取了 Cookie
	mock_user_context.cookies.assert_called_once()
	# 验证：创建了新的隔离 context（不是复用 contexts[0]）
	mock_browser.new_context.assert_called_once()
	# 验证：Cookie 被注入到新 context
	mock_new_context.add_cookies.assert_called_once()
	# 验证：page 在新 context 中创建
	mock_new_context.new_page.assert_called_once()
	# 验证：用户原始 context 没有被创建新 page
	mock_user_context.new_page.assert_not_called()
