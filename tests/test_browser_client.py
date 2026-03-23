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


def test_close_cdp_mode_only_closes_page():
	"""CDP 模式下 close() 只关闭 page，不关闭 browser"""
	session = BrowserSession(cookies={}, user_agent="")
	session._is_cdp = True
	session._started = True
	session._page = MagicMock()
	session._browser = MagicMock()
	session._pw = MagicMock()

	session.close()

	session._page.close.assert_called_once()
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
