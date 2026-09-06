from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PySide6.QtCore import Qt

from pygpt_net.ui.widget.option.checkbox import OptionCheckbox
from pygpt_net.ui.widget.option.checkbox_list import OptionCheckboxList
from pygpt_net.ui.widget.option.toggle_label import ToggleLabel


def test_checkbox_translation_falls_back_for_dictionary_key():
    widget = SimpleNamespace()
    with patch("pygpt_net.ui.widget.option.checkbox.trans", side_effect=lambda value: value):
        assert OptionCheckbox.trans_or_not(widget, "dictionary.api_key") == "Api_key"
        assert OptionCheckbox.trans_or_not(widget, "plain.label") == "plain.label"


def test_checkbox_translation_uses_translated_value():
    widget = SimpleNamespace()
    with patch("pygpt_net.ui.widget.option.checkbox.trans", return_value="Translated"):
        assert OptionCheckbox.trans_or_not(widget, "label.key") == "Translated"


def test_checkbox_proxy_methods_update_underlying_controls():
    widget = SimpleNamespace(box=MagicMock(), label=MagicMock(), title="")
    widget.box.isChecked.return_value = True

    OptionCheckbox.setIcon(widget, "icon")
    OptionCheckbox.setText(widget, "Title")
    OptionCheckbox.setChecked(widget, True)

    widget.box.setIcon.assert_called_once_with("icon")
    widget.label.setText.assert_called_once_with("Title")
    assert widget.title == "Title"
    assert OptionCheckbox.isChecked(widget) is True


def test_checkbox_list_places_overlay_button_at_top_right():
    button = MagicMock()
    button.width.return_value = 22
    widget = SimpleNamespace(btn_select=button, _overlay_margin=4, width=lambda: 100)

    OptionCheckboxList._place_select_button(widget)

    button.move.assert_called_once_with(74, 4)


def test_checkbox_list_place_is_safe_without_button():
    widget = SimpleNamespace(btn_select=None, _overlay_margin=4)
    OptionCheckboxList._place_select_button(widget)


def test_checkbox_list_set_text_checked_and_missing_key():
    box = MagicMock()
    box.isChecked.return_value = True
    updater = MagicMock()
    widget = SimpleNamespace(
        boxes={"a": box},
        window=SimpleNamespace(controller=SimpleNamespace(config=SimpleNamespace(
            checkbox_list=SimpleNamespace(on_update=updater)
        ))),
        parent_id="parent",
        id="option",
        option={"x": 1},
    )

    OptionCheckboxList.setText(widget, "a", "Alpha")
    OptionCheckboxList.setChecked(widget, "a", False)

    box.setText.assert_called_once_with("Alpha")
    box.setChecked.assert_called_once_with(False)
    updater.assert_called_once_with("parent", "option", {"x": 1}, False, "a")
    assert OptionCheckboxList.isChecked(widget, "a") is True
    assert OptionCheckboxList.isChecked(widget, "missing") is False


def test_toggle_label_proxy_methods():
    widget = SimpleNamespace(box=MagicMock(), label=MagicMock(), title="")
    widget.box.isChecked.return_value = False

    ToggleLabel.setText(widget, "New")
    ToggleLabel.setChecked(widget, True)

    widget.label.setText.assert_called_once_with("New")
    widget.box.setChecked.assert_called_once_with(True)
    assert ToggleLabel.isChecked(widget) is False
