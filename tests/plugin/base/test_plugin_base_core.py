from unittest.mock import MagicMock, patch

from pygpt_net.item.ctx import CtxItem
from pygpt_net.plugin.base.config import BaseConfig
from pygpt_net.plugin.base.plugin import BasePlugin
from tests.mocks import mock_window


def make_plugin(mock_window):
    plugin = BasePlugin(window=mock_window)
    plugin.id = "sample"
    plugin.name = "Sample"
    plugin.prefix = "Test"
    return plugin


def test_base_config_from_defaults_is_noop(mock_window):
    plugin = make_plugin(mock_window)
    cfg = BaseConfig(plugin)
    assert cfg.from_defaults(plugin) is None
    assert plugin.options == {}


def test_add_option_applies_defaults_and_tooltip(mock_window):
    plugin = make_plugin(mock_window)
    option = plugin.add_option("alpha", "text", value="x", description="desc")
    assert option["id"] == "alpha"
    assert option["type"] == "text"
    assert option["value"] == "x"
    assert option["tooltip"] == "desc"
    assert plugin.setup()["alpha"] is option


def test_add_option_does_not_mutate_global_defaults(mock_window):
    plugin = make_plugin(mock_window)
    plugin.add_option("one", "text", description="first")
    plugin.add_option("two", "text")
    assert plugin.get_option("two")["description"] == ""
    assert BasePlugin.DEFAULT_OPTION["description"] == ""


def test_add_cmd_and_get_cmd_return_independent_copy(mock_window):
    plugin = make_plugin(mock_window)
    plugin.add_cmd(
        "demo",
        instruction="Run demo",
        params={"name": {"type": "str"}},
        enabled=True,
        label="Demo",
    )
    assert plugin.has_cmd("demo") is True
    first = plugin.get_cmd("demo")
    assert first["cmd"] == "demo"
    assert first["instruction"] == "Run demo"
    first["params"]["name"]["type"] = "changed"
    assert plugin.get_cmd("demo")["params"]["name"]["type"] == "str"
    assert plugin.get_cmd("missing") is None


def test_option_access_and_typed_value_conversion(mock_window):
    plugin = make_plugin(mock_window)
    plugin.add_option("flag", "bool", value=0)
    plugin.add_option("count", "int", value="7")
    plugin.add_option("ratio", "float", value="1.25")
    plugin.add_option("text", "text", value="abc")

    assert plugin.has_option("flag") is True
    assert plugin.has_option("missing") is False
    assert plugin.get_option_value("flag") is False
    assert plugin.get_option_value("count") == 7
    assert plugin.get_option_value("ratio") == 1.25
    assert plugin.get_option_value("text") == "abc"
    assert plugin.get_option_value("missing") is None


def test_set_option_value_converts_type_and_refreshes(mock_window):
    plugin = make_plugin(mock_window)
    plugin.add_option("count", "int", value=1)
    plugin.refresh_option = MagicMock()
    plugin.set_option_value("count", "9")
    assert plugin.get_option_value("count") == 9
    plugin.refresh_option.assert_called_once_with("count")

    plugin.refresh_option.reset_mock()
    plugin.set_option_value("missing", 5)
    plugin.refresh_option.assert_not_called()


def test_attach_refresh_and_command_flags(mock_window):
    plugin = make_plugin(mock_window)
    plugin.add_option("x", "text", value="y")
    other_window = MagicMock()
    plugin.attach(other_window)
    assert plugin.window is other_window

    plugin.refresh_option("x")
    other_window.controller.plugins.settings.refresh_option.assert_called_once_with("sample", "x")

    plugin.allowed_cmds = ["ok"]
    assert plugin.cmd_allowed("ok") is True
    assert plugin.cmd_allowed("nope") is False
    other_window.core.config.get.return_value = True
    assert plugin.cmd_exe() is True


def test_trans_uses_plugin_domain_and_handles_none(mock_window):
    plugin = make_plugin(mock_window)
    assert plugin.trans(None) == ""
    with patch("pygpt_net.plugin.base.plugin.trans", return_value="translated") as trans:
        assert plugin.trans("hello") == "translated"
    trans.assert_called_once_with("hello", False, "plugin.sample")


def test_error_debug_reply_and_native_helpers(mock_window):
    plugin = make_plugin(mock_window)
    mock_window.core.debug.parse_alert.return_value = "parsed"
    plugin.error(ValueError("bad"))
    mock_window.core.debug.log.assert_called_once()
    mock_window.ui.dialogs.alert.assert_called_once_with("Sample: parsed")

    plugin.debug("dbg", False)
    mock_window.core.debug.info.assert_called_with("dbg", False)

    plugin.handle_finished = MagicMock()
    ctx = CtxItem()
    plugin.reply({"result": "ok"}, ctx, {"a": 1})
    plugin.handle_finished.assert_called_once_with({"result": "ok"}, ctx, {"a": 1})

    mock_window.core.command.is_native_enabled.return_value = True
    assert plugin.is_native_cmd() is True


def test_is_log_async_and_threaded(mock_window):
    plugin = make_plugin(mock_window)
    mock_window.core.config.set("log.plugins", True)
    assert plugin.is_log() is True

    ctx = CtxItem()
    ctx.async_disabled = True
    assert plugin.is_async(ctx) is False
    mock_window.controller.kernel.async_allowed.assert_not_called()

    ctx.async_disabled = False
    mock_window.controller.kernel.async_allowed.return_value = True
    assert plugin.is_async(ctx) is True
    mock_window.controller.kernel.async_allowed.assert_called_once_with(ctx)

    mock_window.controller.kernel.is_threaded.return_value = True
    assert plugin.is_threaded() is True


def test_log_updates_status_only_outside_thread(mock_window, capsys):
    plugin = make_plugin(mock_window)
    plugin.is_log = MagicMock(return_value=False)
    plugin.is_threaded = MagicMock(return_value=False)
    plugin.debug = MagicMock()
    plugin.log("line\nnext")
    plugin.debug.assert_called_once_with("[Test] line\nnext", True)
    mock_window.update_status.assert_called_once_with("[Test] line next")
    assert capsys.readouterr().out == ""

    mock_window.update_status.reset_mock()
    plugin.is_threaded.return_value = True
    plugin.log("hidden")
    mock_window.update_status.assert_not_called()


def test_log_prints_when_plugin_logging_enabled(mock_window, capsys):
    plugin = make_plugin(mock_window)
    plugin.is_log = MagicMock(return_value=True)
    plugin.is_threaded = MagicMock(return_value=False)
    plugin.debug = MagicMock()
    plugin.log("hello")
    assert "[Test] hello" in capsys.readouterr().out
    plugin.debug.assert_called_once_with("[Test] hello", False)


def test_cmd_prepare_dispatches_busy_state(mock_window):
    plugin = make_plugin(mock_window)
    plugin.cmd_prepare(CtxItem(), [{"cmd": "x"}])
    mock_window.dispatch.assert_called_once()
    event = mock_window.dispatch.call_args.args[0]
    assert event.name == event.STATE_BUSY
    assert event.data == {"id": "img"}


def test_prepare_reply_ctx_filters_results_and_collects_tool_output(mock_window):
    plugin = make_plugin(mock_window)
    ctx = CtxItem()
    response = {
        "request": {"cmd": "x"},
        "result": "ok",
        "context": "ctx text",
        "agent_trace": {"step": 1},
        "private": "extra only",
    }
    mock_window.core.config.set("ctx.use_extra", False)
    returned = plugin.prepare_reply_ctx(response, ctx)

    assert returned is response
    assert ctx.reply is True
    assert ctx.results == [{
        "request": {"cmd": "x"},
        "result": "ok",
        "context": "ctx text",
        "agent_trace": {"step": 1},
    }]
    assert ctx.extra["tool_output"] == [{
        "result": "ok",
        "agent_trace": {"step": 1},
        "private": "extra only",
    }]
    assert "context" not in response


def test_prepare_reply_ctx_moves_context_to_extra_ctx_when_enabled(mock_window):
    plugin = make_plugin(mock_window)
    ctx = CtxItem()
    ctx.extra_ctx = "previous"
    mock_window.core.config.set("ctx.use_extra", True)
    response = {"result": "value", "context": "new context"}

    plugin.prepare_reply_ctx(response, ctx)

    assert ctx.extra_ctx == "previous\n\nnew context"
    assert response["result"] == "OK"
    assert response["context"] == "new context"


def test_handle_finished_dispatches_single_response(mock_window):
    plugin = make_plugin(mock_window)
    ctx = CtxItem()
    plugin.handle_finished({"result": "ok"}, ctx, {"custom": 1})
    mock_window.dispatch.assert_called_once()
    event = mock_window.dispatch.call_args.args[0]
    assert event.name == event.REPLY_ADD
    assert event.data["context"].ctx is ctx
    assert event.data["extra"] == {"custom": 1, "response_type": "single"}


def test_handle_finished_without_context_does_not_dispatch(mock_window):
    plugin = make_plugin(mock_window)
    plugin.handle_finished({"result": "ok"}, None, None)
    mock_window.dispatch.assert_not_called()


def test_handle_finished_more_prepares_all_and_dispatches_once(mock_window):
    plugin = make_plugin(mock_window)
    ctx = CtxItem()
    plugin.prepare_reply_ctx = MagicMock()
    responses = [{"result": 1}, {"result": 2}]
    plugin.handle_finished_more(responses, ctx, {"custom": 2})
    assert plugin.prepare_reply_ctx.call_count == 2
    mock_window.dispatch.assert_called_once()
    event = mock_window.dispatch.call_args.args[0]
    assert event.data["extra"] == {"custom": 2, "response_type": "multiple"}


def test_status_error_debug_log_handlers_and_open_url(mock_window):
    plugin = make_plugin(mock_window)
    plugin.is_threaded = MagicMock(return_value=False)
    plugin.error = MagicMock()
    plugin.debug = MagicMock()
    plugin.log = MagicMock()

    plugin.handle_status(123)
    mock_window.update_status.assert_called_once_with("123")
    plugin.handle_error("err")
    plugin.error.assert_called_once_with("err")
    plugin.handle_debug("dbg")
    plugin.debug.assert_called_once_with("dbg")
    plugin.handle_log("log")
    plugin.log.assert_called_once_with("log")

    plugin.open_url("https://example.com")
    mock_window.controller.dialogs.info.open_url.assert_called_once_with("https://example.com")


def test_status_and_log_handlers_ignore_threaded_calls(mock_window):
    plugin = make_plugin(mock_window)
    plugin.is_threaded = MagicMock(return_value=True)
    plugin.log = MagicMock()
    plugin.handle_status("x")
    plugin.handle_log("y")
    mock_window.update_status.assert_not_called()
    plugin.log.assert_not_called()
