from types import SimpleNamespace
from unittest.mock import MagicMock

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QWidget
import shiboken6

from pygpt_net.tools.base import BaseTool


def _manager(qapp):
    tool = BaseTool()
    tool.id = 'example'
    tool.allow_tab = True
    tabs = MagicMock()
    tabs.get_tabs_by_tool.return_value = []
    tabs.get_current_tab.return_value = None
    tool.attach(SimpleNamespace(controller=SimpleNamespace(tabs=tabs)))
    from pygpt_net.controller.tabs.operations import TabOperations
    selection = SimpleNamespace(
        _state=SimpleNamespace(recent_pids=[]),
        window=SimpleNamespace(ui=SimpleNamespace(splitters={
            'columns': SimpleNamespace(sizes=lambda: [500, 500])})),
        get_current_tab=tabs.get_current_tab,
        get_current_by_column=tabs.get_current_by_column,
    )
    tabs.preferred_tab.side_effect = lambda items, **kwargs: TabOperations.preferred_tab(selection, items, **kwargs)

    return tool, tabs


def _tab(tool, tabs, column, index):
    tab = SimpleNamespace(column_idx=column, idx=index)
    runtime = object()
    widget = QWidget()
    tool.register_surface(runtime, widget, tab=tab)
    tabs.get_tabs_by_tool.return_value.append(tab)
    return runtime, widget, tab


def test_resolution_prioritizes_recent_then_current_then_ui_order_then_dialog(qapp):
    tool, tabs = _manager(qapp)
    second, second_widget, second_tab = _tab(tool, tabs, 1, 0)
    first, first_widget, first_tab = _tab(tool, tabs, 0, 2)
    dialog, dialog_widget = object(), QWidget()
    tool.register_surface(dialog, dialog_widget, dialog_id='dialog')
    dialog_widget.show()
    tool._last_surface = None
    assert tool.resolve_surface() is first
    tabs.get_current_tab.return_value = second_tab
    assert tool.resolve_surface() is second
    tool.mark_surface_used(dialog)
    assert tool.resolve_surface() is dialog
    dialog_widget.hide()
    assert tool.resolve_surface() is second
    tabs.get_current_tab.return_value = None
    assert tool.resolve_surface() is first
    tabs.get_tabs_by_tool.return_value.clear()
    dialog_widget.show()
    assert tool.resolve_surface() is dialog
    dialog_widget.close()
    assert tool.resolve_surface() is None


def test_deleted_and_unregistered_surfaces_are_never_selected(qapp):
    tool, tabs = _manager(qapp)
    first, widget, tab = _tab(tool, tabs, 0, 0)
    other, other_widget, other_tab = _tab(tool, tabs, 0, 1)
    tool.mark_surface_used(first)
    shiboken6.delete(widget)
    assert tool.resolve_surface() is other
    tool.unregister_surface(other)
    assert tool.resolve_surface() is None


def test_activation_reveals_column_without_changing_chat_context(qapp):
    tool, tabs = _manager(qapp)
    runtime, widget, tab = _tab(tool, tabs, 1, 0)
    tabs.is_split_screen_enabled.return_value = False
    assert tool.resolve_surface(activate=True) is runtime
    tabs.enable_split_screen.assert_called_once_with(update_switch=True)
    tabs.activate_tab.assert_called_once_with(tab, sync_context=False)
    assert tool._last_surface is runtime


def test_focus_inside_frontend_updates_last_used(qapp):
    tool, tabs = _manager(qapp)
    first, widget, tab = _tab(tool, tabs, 0, 0)
    child = QWidget(widget)
    tool._on_surface_focus_changed(None, child)
    assert tool._last_surface is first


def test_creation_only_when_no_surface_and_respects_permissions(qapp):
    tool, tabs = _manager(qapp)
    runtime, widget, tab = _tab(tool, tabs, 0, 0)
    tool.create_surface = MagicMock(return_value=runtime)
    assert tool.resolve_surface(create=True) is runtime
    tool.create_surface.assert_not_called()
    tool.allow_tab = False
    assert tool.resolve_surface() is None
    tool.allow_tab = True
    tool.unregister_surface(runtime)
    def create():
        tool.register_surface(runtime, widget, tab=tab)
        return runtime
    tool.create_surface.side_effect = create
    assert tool.resolve_surface(create=True) is runtime
    tool.create_surface.assert_called_once_with()


def test_visible_surface_wins_over_last_used_hidden_surface(qapp):
    tool, tabs = _manager(qapp)
    first, first_widget, first_tab = _tab(tool, tabs, 0, 0)
    second, second_widget, second_tab = _tab(tool, tabs, 1, 0)
    second_widget.show()
    tabs.get_current_by_column.side_effect = lambda col: second_tab if col == 1 else None
    tool.mark_surface_used(first)
    tabs.get_current_tab.return_value = None
    assert tool.resolve_surface() is second
    second_widget.close()
