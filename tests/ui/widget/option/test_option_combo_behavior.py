from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.ui.widget.option.combo import SeparatorComboBox, NoScrollCombo, OptionCombo


def test_separator_first_and_last_valid_index_skip_marked_rows():
    widget = SimpleNamespace(
        count=lambda: 5,
        is_separator=lambda i: i in {0, 2, 4},
    )
    assert SeparatorComboBox.first_valid_index(widget) == 1
    assert SeparatorComboBox.last_valid_index(widget) == 3


def test_separator_sanitize_prefers_next_then_previous_and_handles_bounds():
    widget = SimpleNamespace(
        count=lambda: 4,
        is_separator=lambda i: i in {1, 3},
        first_valid_index=lambda: 0,
    )
    assert SeparatorComboBox._sanitize_index(widget, None) == 0
    assert SeparatorComboBox._sanitize_index(widget, -4) == 0
    assert SeparatorComboBox._sanitize_index(widget, 10) == 0
    assert SeparatorComboBox._sanitize_index(widget, 1) == 2
    assert SeparatorComboBox._sanitize_index(widget, 3) == 2
    assert SeparatorComboBox._sanitize_index(widget, 2) == 2


def test_separator_sanitize_returns_minus_one_when_every_row_is_separator():
    widget = SimpleNamespace(
        count=lambda: 2,
        is_separator=lambda i: True,
        first_valid_index=lambda: -1,
    )
    assert SeparatorComboBox._sanitize_index(widget, 0) == -1


def test_no_scroll_combo_wheel_event_is_ignored():
    event = MagicMock()
    NoScrollCombo.wheelEvent(SimpleNamespace(), event)
    event.ignore.assert_called_once_with()


def _combo_widget(**overrides):
    combo = MagicMock()
    window = SimpleNamespace(controller=SimpleNamespace(config=SimpleNamespace(
        combo=SimpleNamespace(on_update=MagicMock())
    )))
    values = dict(
        combo=combo,
        current_id=None,
        locked=False,
        keys=[],
        option={"keys": []},
        parent_id="parent",
        id="field",
        window=window,
        title="",
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def test_option_combo_apply_initial_selection_prefers_current_id_and_restores_lock_state():
    widget = _combo_widget(current_id="b", locked=False)
    widget.combo.findData.return_value = 3

    OptionCombo._apply_initial_selection(widget)

    widget.combo.findData.assert_called_once_with("b")
    widget.combo.setCurrentIndex.assert_called_once_with(3)
    assert widget.locked is False


def test_option_combo_apply_initial_selection_falls_back_to_first_valid():
    widget = _combo_widget(current_id="missing", locked=True)
    widget.combo.findData.return_value = -1
    widget.combo.first_valid_index.return_value = 2

    OptionCombo._apply_initial_selection(widget)

    widget.combo.setCurrentIndex.assert_called_once_with(2)
    assert widget.locked is True


def test_option_combo_set_value_ignores_empty_and_sanitizes_unknown():
    widget = _combo_widget()
    OptionCombo.set_value(widget, "")
    widget.combo.findData.assert_not_called()

    widget.combo.findData.return_value = -1
    OptionCombo.set_value(widget, "unknown")
    widget.combo.ensure_valid_current.assert_called_once_with()

    widget.combo.findData.return_value = 4
    OptionCombo.set_value(widget, "known")
    widget.combo.setCurrentIndex.assert_called_once_with(4)


def test_option_combo_change_ignores_lock_and_corrects_separator_before_dispatch():
    widget = _combo_widget(locked=True, current_id="old")
    OptionCombo.on_combo_change(widget, 1)
    assert widget.current_id == "old"
    widget.window.controller.config.combo.on_update.assert_not_called()

    widget.locked = False
    widget.combo.is_separator.return_value = True
    widget.combo.ensure_valid_current.return_value = 2
    widget.combo.itemData.return_value = "new"
    OptionCombo.on_combo_change(widget, 1)
    assert widget.current_id == "new"
    widget.window.controller.config.combo.on_update.assert_called_once_with(
        "parent", "field", widget.option, "new"
    )
    assert widget.locked is False


def test_option_combo_change_separator_with_no_valid_row_clears_value_without_dispatch():
    widget = _combo_widget(current_id="old")
    widget.combo.is_separator.return_value = True
    widget.combo.ensure_valid_current.return_value = -1

    OptionCombo.on_combo_change(widget, 1)

    assert widget.current_id is None
    widget.window.controller.config.combo.on_update.assert_not_called()


def test_option_combo_set_keys_updates_option_and_unlocks_after_locked_refresh():
    widget = _combo_widget()
    widget.update = MagicMock()
    keys = [{"a": "A"}]

    OptionCombo.set_keys(widget, keys, lock=True)

    assert widget.keys == keys
    assert widget.option["keys"] == keys
    widget.combo.clear.assert_called_once_with()
    widget.update.assert_called_once_with()
    widget.combo.ensure_valid_current.assert_called_once_with()
    assert widget.locked is False


def test_option_combo_get_value_and_set_text_are_simple_state_accessors():
    widget = _combo_widget(current_id="x", title="old")
    assert OptionCombo.get_value(widget) == "x"
    OptionCombo.setText(widget, "New title")
    assert widget.title == "New title"
