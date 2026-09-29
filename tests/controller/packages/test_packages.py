from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication, QWidget, QMessageBox

from pygpt_net.controller.packages import Packages
from pygpt_net.core.runtime_packages import RuntimePackages


@pytest.fixture
def controller(tmp_path, monkeypatch):
    import pygpt_net.controller.packages as module
    monkeypatch.setattr(module, "trans", lambda key: key)
    app = QApplication.instance() or QApplication([])
    window = QWidget()
    window.core = SimpleNamespace(config=SimpleNamespace(
        get_user_path=lambda: str(tmp_path), get_base_workdir=lambda: str(tmp_path), get=lambda *args: False))
    window.core.packages = RuntimePackages(window)
    window.ui = SimpleNamespace(dialogs=SimpleNamespace(alert=MagicMock()))
    control = Packages(window)
    yield control
    if control.dialog:
        control.dialog.close()
    window.close()


def test_decline_signals_failure_without_starting_worker(controller, monkeypatch):
    monkeypatch.setattr(QMessageBox, 'question', lambda *args: QMessageBox.No)
    callback = MagicMock()
    assert controller.install(['demo'], callback) is False
    callback.assert_called_once_with(False)
    assert controller.worker is None


def test_manager_only_shows_external_packages(controller):
    controller.open()
    assert controller.tree.topLevelItemCount() == 0
    assert controller.input.isEnabled()


def test_dependency_request_is_released_on_decline(controller, monkeypatch):
    import threading
    monkeypatch.setattr(QMessageBox, 'question', lambda *args: QMessageBox.No)
    request = {'requirements': ['demo'], 'event': threading.Event(), 'ok': False}
    controller._dependencies(request)
    assert request['event'].is_set()
    assert request['ok'] is False
