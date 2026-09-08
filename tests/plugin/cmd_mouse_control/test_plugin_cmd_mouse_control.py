from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem
from pygpt_net.plugin.cmd_mouse_control import Plugin
from tests.mocks import mock_window


def test_mouse_control_surface_and_syntax(mock_window):
    plugin = Plugin(window=mock_window)
    assert plugin.allowed_cmds
    data = {"cmd": []}
    plugin.cmd_syntax(data)
    assert [x["cmd"] for x in data["cmd"]] == [c for c in plugin.allowed_cmds if plugin.has_cmd(c)]


def test_mouse_control_sandbox_flag_reads_config(mock_window):
    plugin = Plugin(window=mock_window)
    mock_window.core.config.set("remote_tools.computer_use.sandbox", True)
    assert plugin.is_sandbox() is True
    mock_window.core.config.set("remote_tools.computer_use.sandbox", False)
    assert plugin.is_sandbox() is False


def test_get_worker_uses_native_worker_when_not_sandboxed(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.is_sandbox = MagicMock(return_value=False)
    worker = MagicMock()
    fake_mod = ModuleType("pygpt_net.plugin.cmd_mouse_control.worker")
    fake_mod.Worker = MagicMock(return_value=worker)
    with patch.dict("sys.modules", {"pygpt_net.plugin.cmd_mouse_control.worker": fake_mod}):
        assert plugin.get_worker() is worker
    fake_mod.Worker.assert_called_once_with()


def test_get_worker_uses_sandbox_worker_and_connects_control_signals(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.is_sandbox = MagicMock(return_value=True)
    worker = MagicMock()
    fake_mod = ModuleType("pygpt_net.plugin.cmd_mouse_control.worker_sandbox")
    fake_mod.Worker = MagicMock(return_value=worker)
    with patch.dict("sys.modules", {"pygpt_net.plugin.cmd_mouse_control.worker_sandbox": fake_mod}):
        assert plugin.get_worker() is worker
    worker.signals.start.connect.assert_called_once_with(plugin.on_playwright_start)
    worker.signals.call.connect.assert_called_once_with(plugin.on_playwright_call)


def test_cmd_filters_and_routes_sync_worker(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.cmd_prepare = MagicMock()
    plugin.is_async = MagicMock(return_value=False)
    worker = MagicMock()
    plugin.get_worker = MagicMock(return_value=worker)
    ctx = CtxItem()

    plugin.cmd(ctx, [{"cmd": "foreign", "params": {}}])
    worker.from_defaults.assert_not_called()

    request = {"cmd": plugin.allowed_cmds[0], "params": {}}
    plugin.cmd(ctx, [request])
    worker.from_defaults.assert_called_once_with(plugin)
    assert worker.cmds == [request]
    assert worker.ctx is ctx
    worker.run.assert_called_once_with()


def test_handle_call_forces_no_screenshot_and_runs_sync(mock_window):
    plugin = Plugin(window=mock_window)
    worker = MagicMock()
    plugin.get_worker = MagicMock(return_value=worker)
    item = {"cmd": "click", "params": {}}
    plugin.handle_call(item)
    assert item["params"]["no_screenshot"] is True
    worker.from_defaults.assert_called_once_with(plugin)
    assert worker.cmds == [item]
    assert isinstance(worker.ctx, CtxItem)
    worker.run.assert_called_once_with()


def test_is_google_checks_context_model_provider(mock_window):
    plugin = Plugin(window=mock_window)
    ctx = CtxItem()
    assert plugin.is_google(ctx) is False
    ctx.model = "m"
    mock_window.core.models.get.return_value = SimpleNamespace(provider="google")
    assert plugin.is_google(ctx) is True
    mock_window.core.models.get.return_value = SimpleNamespace(provider="openai")
    assert plugin.is_google(ctx) is False


def test_handle_finished_more_prepares_each_response_and_disables_screenshot_on_flag(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.prepare_reply_ctx = MagicMock()
    plugin.handle_delayed = MagicMock()
    ctx = CtxItem()
    responses = [
        {"result": {"ok": True}},
        {"result": {"no_screenshot": True}},
    ]
    plugin.handle_finished_more(responses, ctx)
    assert plugin.prepare_reply_ctx.call_count == 2
    assert ctx.reply is True
    plugin.handle_delayed.assert_called_once_with(ctx, True)


def test_handle_delayed_uses_qtimer_only_when_screenshot_allowed(mock_window):
    plugin = Plugin(window=mock_window)
    ctx = CtxItem()
    plugin.set_option_value("allow_screenshot", True)
    with patch("pygpt_net.plugin.cmd_mouse_control.plugin.QTimer.singleShot") as single_shot:
        plugin.handle_delayed(ctx, True)
    single_shot.assert_called_once()
    assert single_shot.call_args.args[0] == plugin.SLEEP_TIME

    mock_window.dispatch.reset_mock()
    plugin.set_option_value("allow_screenshot", False)
    plugin.handle_delayed(ctx, True)
    mock_window.dispatch.assert_called_once()
    event = mock_window.dispatch.call_args.args[0]
    assert event.data["extra"]["response_type"] == "multiple"


def test_delayed_screenshot_native_attaches_local_image_and_dispatches(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.is_sandbox = MagicMock(return_value=False)
    mock_window.controller.painter.capture.screenshot.return_value = "/tmp/a.png"
    mock_window.core.filesystem.make_local.return_value = "local:a.png"
    ctx = CtxItem()
    plugin.delayed_screenshot(ctx)
    mock_window.controller.attachment.clear_silent.assert_called_once_with()
    mock_window.controller.painter.capture.screenshot.assert_called_once_with(attach_cursor=True, silent=True, append_to_ctx=False)
    assert ctx.images_before == []
    assert ctx.transport_images == ["local:a.png"]
    mock_window.core.attachments.register_ctx_excluded_path.assert_called_once_with("/tmp/a.png")
    mock_window.dispatch.assert_called_once()


def test_delayed_screenshot_sandbox_uses_playwright_capture(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.is_sandbox = MagicMock(return_value=True)
    mock_window.controller.painter.capture.screenshot_playwright.return_value = "/tmp/a.png"
    mock_window.core.filesystem.make_local.return_value = "local:a.png"
    ctx = CtxItem()
    plugin.delayed_screenshot(ctx)
    mock_window.controller.painter.capture.screenshot_playwright.assert_called_once_with(
        page=plugin.page, silent=True, append_to_ctx=False, attach_cursor=True, cursor_position=(0, 0)
    )
    assert ctx.images_before == []
    assert ctx.transport_images == ["local:a.png"]
    mock_window.core.attachments.register_ctx_excluded_path.assert_called_once_with("/tmp/a.png")


def test_key_mapping_and_viewport_helpers(mock_window):
    plugin = Plugin(window=mock_window)
    assert plugin._key_to_playwright("ctrl") == "Control"
    assert plugin._key_to_playwright("enter") == "Enter"
    assert plugin._key_to_playwright("F12") == "F12"
    assert plugin._key_to_playwright("x") == "x"

    plugin.page = SimpleNamespace(viewport_size={"width": 800, "height": 600}, url="https://example.test")
    assert plugin._get_viewport() == (800, 600)
    assert plugin.get_last_url() == "https://example.test"


def test_press_combo_uses_playwright_chord(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.page = MagicMock()
    plugin._press_combo(["ctrl", "l"], delay=0.01)
    plugin.page.keyboard.press.assert_called_once_with("Control+l", delay=0.01)


def test_playwright_call_unknown_operation_always_sets_done(mock_window):
    plugin = Plugin(window=mock_window)
    plugin._get_url = MagicMock(return_value="https://example.test")
    done = MagicMock()
    ret = {}
    plugin.on_playwright_call("unknown", {}, ret, done)
    assert ret == {"ok": False, "error": "Unknown op: unknown", "url": "https://example.test"}
    done.set.assert_called_once_with()


def test_system_prompt_appends_plugin_prompt(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.set_option_value("prompt", "TOOLS")
    assert plugin.on_system_prompt("base") == "base\n\nTOOLS"
    assert plugin.on_system_prompt("") == "TOOLS"


def test_handle_routes_system_prompt_only_when_commands_enabled(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.cmd_exe = MagicMock(return_value=True)
    plugin.on_system_prompt = MagicMock(return_value="changed")
    event = Event()
    event.name = Event.SYSTEM_PROMPT
    event.data = {"value": "base"}
    event.ctx = CtxItem()
    plugin.handle(event)
    assert event.data["value"] == "changed"
