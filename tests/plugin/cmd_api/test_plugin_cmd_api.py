from unittest.mock import MagicMock, patch

from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem
from pygpt_net.plugin.cmd_api import Plugin
from pygpt_net.plugin.cmd_api.worker import Worker
from tests.mocks import mock_window


def test_cmd_api_defaults_and_syntax(mock_window):
    plugin = Plugin(window=mock_window)
    options = plugin.setup()
    assert {"cmds", "disable_ssl", "timeout", "user_agent"}.issubset(options)

    data = {"cmd": []}
    plugin.cmd_syntax(data)
    assert data["cmd"] == [{
        "cmd": "search_wiki",
        "instruction": "send API call to Wikipedia to search pages by query",
        "params": [
            {"name": "query", "type": "str", "description": "query"},
            {"name": "limit", "type": "str", "description": "limit"},
        ],
    }]


def test_cmd_api_extract_params_and_get_item(mock_window):
    plugin = Plugin(window=mock_window)
    assert plugin.extract_params(None) == []
    assert plugin.extract_params("") == []
    assert plugin.extract_params(" a, ,b ") == [
        {"name": "a", "type": "str", "description": "a"},
        {"name": "b", "type": "str", "description": "b"},
    ]
    assert plugin.get_item("search_wiki")["type"] == "GET"
    assert plugin.get_item("missing") == {}


def test_cmd_api_handle_routes_syntax_and_execute(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.cmd_syntax = MagicMock()
    event = Event()
    event.name = Event.CMD_SYNTAX
    event.data = {"cmd": []}
    event.ctx = CtxItem()
    plugin.handle(event)
    plugin.cmd_syntax.assert_called_once_with(event.data)

    plugin.cmd = MagicMock()
    event.name = Event.CMD_EXECUTE
    event.data = {"commands": [{"cmd": "search_wiki", "params": {}}]}
    plugin.handle(event)
    plugin.cmd.assert_called_once_with(event.ctx, event.data["commands"])


def test_cmd_api_cmd_filters_and_uses_sync_or_async_worker(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.cmd_prepare = MagicMock()
    ctx = CtxItem()

    with patch("pygpt_net.plugin.cmd_api.plugin.Worker") as worker_cls:
        plugin.is_async = MagicMock(return_value=False)
        plugin.cmd(ctx, [{"cmd": "missing", "params": {}}])
        worker_cls.assert_not_called()

        request = {"cmd": "search_wiki", "params": {"query": "x"}}
        plugin.cmd(ctx, [request])
        worker = worker_cls.return_value
        worker.from_defaults.assert_called_once_with(plugin)
        assert worker.cmds == [request]
        assert worker.ctx is ctx
        worker.run.assert_called_once_with()

    with patch("pygpt_net.plugin.cmd_api.plugin.Worker") as worker_cls:
        plugin.is_async = MagicMock(return_value=True)
        request = {"cmd": "search_wiki", "params": {}}
        plugin.cmd(ctx, [request])
        worker_cls.return_value.run_async.assert_called_once_with()


def test_call_get_uses_mocked_urlopen_and_headers(mock_window):
    plugin = Plugin(window=mock_window)
    response = MagicMock()
    response.read.return_value = b"ok"
    with patch("pygpt_net.plugin.cmd_api.plugin.urlopen", return_value=response) as urlopen:
        result = plugin.call_get("https://example.test/a", {"X-Test": "1"})
    assert result == b"ok"
    req = urlopen.call_args.args[0]
    assert req.full_url == "https://example.test/a"
    assert req.headers["User-agent"] == "Mozilla/5.0"
    assert req.headers["X-test"] == "1"
    assert urlopen.call_args.kwargs["timeout"] == 5


def test_call_get_disable_ssl_passes_non_verifying_context(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.set_option_value("disable_ssl", True)
    response = MagicMock()
    response.read.return_value = b"ok"
    ssl_ctx = MagicMock()
    with patch("pygpt_net.plugin.cmd_api.plugin.ssl.create_default_context", return_value=ssl_ctx), \
            patch("pygpt_net.plugin.cmd_api.plugin.urlopen", return_value=response) as urlopen:
        plugin.call_get("https://example.test")
    assert ssl_ctx.check_hostname is False
    assert urlopen.call_args.kwargs["context"] is ssl_ctx


def test_call_post_and_post_json_encode_payloads(mock_window):
    plugin = Plugin(window=mock_window)
    response = MagicMock()
    response.read.side_effect = [b"form", b"json"]
    with patch("pygpt_net.plugin.cmd_api.plugin.urlopen", return_value=response) as urlopen:
        assert plugin.call_post("https://example.test", {"a": "hello world"}) == b"form"
        form_req = urlopen.call_args_list[0].args[0]
        assert form_req.data == b"a=hello+world"
        assert form_req.headers["Content-type"] == "application/x-www-form-urlencoded"

        assert plugin.call_post_json("https://example.test", {"a": 1}) == b"json"
        json_req = urlopen.call_args_list[1].args[0]
        assert json_req.data == b'{"a": 1}'
        assert json_req.headers["Content-type"] == "application/json"


def test_worker_handle_cmd_get_substitutes_and_quotes_params(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.call_get = MagicMock(return_value=b'{"ok": true}')
    worker = Worker()
    worker.plugin = plugin
    worker.log = MagicMock()
    command = {
        "name": "demo",
        "endpoint": "https://example.test?q={query}",
        "type": "GET",
        "get_params": "query",
        "post_params": "",
        "post_json": "",
        "headers": '{"Authorization": "Bearer x"}',
    }
    item = {"cmd": "demo", "params": {"query": "a b/c"}}
    response = worker.handle_cmd(command, item)
    plugin.call_get.assert_called_once_with(
        "https://example.test?q=a%20b/c",
        {"Authorization": "Bearer x"},
    )
    assert response["result"] == '{"ok": true}'
    assert response["url"] == "https://example.test?q=a%20b/c"
    assert response["type"] == "GET"


def test_worker_handle_cmd_rejects_invalid_headers_json(mock_window):
    plugin = Plugin(window=mock_window)
    worker = Worker()
    worker.plugin = plugin
    worker.log = MagicMock()
    command = {
        "endpoint": "https://example.test",
        "type": "GET",
        "get_params": "",
        "post_params": "",
        "post_json": "",
        "headers": "{bad",
    }
    assert worker.handle_cmd(command, {"cmd": "x", "params": {}}) is False
    worker.log.assert_called_once()


def test_worker_handle_cmd_post_json_uses_template(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.call_post_json = MagicMock(return_value=b"done")
    worker = Worker()
    worker.plugin = plugin
    worker.log = MagicMock()
    command = {
        "endpoint": "https://example.test",
        "type": "POST_JSON",
        "get_params": "",
        "post_params": "name",
        "post_json": '{"name": "%name%"}',
        "headers": "",
    }
    item = {"cmd": "x", "params": {"name": "Alice"}}
    response = worker.handle_cmd(command, item)
    plugin.call_post_json.assert_called_once_with(
        "https://example.test", {"name": "Alice"}, {}
    )
    assert response["result"] == "done"


def test_worker_run_collects_responses_and_cleans_up(mock_window):
    plugin = Plugin(window=mock_window)
    worker = Worker()
    worker.plugin = plugin
    worker.cmds = [{"cmd": "search_wiki", "params": {}}]
    worker.is_stopped = MagicMock(return_value=False)
    worker.handle_cmd = MagicMock(return_value={"result": "ok"})
    worker.reply_more = MagicMock()
    worker.cleanup = MagicMock()
    worker.run()
    worker.reply_more.assert_called_once_with([{"result": "ok"}])
    worker.cleanup.assert_called_once_with()
