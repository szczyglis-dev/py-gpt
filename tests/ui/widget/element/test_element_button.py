from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PySide6.QtCore import Qt

from pygpt_net.ui.widget.element.button import ContextMenuButton, NewCtxButton, SyncButton


def test_context_menu_button_invokes_action_for_left_and_right_click():
    action = MagicMock()
    widget = SimpleNamespace(action=action)
    for button in (Qt.LeftButton, Qt.RightButton):
        event = MagicMock()
        event.button.return_value = button
        event.pos.return_value = "pos"
        ContextMenuButton.mousePressEvent(widget, event)
    assert action.call_count == 2
    assert action.call_args.args == (widget, "pos")


def test_new_context_icons_are_cached():
    NewCtxButton._icon_add = None
    NewCtxButton._icon_folder_filled = None
    with patch("pygpt_net.ui.widget.element.button.QIcon") as icon:
        NewCtxButton._ensure_icons()
        NewCtxButton._ensure_icons()
    assert icon.call_count == 2


def test_sync_icon_is_cached():
    SyncButton._icon_download = None
    with patch("pygpt_net.ui.widget.element.button.QIcon") as icon:
        SyncButton._ensure_icons()
        SyncButton._ensure_icons()
    icon.assert_called_once_with(":/icons/download.svg")


def test_new_context_menu_adds_group_action_only_for_active_group():
    ctx = MagicMock()
    ctx.group_id = 4
    ctx.get_group_name.return_value = "Work"
    class Widget:
        _icon_add = object()
        _icon_folder_filled = object()
        @classmethod
        def _ensure_icons(cls):
            pass
    widget = Widget()
    widget.window = SimpleNamespace(controller=SimpleNamespace(ctx=ctx))
    parent = MagicMock()
    parent.mapToGlobal.return_value = "global"
    menu = MagicMock()
    actions = [MagicMock(), MagicMock(), MagicMock()]
    menu.addAction.side_effect = actions

    with patch("pygpt_net.ui.widget.element.button.QMenu", return_value=menu), \
         patch("pygpt_net.ui.widget.element.button.trans", side_effect=lambda key: key):
        NewCtxButton.new_context_menu(widget, parent, "pos")

    assert menu.addAction.call_count == 3
    menu.exec_.assert_called_once_with("global")
    menu.deleteLater.assert_called_once_with()


def test_new_context_menu_without_group_has_two_actions():
    ctx = MagicMock()
    ctx.group_id = None
    class Widget:
        _icon_add = object()
        _icon_folder_filled = object()
        @classmethod
        def _ensure_icons(cls):
            pass
    widget = Widget()
    widget.window = SimpleNamespace(controller=SimpleNamespace(ctx=ctx))
    parent = MagicMock()
    menu = MagicMock()

    with patch("pygpt_net.ui.widget.element.button.QMenu", return_value=menu), \
         patch("pygpt_net.ui.widget.element.button.trans", side_effect=lambda key: key):
        NewCtxButton.new_context_menu(widget, parent, "pos")

    assert menu.addAction.call_count == 2


def test_sync_context_menu_exposes_current_and_all_actions():
    batch = MagicMock()
    class Widget:
        _icon_download = object()
        @classmethod
        def _ensure_icons(cls):
            pass
    widget = Widget()
    widget.window = SimpleNamespace(controller=SimpleNamespace(remote_store=SimpleNamespace(batch=batch)))
    parent = MagicMock()
    menu = MagicMock()
    menu.addAction.side_effect = [MagicMock(), MagicMock()]

    with patch("pygpt_net.ui.widget.element.button.QMenu", return_value=menu), \
         patch("pygpt_net.ui.widget.element.button.trans", side_effect=lambda key: key):
        SyncButton.new_context_menu(widget, parent, "pos")

    assert menu.addAction.call_count == 2
    menu.exec_.assert_called_once_with(parent.mapToGlobal.return_value)
