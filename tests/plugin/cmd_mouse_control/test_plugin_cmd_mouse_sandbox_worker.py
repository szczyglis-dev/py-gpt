from unittest.mock import MagicMock

from pygpt_net.plugin.cmd_mouse_control.worker_sandbox import Worker


def test_sandbox_worker_state_update_and_normalization():
    worker = Worker()
    worker._update_state_from_ret({
        "url": "https://example.test",
        "viewport_w": 1000,
        "viewport_h": 500,
        "mouse_x": 100,
        "mouse_y": 200,
    })
    assert worker._last_url == "https://example.test"
    assert (worker.viewport_w, worker.viewport_h) == (1000, 500)
    assert (worker._mouse_x, worker._mouse_y) == (100, 200)
    assert worker._denorm_x(500) == 500
    assert worker._denorm_y(500) == 250
    assert worker._denorm_x(-10) == 0
    assert worker._denorm_y(5000) == 500


def test_sandbox_worker_button_and_permission_helpers():
    worker = Worker()
    assert worker._button_from_name(None) == "left"
    assert worker._button_from_name("RIGHT") == "right"
    assert worker._button_from_name("other") == "left"

    worker.plugin = MagicMock()
    worker.plugin.get_option_value.return_value = None
    assert worker._permit("x") is True
    worker.plugin.get_option_value.return_value = False
    assert worker._permit("x") is False


def test_sandbox_worker_screen_state_includes_step():
    worker = Worker()
    worker.viewport_w = 800
    worker.viewport_h = 600
    worker._mouse_x = 12
    worker._mouse_y = 34
    state = worker._get_screen_and_pointer({"params": {"current_step": "step-1"}})
    assert state == {
        "result": "success",
        "current_step": "step-1",
        "screen_w": 800,
        "screen_h": 600,
        "mouse_x": 12,
        "mouse_y": 34,
    }


def test_sandbox_worker_dispatch_maps_commands_without_real_playwright():
    worker = Worker()
    worker.cmd_click = MagicMock(return_value={"ok": True})
    assert worker._dispatch({"cmd": "click", "params": {}}) == {"ok": True}
    worker.cmd_click.assert_called_once()
    assert worker._dispatch({"cmd": "unknown", "params": {}}) is None


def test_sandbox_worker_run_filters_unknown_commands_and_replies():
    worker = Worker()
    worker.plugin = MagicMock()
    worker.plugin.allowed_cmds = ["click"]
    worker.cmds = [
        {"cmd": "unknown", "params": {}},
        {"cmd": "click", "params": {}},
    ]
    worker.is_stopped = MagicMock(return_value=False)
    worker._dispatch = MagicMock(return_value={"result": "ok"})
    worker.reply_more = MagicMock()
    worker.run()
    worker._dispatch.assert_called_once_with({"cmd": "click", "params": {}})
    worker.reply_more.assert_called_once_with([{"result": "ok"}])


def test_sandbox_worker_cleanup_does_not_touch_plugin_browser():
    worker = Worker()
    worker.plugin = MagicMock()
    assert worker.cleanup() is None
    worker.plugin.assert_not_called()
