from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.ui.widget.option.toggle_label import ToggleLabel


def test_toggle_label_forwards_text_and_checked_state():
    widget = SimpleNamespace(label=MagicMock(), box=MagicMock())
    widget.box.isChecked.return_value = True

    ToggleLabel.setText(widget, "Title")
    ToggleLabel.setChecked(widget, True)

    widget.label.setText.assert_called_once_with("Title")
    widget.box.setChecked.assert_called_once_with(True)
    assert ToggleLabel.isChecked(widget) is True
