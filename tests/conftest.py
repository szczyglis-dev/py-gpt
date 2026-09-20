import sys
import os
import pytest
import importlib

_SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
_SRC_PATH_ADDED = _SRC_PATH not in sys.path
if _SRC_PATH_ADDED:
    sys.path.insert(0, _SRC_PATH)

_ENV_MISSING = object()
_QT_QPA_PLATFORM_BEFORE = os.environ.get('QT_QPA_PLATFORM', _ENV_MISSING)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')


@pytest.fixture(scope='session', autouse=True)
def set_env_vars():
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv('ENV_TEST', '1')  # set env = test
    monkeypatch.setenv('TEST_LANGUAGE', 'en')  # force EN locale for tests
    yield
    monkeypatch.undo()


def pytest_sessionfinish(session, exitstatus):
    """Restore process-level bootstrap state changed before test collection."""
    if _SRC_PATH_ADDED:
        try:
            sys.path.remove(_SRC_PATH)
        except ValueError:
            pass

    if _QT_QPA_PLATFORM_BEFORE is _ENV_MISSING:
        os.environ.pop('QT_QPA_PLATFORM', None)
    else:
        os.environ['QT_QPA_PLATFORM'] = _QT_QPA_PLATFORM_BEFORE


@pytest.fixture(autouse=True)
def reload_attachment_module():
    import pygpt_net.item.attachment as mod
    importlib.reload(mod)
    yield
