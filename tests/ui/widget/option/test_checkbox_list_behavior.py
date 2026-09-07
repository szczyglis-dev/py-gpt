from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.ui.widget.option.checkbox_list import OptionCheckboxList


def _widget(**overrides):
    window = SimpleNamespace(controller=SimpleNamespace(config=SimpleNamespace(
        checkbox_list=SimpleNamespace(on_update=MagicMock())
    )))
    data = dict(
        btn_select=MagicMock(),
        _overlay_margin=4,
        width=lambda: 100,
        boxes={},
        value="a,c",
        keys=[],
        window=window,
        parent_id="parent",
        id="field",
        option={"id": "field"},
    )
    data.update(overrides)
    return SimpleNamespace(**data)


def test_place_select_button_uses_top_right_with_margin():
    button = MagicMock()
    button.width.return_value = 22
    widget = _widget(btn_select=button)

    OptionCheckboxList._place_select_button(widget)

    button.move.assert_called_once_with(74, 4)


def test_place_select_button_handles_too_narrow_widget_and_missing_button():
    button = MagicMock()
    button.width.return_value = 22
    widget = _widget(btn_select=button, width=lambda: 10)
    OptionCheckboxList._place_select_button(widget)
    button.move.assert_called_once_with(0, 4)

    widget.btn_select = None
    OptionCheckboxList._place_select_button(widget)


def test_set_text_checked_and_is_checked_dispatch_only_for_existing_key():
    box = MagicMock()
    box.isChecked.return_value = True
    widget = _widget(boxes={"a": box})

    OptionCheckboxList.setText(widget, "a", "Alpha")
    OptionCheckboxList.setText(widget, "missing", "Ignored")
    OptionCheckboxList.setChecked(widget, "a", True)
    OptionCheckboxList.setChecked(widget, "missing", False)

    box.setText.assert_called_once_with("Alpha")
    box.setChecked.assert_called_once_with(True)
    widget.window.controller.config.checkbox_list.on_update.assert_called_once_with(
        "parent", "field", {"id": "field"}, True, "a"
    )
    assert OptionCheckboxList.isChecked(widget, "a") is True
    assert OptionCheckboxList.isChecked(widget, "missing") is False


class _OldItem:
    def __init__(self, widget):
        self._widget = widget

    def widget(self):
        return self._widget


class _Layout:
    def __init__(self, old_widgets):
        self.old = list(old_widgets)
        self.added = []

    def count(self):
        return len(self.old)

    def takeAt(self, index):
        return _OldItem(self.old.pop(index))

    def addWidget(self, widget):
        self.added.append(widget)


class _Signal:
    def __init__(self):
        self.callback = None

    def connect(self, callback):
        self.callback = callback


class _FakeCheckBox:
    def __init__(self, text, parent):
        self.text = text
        self.parent = parent
        self.checked = None
        self.stateChanged = _Signal()

    def setStyleSheet(self, value):
        self.style = value

    def setChecked(self, value):
        self.checked = value


def test_update_boxes_list_replaces_widgets_preserves_values_and_reconnects_callbacks():
    old1, old2 = MagicMock(), MagicMock()
    layout = _Layout([old1, old2])
    place = MagicMock()
    widget = _widget(layout=layout, boxes={"old": MagicMock()}, value="a,c")
    widget._place_select_button = place

    with patch("pygpt_net.ui.widget.option.checkbox_list.QCheckBox", _FakeCheckBox):
        OptionCheckboxList.update_boxes_list(widget, [{"a": "Alpha"}, {"b": "Beta"}, {"c": "Gamma"}])

    old1.setParent.assert_called_once_with(None)
    old1.deleteLater.assert_called_once_with()
    old2.setParent.assert_called_once_with(None)
    old2.deleteLater.assert_called_once_with()
    assert list(widget.boxes) == ["a", "b", "c"]
    assert widget.boxes["a"].checked is True
    assert widget.boxes["b"].checked is False
    assert widget.boxes["c"].checked is True
    assert layout.added == [widget.boxes["a"], widget.boxes["b"], widget.boxes["c"]]

    widget.boxes["b"].stateChanged.callback(2)
    widget.window.controller.config.checkbox_list.on_update.assert_called_once_with(
        "parent", "field", {"id": "field"}, 2, "b"
    )
    place.assert_called_once_with()
