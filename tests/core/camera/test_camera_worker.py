from types import SimpleNamespace
from unittest.mock import MagicMock

import pygpt_net.core.camera.worker as camera_module
from pygpt_net.core.camera.worker import CaptureThread, CaptureWorker


class Resolution:
    def __init__(self, width, height):
        self._width = width
        self._height = height

    def width(self):
        return self._width

    def height(self):
        return self._height


class Format:
    def __init__(self, width, height):
        self._resolution = Resolution(width, height)

    def resolution(self):
        return self._resolution


def test_camera_worker_selects_nearest_format_and_handles_missing_formats():
    worker = CaptureWorker()
    formats = [Format(640, 480), Format(1280, 720), Format(1920, 1080)]
    device = SimpleNamespace(videoFormats=lambda: formats)

    assert worker._select_camera_format(device, 1200, 700) is formats[1]
    assert worker._select_camera_format(SimpleNamespace(videoFormats=lambda: []), 100, 100) is None
    assert worker._select_camera_format(SimpleNamespace(videoFormats=MagicMock(side_effect=RuntimeError("bad"))), 100, 100) is None


def test_camera_worker_capture_thread_delegates_run():
    wrapped = SimpleNamespace(run=MagicMock())
    thread = CaptureThread(wrapped)

    thread.run()

    wrapped.run.assert_called_once_with()


def test_camera_worker_request_stop_quits_loops_and_releases_capture_async(monkeypatch):
    worker = CaptureWorker()
    probe = SimpleNamespace(quit=MagicMock())
    loop = SimpleNamespace(quit=MagicMock())
    cap = SimpleNamespace(release=MagicMock())
    worker._probe_loop = probe
    worker.loop = loop
    worker.cv_cap = cap

    started = []

    class FakeThread:
        def __init__(self, target, name, daemon):
            self.target = target
            self.name = name
            self.daemon = daemon

        def start(self):
            started.append((self.name, self.daemon))
            self.target()

    monkeypatch.setattr(camera_module.threading, "Thread", FakeThread)

    worker.request_stop()

    assert worker._stop_event.is_set()
    probe.quit.assert_called_once_with()
    loop.quit.assert_called_once_with()
    assert worker.cv_cap is None
    cap.release.assert_called_once_with()
    assert started == [("PyGPTCameraRelease", True)]


def test_camera_worker_run_early_stop_finishes_and_marks_done(monkeypatch):
    worker = CaptureWorker()
    signals = MagicMock()
    worker.signals = signals
    worker.window = SimpleNamespace(core=SimpleNamespace(debug=SimpleNamespace(log=MagicMock())))
    worker._stop_event.set()
    worker._teardown_qt = MagicMock()
    worker._teardown_cv2 = MagicMock()
    worker.cleanup = MagicMock()
    emitted = []
    monkeypatch.setattr(camera_module, "safe_emit", lambda source, name, *args: emitted.append(name) or True)

    worker.run()

    assert "finished" in emitted
    worker._teardown_qt.assert_called_once_with()
    worker._teardown_cv2.assert_called_once_with()
    worker.cleanup.assert_called_once_with()
    assert worker.is_done() is True
