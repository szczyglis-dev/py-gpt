from types import SimpleNamespace
from unittest.mock import MagicMock, call

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.ui.widget.tabs.output import OutputTabBar, OutputTabs


def test_column_index_defaults_to_zero_and_uses_column_value():
    assert OutputTabBar._column_index(SimpleNamespace(column=None)) == 0
    column = SimpleNamespace(get_idx=MagicMock(return_value="1"))
    assert OutputTabBar._column_index(SimpleNamespace(column=column)) == 1


def test_set_corner_target_is_noop_without_button_or_when_unchanged():
    widget = SimpleNamespace(corner_button=None, _corner_current=None, tabs=MagicMock())
    assert OutputTabBar._set_corner_target(widget, 1) is False
    widget.tabs.setCornerWidget.assert_not_called()

    widget.corner_button = object()
    widget._corner_current = 1
    assert OutputTabBar._set_corner_target(widget, 1) is False
    widget.tabs.setCornerWidget.assert_not_called()


def test_set_corner_target_detaches_old_corner_and_attaches_new():
    button = object()
    tabs = MagicMock()
    widget = SimpleNamespace(corner_button=button, _corner_current=1, tabs=tabs)
    assert OutputTabBar._set_corner_target(widget, 2) is True
    assert tabs.setCornerWidget.call_args_list == [call(None, 1), call(button, 2)]
    assert widget._corner_current == 2


def test_set_corner_target_can_detach_without_new_target():
    tabs = MagicMock()
    widget = SimpleNamespace(corner_button=object(), _corner_current=1, tabs=tabs)
    assert OutputTabBar._set_corner_target(widget, None) is True
    tabs.setCornerWidget.assert_called_once_with(None, 1)
    assert widget._corner_current is None


def test_visible_scroll_buttons_uses_extreme_visible_autorepeat_buttons():
    b1, b2, hidden, non_repeat = MagicMock(), MagicMock(), MagicMock(), MagicMock()
    b1.isVisible.return_value = True
    b2.isVisible.return_value = True
    hidden.isVisible.return_value = False
    non_repeat.isVisible.return_value = True
    b1.autoRepeat.return_value = b2.autoRepeat.return_value = True
    non_repeat.autoRepeat.return_value = False
    b1.x.return_value = 5
    b2.x.return_value = 50
    widget = SimpleNamespace(findChildren=MagicMock(return_value=[b2, hidden, b1, non_repeat]))
    left, right = OutputTabBar._visible_scroll_buttons(widget)
    assert left is b1
    assert right is b2


def test_refresh_plus_button_calls_custom_tabbar_method_when_available():
    bar = SimpleNamespace(updateAddButtonPlacement=MagicMock())
    widget = SimpleNamespace(tabBar=MagicMock(return_value=bar))
    OutputTabs._refresh_plus_button(widget)
    bar.updateAddButtonPlacement.assert_called_once_with()


def test_refresh_plus_button_ignores_standard_tabbar():
    widget = SimpleNamespace(tabBar=MagicMock(return_value=SimpleNamespace()))
    OutputTabs._refresh_plus_button(widget)


def test_set_active_get_column_and_owner_are_simple_state_helpers():
    column = object()
    widget = SimpleNamespace(active=False, column=column, owner=None)
    OutputTabs.set_active(widget, True)
    assert widget.active is True
    assert OutputTabs.get_column(widget) is column
    owner = object()
    OutputTabs.setOwner(widget, owner)
    assert widget.owner is owner


def _tabs_widget():
    ui_tabs = SimpleNamespace(
        on_tab_changed=MagicMock(),
        on_tab_clicked=MagicMock(),
        on_tab_dbl_clicked=MagicMock(),
        on_tab_closed=MagicMock(),
        on_tab_moved=MagicMock(),
        rename=MagicMock(),
        close=MagicMock(),
        close_all=MagicMock(),
        append=MagicMock(),
    )
    window = SimpleNamespace(
        controller=SimpleNamespace(ui=SimpleNamespace(tabs=ui_tabs)),
        core=SimpleNamespace(tabs=SimpleNamespace(get_max_idx_by_column=MagicMock(return_value=3))),
    )
    return SimpleNamespace(
        window=window,
        column=SimpleNamespace(get_idx=MagicMock(return_value=1)),
        currentIndex=MagicMock(return_value=4),
        _refresh_plus_button=MagicMock(),
    )


def test_tab_signal_handlers_route_current_index_and_column():
    widget = _tabs_widget()
    OutputTabs._on_current_changed(widget, 99)
    OutputTabs._on_tabbar_clicked(widget, 99)
    OutputTabs._on_tabbar_dbl_clicked(widget, 99)
    OutputTabs._on_tab_moved(widget, 1, 2)

    tabs = widget.window.controller.ui.tabs
    tabs.on_tab_changed.assert_called_once_with(4, 1)
    tabs.on_tab_clicked.assert_called_once_with(4, 1)
    tabs.on_tab_dbl_clicked.assert_called_once_with(4, 1)
    tabs.on_tab_moved.assert_called_once_with(4, 1)


def test_tab_close_handler_routes_and_schedules_refresh(monkeypatch):
    from pygpt_net.ui.widget.tabs import output as output_module

    widget = _tabs_widget()
    single_shot = MagicMock()
    monkeypatch.setattr(output_module, "QTimer", SimpleNamespace(singleShot=single_shot))
    OutputTabs._on_tab_close_requested(widget, 2)
    widget.window.controller.ui.tabs.on_tab_closed.assert_called_once_with(4, 1)
    single_shot.assert_called_once_with(0, widget._refresh_plus_button)


def test_tab_operation_wrappers_route_to_controller():
    widget = _tabs_widget()
    OutputTabs.rename_tab(widget, 2, 1)
    OutputTabs.close_tab(widget, 3, 0)
    OutputTabs.close_all(widget, Tab.TAB_NOTEPAD, 1)

    tabs = widget.window.controller.ui.tabs
    tabs.rename.assert_called_once_with(2, 1)
    tabs.close.assert_called_once_with(3, 0)
    tabs.close_all.assert_called_once_with(Tab.TAB_NOTEPAD, 1)


def test_add_tab_uses_requested_index_for_regular_insert():
    widget = _tabs_widget()
    OutputTabs.add_tab(widget, 5, 1, Tab.TAB_CHAT, tool_id="tool-x")
    widget.window.controller.ui.tabs.append.assert_called_once_with(
        type=Tab.TAB_CHAT,
        tool_id="tool-x",
        idx=5,
        column_idx=1,
    )
    widget.window.core.tabs.get_max_idx_by_column.assert_not_called()


def test_add_tab_resolves_special_new_button_index():
    widget = _tabs_widget()
    OutputTabs.add_tab(widget, -2, 1, Tab.TAB_NOTEPAD)
    widget.window.core.tabs.get_max_idx_by_column.assert_called_once_with(1)
    widget.window.controller.ui.tabs.append.assert_called_once_with(
        type=Tab.TAB_NOTEPAD,
        tool_id=None,
        idx=3,
        column_idx=1,
    )


def test_add_tab_uses_zero_when_column_is_empty():
    widget = _tabs_widget()
    widget.window.core.tabs.get_max_idx_by_column.return_value = -1
    OutputTabs.add_tab(widget, -2, 0, Tab.TAB_CHAT)
    widget.window.controller.ui.tabs.append.assert_called_once_with(
        type=Tab.TAB_CHAT,
        tool_id=None,
        idx=0,
        column_idx=0,
    )
