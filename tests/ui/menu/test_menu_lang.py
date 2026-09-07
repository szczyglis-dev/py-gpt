from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.ui.menu.lang import Lang


def test_setup_initializes_language_actions_and_menu():
    window = SimpleNamespace(ui=SimpleNamespace(menu={}))
    menu = MagicMock()
    with patch("pygpt_net.ui.menu.lang.QMenu", return_value=menu) as cls, \
         patch("pygpt_net.ui.menu.lang.trans", return_value="Language"):
        Lang(window).setup()
    assert window.ui.menu["lang"] == {}
    assert window.ui.menu["menu.lang"] is menu
    cls.assert_called_once_with("Language", window)
