from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.ui.layout.toolbox.computer_env import ComputerEnv


def test_environment_change_ignores_missing_combo():
    window = SimpleNamespace(ui=SimpleNamespace(nodes={}), controller=MagicMock())
    widget = SimpleNamespace(window=window, id="computer_env")

    ComputerEnv._on_env_index_changed(widget, 1)
    window.controller.ui.on_computer_env_changed.assert_not_called()


def test_environment_change_forwards_item_data():
    combo = MagicMock()
    combo.itemData.return_value = "linux"
    window = SimpleNamespace(ui=SimpleNamespace(nodes={"computer_env": combo}), controller=MagicMock())
    widget = SimpleNamespace(window=window, id="computer_env")

    ComputerEnv._on_env_index_changed(widget, 3)

    combo.itemData.assert_called_once_with(3)
    window.controller.ui.on_computer_env_changed.assert_called_once_with("linux")


def test_sandbox_toggle_forwards_boolean():
    window = MagicMock()
    widget = SimpleNamespace(window=window)
    ComputerEnv.on_sandbox_toggled(widget, True)
    window.controller.ui.on_computer_sandbox_toggled.assert_called_once_with(True)
