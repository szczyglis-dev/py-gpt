from types import SimpleNamespace
from unittest.mock import MagicMock

import pygpt_net.core.attachments.worker as worker_module
from pygpt_net.core.attachments.worker import AttachmentWorker


def make_worker():
    worker = AttachmentWorker()
    worker.window = SimpleNamespace(
        controller=SimpleNamespace(
            chat=SimpleNamespace(
                attachment=SimpleNamespace(upload=MagicMock()),
            ),
        ),
        core=SimpleNamespace(debug=SimpleNamespace(error=MagicMock())),
    )
    worker.meta = object()
    worker.mode = "query"
    worker.prompt = "hello"
    worker.signals = MagicMock()
    return worker


def test_attachment_worker_uploads_and_emits_success(monkeypatch):
    worker = make_worker()
    signals = worker.signals
    emitted = []
    monkeypatch.setattr(worker_module, "safe_emit", lambda source, name, *args: emitted.append((source, name, args)) or True)

    worker.run()

    worker.window.controller.chat.attachment.upload.assert_called_once_with(worker.meta, "query", "hello")
    assert emitted == [(signals, "success", ("hello",))]
    signals.deleteLater.assert_called_once_with()
    assert worker.signals is None


def test_attachment_worker_emits_error_logs_and_cleans_up(monkeypatch):
    worker = make_worker()
    signals = worker.signals
    error = RuntimeError("upload failed")
    worker.window.controller.chat.attachment.upload.side_effect = error
    emitted = []
    monkeypatch.setattr(worker_module, "safe_emit", lambda source, name, *args: emitted.append((source, name, args)) or True)

    worker.run()

    assert emitted == [(signals, "error", (error,))]
    worker.window.core.debug.error.assert_called_once_with(error)
    signals.deleteLater.assert_called_once_with()
    assert worker.signals is None


def test_attachment_worker_cleanup_ignores_deleted_signal_runtime_error():
    worker = make_worker()
    worker.signals.deleteLater.side_effect = RuntimeError("already deleted")

    worker.cleanup()

    assert worker.signals is None
