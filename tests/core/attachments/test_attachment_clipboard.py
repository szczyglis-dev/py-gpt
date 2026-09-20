from collections import deque
import os
from types import SimpleNamespace
from unittest.mock import MagicMock

from PySide6.QtCore import QObject

import pygpt_net.core.attachments.clipboard as clipboard_module
from pygpt_net.core.attachments.clipboard import (
    AttachmentDropHandler,
    DirectoryCountWorker,
    DirectoryEnumerateWorker,
    DirectoryPasteHandler,
)


def test_attachment_clipboard_count_worker_emits_count_and_error(monkeypatch):
    emitted = []
    monkeypatch.setattr(clipboard_module, "safe_emit", lambda source, name, *args: emitted.append((name, args)) or True)
    monkeypatch.setattr(clipboard_module.os, "walk", lambda path: [(path, [], ["a", "b"]), (path + "/x", [], ["c"])])

    worker = DirectoryCountWorker("/tmp/root")
    worker.run()

    assert emitted[-1][0] == "finished"
    assert emitted[-1][1][1:] == ("/tmp/root", 3, None)

    def broken_walk(path):
        raise OSError("boom")
        yield

    emitted.clear()
    monkeypatch.setattr(clipboard_module.os, "walk", broken_walk)
    worker.run()
    assert emitted[-1][1][2] == 0
    assert isinstance(emitted[-1][1][3], OSError)


def test_attachment_clipboard_enumerate_worker_chunks_batches(monkeypatch):
    emitted = []
    monkeypatch.setattr(clipboard_module, "DIRECTORY_SCAN_BATCH_SIZE", 2)
    monkeypatch.setattr(clipboard_module, "safe_emit", lambda source, name, *args: emitted.append((name, args)) or True)
    monkeypatch.setattr(
        clipboard_module.os,
        "walk",
        lambda path: [(path, [], ["a", "b", "c"]), (path + "/sub", [], ["d"])],
    )

    worker = DirectoryEnumerateWorker("/tmp/root")
    worker.run()

    batches = [args[1] for name, args in emitted if name == "batch"]
    assert batches == [
        [os.path.join("/tmp/root", "a"), os.path.join("/tmp/root", "b")],
        [os.path.join("/tmp/root", "c"), os.path.join("/tmp/root/sub", "d")],
    ]
    assert emitted[-1][0] == "finished"
    assert emitted[-1][1][1] is None


def make_paste_handler():
    handler = DirectoryPasteHandler(SimpleNamespace(), QObject())
    handler.window = SimpleNamespace(
        controller=SimpleNamespace(
            attachment=SimpleNamespace(from_clipboard_url=MagicMock()),
        ),
        core=SimpleNamespace(debug=SimpleNamespace(log=MagicMock())),
    )
    handler._workers = set()
    handler._warning_queue = deque()
    handler._warning_active = False
    handler._file_queue = deque()
    handler._add_timer = MagicMock()
    return handler


def test_attachment_clipboard_count_result_routes_warning_or_enumeration(monkeypatch):
    handler = make_paste_handler()
    worker = object()
    handler._workers.add(worker)
    handler._show_next_warning = MagicMock()
    handler._start_enumeration = MagicMock()
    handler._log_error = MagicMock()
    monkeypatch.setattr(DirectoryPasteHandler, "_warning_threshold", staticmethod(lambda: 10))

    handler._on_count_finished(worker, "/large", 11, RuntimeError("scan"))
    assert list(handler._warning_queue) == [("/large", 11)]
    handler._show_next_warning.assert_called_once_with()
    handler._start_enumeration.assert_not_called()
    handler._log_error.assert_called_once()

    handler._show_next_warning.reset_mock()
    handler._on_count_finished(object(), "/small", 3, None)
    handler._start_enumeration.assert_called_once_with("/small")


def test_attachment_clipboard_process_queue_respects_batch_and_logs_errors(monkeypatch):
    handler = make_paste_handler()
    handler._file_queue.extend(["a", "b", "c"])
    handler.window.controller.attachment.from_clipboard_url.side_effect = [None, RuntimeError("bad"), None]
    monkeypatch.setattr(clipboard_module, "DIRECTORY_PASTE_BATCH_SIZE", 2)

    handler._process_file_queue()

    assert handler.window.controller.attachment.from_clipboard_url.call_count == 2
    assert list(handler._file_queue) == ["c"]
    handler._add_timer.stop.assert_not_called()
    handler.window.core.debug.log.assert_called_once()

    handler._process_file_queue()
    assert list(handler._file_queue) == []
    handler._add_timer.stop.assert_called_once_with()


def test_attachment_clipboard_warning_threshold_is_sanitized(monkeypatch):
    monkeypatch.setattr(clipboard_module, "DIRECTORY_PASTE_WARNING_THRESHOLD", -5)
    assert DirectoryPasteHandler._warning_threshold() == 0

    monkeypatch.setattr(clipboard_module, "DIRECTORY_PASTE_WARNING_THRESHOLD", "bad")
    assert DirectoryPasteHandler._warning_threshold() == 10


def test_attachment_drop_handler_mime_and_policy_helpers_without_widget_init():
    handler = AttachmentDropHandler(SimpleNamespace(), QObject())
    image = SimpleNamespace(hasUrls=lambda: False, hasImage=lambda: True, hasText=lambda: False)
    text = SimpleNamespace(hasUrls=lambda: False, hasImage=lambda: False, hasText=lambda: True)

    assert handler._mime_supported(None) is False
    assert handler._mime_supported(image) is True
    assert handler._mime_supported(text) is True
    assert handler._allow_default_text_insert_for_non_image(image) is False
    assert handler._allow_default_text_insert_for_non_image(text) is True
