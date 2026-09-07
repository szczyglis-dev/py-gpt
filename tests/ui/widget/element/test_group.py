from types import SimpleNamespace
from unittest.mock import MagicMock

from PySide6.QtCore import Qt

from pygpt_net.ui.widget.element.group import CollapsedGroup


def test_group_update_icon_uses_collapse_for_checked_state():
    widget = SimpleNamespace(box=MagicMock(), _icon_collapse="collapse", _icon_expand="expand")

    CollapsedGroup.update_icon(widget, Qt.Checked)
    widget.box.setIcon.assert_called_once_with("collapse")

    widget.box.setIcon.reset_mock()
    CollapsedGroup.update_icon(widget, Qt.Unchecked)
    widget.box.setIcon.assert_called_once_with("expand")


def test_group_collapse_updates_checkbox_and_options_visibility():
    parent = MagicMock()
    options = MagicMock()
    options.parentWidget.return_value = parent
    widget = SimpleNamespace(box=MagicMock(), options=options)

    CollapsedGroup.collapse(widget, True)

    widget.box.setChecked.assert_called_once_with(True)
    parent.setVisible.assert_called_once_with(True)


def test_group_add_layout_and_widget_delegate_to_options_layout():
    options = MagicMock()
    widget = SimpleNamespace(options=options)
    child_layout = MagicMock()
    child_widget = MagicMock()

    CollapsedGroup.add_layout(widget, child_layout)
    CollapsedGroup.add_widget(widget, child_widget)

    options.addLayout.assert_called_once_with(child_layout)
    options.addWidget.assert_called_once_with(child_widget)
