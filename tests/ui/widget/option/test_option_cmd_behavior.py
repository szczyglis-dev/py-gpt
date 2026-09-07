from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.ui.widget.option.cmd import OptionCmd


def test_option_cmd_update_item_delegates_to_params_widget():
    widget = SimpleNamespace(params=MagicMock())
    OptionCmd.update_item(widget, 3, {"value": 7})
    widget.params.update_item.assert_called_once_with(3, {"value": 7})


def test_option_cmd_update_is_currently_safe_noop():
    widget = SimpleNamespace()
    assert OptionCmd.update(widget) is None
