from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.ui.dialog.find import Find


def test_setup_creates_find_dialog_and_title():
    window = SimpleNamespace(ui=SimpleNamespace(dialog={}))
    dialog = MagicMock()
    with patch("pygpt_net.ui.dialog.find.FindDialog", return_value=dialog) as cls, \
         patch("pygpt_net.ui.dialog.find.trans", return_value="Find"):
        Find(window).setup()
    cls.assert_called_once_with(window, "find")
    assert window.ui.dialog["find"] is dialog
    dialog.setWindowTitle.assert_called_once_with("Find")
