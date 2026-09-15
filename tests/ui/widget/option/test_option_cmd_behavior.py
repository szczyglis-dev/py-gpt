from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.ui.widget.option.cmd import OptionCmd


def test_option_cmd_update_item_is_noop_for_read_only_params():
    widget = SimpleNamespace(params=MagicMock())

    assert OptionCmd.update_item(widget, 3, {"value": 7}) is None

    widget.params.update_item.assert_not_called()


def test_option_cmd_update_refreshes_locale():
    widget = SimpleNamespace(update_locale=MagicMock())

    assert OptionCmd.update(widget) is None

    widget.update_locale.assert_called_once_with()
