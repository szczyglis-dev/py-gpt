import sys
import os
import pytest
import importlib

_SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
_SRC_PATH_ADDED = _SRC_PATH not in sys.path
if _SRC_PATH_ADDED:
    sys.path.insert(0, _SRC_PATH)

_ENV_MISSING = object()
_TEST_ENV = {
    'ENV_TEST': '1',
    'TEST_LANGUAGE': 'en',
    'QT_QPA_PLATFORM': 'offscreen',
}
_ENV_BEFORE = {key: os.environ.get(key, _ENV_MISSING) for key in _TEST_ENV}

# These values must be available while pytest imports test modules during
# collection. A session fixture is too late for imports performed at module
# scope (notably pygpt_net.core.audio -> PySide6.QtMultimedia).
for key, value in _TEST_ENV.items():
    os.environ.setdefault(key, value)

# The real application registers compiled Qt resources from pygpt_net.app.
# Most UI tests import widgets directly, so register icons explicitly during
# collection to keep qrc paths such as :/icons/close.svg available.
import pygpt_net.icons_rc  # noqa: E402,F401


def pytest_sessionfinish(session, exitstatus):
    """Restore process-level bootstrap state changed before test collection."""
    if _SRC_PATH_ADDED:
        try:
            sys.path.remove(_SRC_PATH)
        except ValueError:
            pass

    for key, previous in _ENV_BEFORE.items():
        if previous is _ENV_MISSING:
            os.environ.pop(key, None)
        else:
            os.environ[key] = previous


@pytest.fixture(autouse=True)
def reload_attachment_module():
    import pygpt_net.item.attachment as mod
    importlib.reload(mod)
    yield


@pytest.fixture(scope="session", autouse=True)
def qt_application():
    """Keep one QApplication alive across all test directories.

    Dropping the last Python reference between widget tests can destroy Qt's
    application while wrappers or deferred callbacks from previous tests remain.
    No event loop is run here.
    """
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def isolate_native_memory_cleanup(monkeypatch):
    """Controller unit tests must not drain Qt events from other test cases.

    The cleanup utility has its own tests. Exercise tab/debug/controller logic
    without invoking process-wide deferred deletion or native memory trimming.
    """
    for name in ('pygpt_net.core.tabs.tabs', 'pygpt_net.core.debug.console.console',
                 'pygpt_net.controller'):
        module = sys.modules.get(name)
        if module is not None and hasattr(module, 'mem_clean'):
            monkeypatch.setattr(module, 'mem_clean', lambda *args, **kwargs: True)


@pytest.fixture(autouse=True)
def isolate_qt_callbacks(monkeypatch, qt_application):
    """Do not execute one test's delayed UI callbacks during the next test."""
    from PySide6.QtCore import QTimer
    single_shot = QTimer.singleShot
    start = QTimer.start
    timers = []
    active = [True]

    def schedule(delay, callback, *args):
        if args or not callable(callback):
            return single_shot(delay, callback, *args)

        def invoke():
            if active[0]:
                callback()

        return single_shot(delay, invoke)

    monkeypatch.setattr(QTimer, 'singleShot', schedule)

    def start_timer(timer, *args):
        timers.append(timer)
        return start(timer, *args)

    monkeypatch.setattr(QTimer, 'start', start_timer)
    yield
    active[0] = False
    # Repeating widget timers must not wake up while another test pumps Qt.
    from shiboken6 import isValid
    for timer in timers:
        if isValid(timer):
            timer.stop()
