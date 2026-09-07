from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.ui.dialog.create import Create


def test_setup_creates_create_dialog_and_title():
    window = SimpleNamespace(ui=SimpleNamespace(dialog={}))
    dialog = MagicMock()
    with patch("pygpt_net.ui.dialog.create.CreateDialog", return_value=dialog) as cls, \
         patch("pygpt_net.ui.dialog.create.trans", return_value="Create"):
        Create(window).setup()
    cls.assert_called_once_with(window, "create")
    assert window.ui.dialog["create"] is dialog
    dialog.setWindowTitle.assert_called_once_with("Create")
