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
