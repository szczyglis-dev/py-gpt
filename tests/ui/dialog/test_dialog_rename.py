from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.ui.dialog.rename import Rename


def test_setup_creates_rename_dialog_and_title():
    window = SimpleNamespace(ui=SimpleNamespace(dialog={}))
    dialog = MagicMock()
    with patch("pygpt_net.ui.dialog.rename.RenameDialog", return_value=dialog) as cls, \
         patch("pygpt_net.ui.dialog.rename.trans", return_value="Rename"):
        Rename(window).setup()
    cls.assert_called_once_with(window, "rename")
    assert window.ui.dialog["rename"] is dialog
    dialog.setWindowTitle.assert_called_once_with("Rename")
