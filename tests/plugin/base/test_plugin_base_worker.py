from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.item.ctx import CtxItem
from pygpt_net.plugin.base.worker import BaseWorker
from tests.mocks import mock_window


def fake_signals():
    return SimpleNamespace(
        debug=SimpleNamespace(emit=MagicMock()),
        destroyed=SimpleNamespace(emit=MagicMock()),
        error=SimpleNamespace(emit=MagicMock()),
        log=SimpleNamespace(emit=MagicMock()),
        finished=SimpleNamespace(emit=MagicMock()),
        finished_more=SimpleNamespace(emit=MagicMock()),
        started=SimpleNamespace(emit=MagicMock()),
        status=SimpleNamespace(emit=MagicMock()),
        stopped=SimpleNamespace(emit=MagicMock()),
        deleteLater=MagicMock(),
    )


def test_signal_helpers_emit_and_cleanup():
    worker = BaseWorker()
    sig = fake_signals()
    worker.signals = sig
    worker.debug("d")
    worker.destroyed()
    worker.error("e")
    worker.started()
    worker.stopped()
    sig.debug.emit.assert_called_once_with("d")
    sig.destroyed.emit.assert_called_once_with()
    sig.error.emit.assert_called_once_with("e")
    sig.started.emit.assert_called_once_with()
    sig.stopped.emit.assert_called_once_with()

    worker.cleanup()
    assert worker.signals is None
    sig.deleteLater.assert_called_once_with()


def test_signal_helpers_are_safe_after_cleanup():
    worker = BaseWorker()
    worker.signals = None
    worker.debug("d")
    worker.destroyed()
    worker.error("e")
    worker.started()
    worker.stopped()
    worker.status("s")
    worker.log("l")


def test_log_and_status_skip_threaded_worker():
    worker = BaseWorker()
    sig = fake_signals()
    worker.signals = sig
    worker.is_threaded = MagicMock(return_value=True)
    worker.log("l")
    worker.status("s")
    sig.log.emit.assert_not_called()
    sig.status.emit.assert_not_called()


def test_log_and_status_emit_when_not_threaded():
    worker = BaseWorker()
    sig = fake_signals()
    worker.signals = sig
    worker.is_threaded = MagicMock(return_value=False)
    worker.log("l")
    worker.status("s")
    sig.log.emit.assert_called_once_with("l")
    sig.status.emit.assert_called_once_with("s")


def test_reply_legacy_agent_calls_plugin_directly():
    plugin = MagicMock()
    worker = BaseWorker(plugin)
    worker.signals = fake_signals()
    ctx = CtxItem()
    ctx.agent_call = True
    ctx.extra = {}
    worker.ctx = ctx
    worker.reply({"result": "ok"}, {"x": 1})
    plugin.handle_finished.assert_called_once_with({"result": "ok"}, ctx, {"x": 1})
    worker.signals.finished.emit.assert_not_called()


def test_reply_agents_v2_uses_finished_signal():
    plugin = MagicMock()
    worker = BaseWorker(plugin)
    worker.signals = fake_signals()
    ctx = CtxItem()
    ctx.agent_call = True
    ctx.extra = {"agents_v2_async_tool": True}
    worker.ctx = ctx
    worker.reply({"result": "ok"}, None)
    plugin.handle_finished.assert_not_called()
    worker.signals.finished.emit.assert_called_once_with({"result": "ok"}, ctx, None)


def test_reply_non_agent_uses_finished_signal():
    worker = BaseWorker()
    worker.signals = fake_signals()
    worker.ctx = CtxItem()
    worker.reply({"result": "ok"}, {"a": 1})
    worker.signals.finished.emit.assert_called_once_with({"result": "ok"}, worker.ctx, {"a": 1})


def test_reply_more_legacy_and_agents_v2_paths():
    plugin = MagicMock()
    worker = BaseWorker(plugin)
    worker.signals = fake_signals()
    ctx = CtxItem()
    ctx.agent_call = True
    worker.ctx = ctx
    responses = [{"result": 1}, {"result": 2}]

    ctx.extra = {}
    worker.reply_more(responses, {"x": 1})
    plugin.handle_finished_more.assert_called_once_with(responses, ctx, {"x": 1})

    plugin.reset_mock()
    worker.signals.finished_more.emit.reset_mock()
    ctx.extra = {"agents_v2_async_tool": True}
    worker.reply_more(responses, None)
    plugin.handle_finished_more.assert_not_called()
    worker.signals.finished_more.emit.assert_called_once_with(responses, ctx, None)


def test_from_request_preserves_json_native_values_and_stringifies_non_json():
    worker = BaseWorker()
    marker = object()
    data = worker.from_request({
        "cmd": "read",
        "params": {
            "path": ["a", "b"],
            "query": marker,
            "ignored": "x",
        },
    })
    assert data["cmd"] == "read"
    assert data["path"] == ["a", "b"]
    assert data["query"] == str(marker)
    assert "ignored" not in data


def test_make_response_merges_extra_fields():
    worker = BaseWorker()
    response = worker.make_response(
        {"cmd": "x", "params": {"query": "q"}},
        {"ok": True},
        {"context": "ctx", "agent_trace": 1},
    )
    assert response == {
        "request": {"cmd": "x", "query": "q"},
        "result": {"ok": True},
        "context": "ctx",
        "agent_trace": 1,
    }


def test_security_helpers_forward_to_security_layer(mock_window):
    plugin = MagicMock()
    plugin.window = mock_window
    worker = BaseWorker(plugin)
    mock_window.core.security.ensure_read.return_value = "/safe/read"
    mock_window.core.security.ensure_write.return_value = "/safe/write"
    mock_window.core.security.ensure_command.return_value = ["echo", "ok"]

    assert worker.security_read("a", sandbox=True) == "/safe/read"
    assert worker.security_write("b", sandbox=False) == "/safe/write"
    assert worker.security_command("echo ok", sandbox=True) == ["echo", "ok"]
    mock_window.core.security.ensure_read.assert_called_once_with("a", sandbox=True, ctx=None)
    mock_window.core.security.ensure_write.assert_called_once_with("b", sandbox=False, ctx=None)
    mock_window.core.security.ensure_command.assert_called_once_with("echo ok", sandbox=True)


def test_security_helpers_fallback_without_plugin():
    worker = BaseWorker()
    assert worker.security_read("a") == "a"
    assert worker.security_write("b") == "b"
    assert worker.security_command("echo ok") == []


def test_throw_error_reports_and_returns_message():
    worker = BaseWorker()
    worker.error = MagicMock()
    worker.log = MagicMock()
    exc = ValueError("bad")
    assert worker.throw_error(exc) == "Error: bad"
    worker.error.assert_called_once_with(exc)
    worker.log.assert_called_once_with("Error: bad")


def test_param_helpers_cover_missing_and_present_values():
    worker = BaseWorker()
    assert worker.has_param(None, "x") is False
    assert worker.has_param({}, "x") is False
    assert worker.has_param({"params": {"x": 0}}, "x") is True
    assert worker.get_param({"params": {"x": 0}}, "x", 7) == 0
    assert worker.get_param({"params": {}}, "x", 7) == 7


def test_is_stopped_and_threaded_delegate_to_plugin(mock_window):
    plugin = MagicMock()
    plugin.window = mock_window
    plugin.is_threaded.return_value = True
    mock_window.controller.kernel.stopped.return_value = True
    worker = BaseWorker(plugin)
    assert worker.is_threaded() is True
    assert worker.is_stopped() is True

    worker.plugin = None
    assert worker.is_threaded() is False
    assert worker.is_stopped() is False


def test_run_sync_calls_run():
    worker = BaseWorker()
    worker.run = MagicMock()
    worker.run_sync()
    worker.run.assert_called_once_with()


def test_run_async_marks_agents_v2_pending_and_uses_threadpool(mock_window):
    plugin = MagicMock()
    plugin.window = mock_window
    worker = BaseWorker(plugin)
    worker.window = mock_window
    worker.ctx = CtxItem()
    worker.ctx.extra = {"agents_v2_async_tool": True}
    with patch("pygpt_net.plugin.base.worker.mark_pending") as mark_pending:
        worker.run_async()
    mark_pending.assert_called_once_with(worker.ctx, True)
    mock_window.threadpool.start.assert_called_once_with(worker)


def test_run_async_without_window_runs_inline():
    worker = BaseWorker()
    worker.run = MagicMock()
    worker.run_async()
    worker.run.assert_called_once_with()
