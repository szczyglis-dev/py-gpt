from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

from pygpt_net.core.tabs.tab import Tab


def test_debug_and_add_delegate_to_core(tabs_env):
    tabs, window = tabs_env.tabs, tabs_env.window
    window.controller.dialogs.debug.is_active.return_value = True
    tabs.debug()
    window.core.tabs.toggle_debug.assert_called_once_with(True)

    window.core.tabs.add.return_value = "created"
    assert tabs.add(7, "Title", icon="i", child="c", data_id=9, tool_id="t") == "created"
    window.core.tabs.add.assert_called_once_with(
        type=7, title="Title", icon="i", child="c", data_id=9, tool_id="t"
    )


def test_debug_is_noop_when_debug_dialog_inactive(tabs_env):
    tabs_env.window.controller.dialogs.debug.is_active.return_value = False
    tabs_env.tabs.debug()
    tabs_env.core_tabs.toggle_debug.assert_not_called()


def test_append_creates_tab_transaction_and_finalizes_with_handler(tabs_env):
    tabs = tabs_env.tabs
    created = tabs_env.make_tab(pid=8, idx=2, column_idx=1, type=Tab.TAB_CHAT)
    tabs_env.core_tabs.append.return_value = created
    tabs.handler.on_created = MagicMock(return_value=created)

    result = tabs.append(
        Tab.TAB_CHAT,
        idx=2,
        column_idx=1,
        activate=False,
        create_chat_context=False,
        data_id=55,
    )

    assert result is created
    tabs_env.core_tabs.append.assert_called_once_with(type=Tab.TAB_CHAT, idx=2, column_idx=1, tool_id=None)
    tabs.handler.on_created.assert_called_once_with(
        created,
        activate=False,
        create_chat_context=False,
        data_id=55,
    )
    assert tabs.are_tab_events_suppressed() is False


def test_append_reuses_single_instance_tool_and_activation_rules(tabs_env):
    tabs, window = tabs_env.tabs, tabs_env.window
    existing = tabs_env.make_tab(pid=9, idx=0, column_idx=0, type=Tab.TAB_TOOL, tool_id="canvas")
    tabs.get_first_tab_by_tool = MagicMock(return_value=existing)
    window.tools.get.return_value = SimpleNamespace(single_instance=True)
    tabs.activate_tab = MagicMock()

    assert tabs.append(Tab.TAB_TOOL, tool_id="canvas") is existing
    tabs.activate_tab.assert_called_once_with(existing)
    tabs_env.core_tabs.append.assert_not_called()

    tabs.activate_tab.reset_mock()
    existing.column_idx = 1
    tabs.is_split_screen_enabled = MagicMock(return_value=False)
    assert tabs.append(Tab.TAB_TOOL, tool_id="canvas") is existing
    tabs.activate_tab.assert_not_called()


def test_activate_tab_handles_none_and_context_sync_modes(tabs_env):
    tabs = tabs_env.tabs
    tab = tabs_env.make_tab(pid=3, idx=2, column_idx=1)
    tabs.switch_tab_by_idx = MagicMock(return_value=tab)

    assert tabs.activate_tab(None) is None
    assert tabs.activate_tab(tab) is tab
    tabs.switch_tab_by_idx.assert_called_once_with(2, 1)

    tabs.switch_tab_by_idx.reset_mock()
    assert tabs.activate_tab(tab, sync_context=False) is tab
    tabs.switch_tab_by_idx.assert_called_once_with(2, 1)
    assert tabs.is_context_sync_suppressed() is False


def test_current_helpers_use_state_and_selected_tab(tabs_env):
    tabs = tabs_env.tabs
    tab = tabs_env.make_tab(pid=12, idx=3, column_idx=1, type=Tab.TAB_NOTEPAD)
    tabs_env.install(tab)
    tabs._state.activate(1, 3, 12)

    assert tabs.get_current_column_idx() == 1
    assert tabs.get_current_idx() == 3
    assert tabs.get_current_idx(1) == 3
    assert tabs.get_current_tab() is tab
    assert tabs.get_current_type() == Tab.TAB_NOTEPAD
    assert tabs.get_current_pid() == 12

    tabs_env.core_tabs.get_tab_by_pid.side_effect = lambda _pid: None
    assert tabs.get_current_idx(1) == 3


def test_index_lookup_helpers_delegate_with_explicit_or_active_column(tabs_env):
    tabs = tabs_env.tabs
    tab = tabs_env.make_tab(type=Tab.TAB_FILES)
    tabs_env.core_tabs.get_tab_by_index.side_effect = None
    tabs_env.core_tabs.get_tab_by_index.return_value = tab
    tabs_env.core_tabs.get_min_idx_by_type.return_value = 4
    tabs_env.core_tabs.get_prev_idx_from.return_value = (2, True)
    tabs_env.core_tabs.get_next_idx_from.return_value = (6, True)
    tabs.set_current_column_idx(1)

    assert tabs.get_type_by_idx(3) == Tab.TAB_FILES
    assert tabs.get_first_idx_by_type(Tab.TAB_FILES) == 4
    assert tabs.get_prev_idx_from(3) == (2, True)
    assert tabs.get_next_idx_from(3) == (6, True)
    tabs_env.core_tabs.get_tab_by_index.assert_called_with(3, 1)
    tabs_env.core_tabs.get_min_idx_by_type.assert_called_with(Tab.TAB_FILES, 1)
    tabs_env.core_tabs.get_prev_idx_from.assert_called_with(3, 1)
    tabs_env.core_tabs.get_next_idx_from.assert_called_with(3, 1)


def test_get_after_close_idx_prefers_previous_then_next(tabs_env):
    tabs = tabs_env.tabs
    tabs.get_prev_idx_from = MagicMock(return_value=(2, True))
    tabs.get_next_idx_from = MagicMock(return_value=(4, True))
    assert tabs.get_after_close_idx(3, 1) == 2
    tabs.get_next_idx_from.assert_not_called()

    tabs.get_prev_idx_from.return_value = (0, False)
    assert tabs.get_after_close_idx(3, 1) == 4
    tabs.get_next_idx_from.return_value = (0, False)
    assert tabs.get_after_close_idx(3, 1) is None


def test_close_delegates_to_event_handler(tabs_env):
    tabs_env.tabs.handler.on_tab_closed = MagicMock()
    tabs_env.tabs.close(3, 1)
    tabs_env.tabs.handler.on_tab_closed.assert_called_once_with(3, 1)


def test_close_all_requests_confirmation_when_not_forced(tabs_env):
    tabs = tabs_env.tabs
    with patch("pygpt_net.controller.tabs.operations.trans", return_value="confirm"):
        tabs.close_all(Tab.TAB_NOTEPAD, 1, force=False)
    tabs_env.window.ui.dialogs.confirm.assert_called_once_with(
        type="tab.close_all",
        id={"type": Tab.TAB_NOTEPAD, "column_idx": 1},
        msg="confirm",
    )
    tabs_env.core_tabs.remove_all_by_type.assert_not_called()


def test_close_all_force_updates_active_column_and_notifies(tabs_env):
    tabs = tabs_env.tabs
    tabs.is_split_screen_enabled = MagicMock(return_value=True)
    tabs.set_current_column_idx(1)
    tabs.handler.on_column_changed = MagicMock()
    tabs.handler.on_changed = MagicMock()
    tabs.debug = MagicMock()

    tabs.close_all(Tab.TAB_NOTEPAD, 1, force=True)

    tabs_env.core_tabs.remove_all_by_type.assert_called_once_with(Tab.TAB_NOTEPAD, 1)
    tabs.handler.on_column_changed.assert_called_once_with(1)
    tabs.handler.on_changed.assert_called_once_with()
    tabs.debug.assert_called_once_with()


def test_close_all_force_remembers_inactive_column_without_focus_change(tabs_env):
    tabs = tabs_env.tabs
    remaining = tabs_env.make_tab(pid=21, idx=0, column_idx=1, type=Tab.TAB_CHAT)
    tabs_env.install(remaining)
    tabs_env.widgets[1]._current = 0
    tabs.is_split_screen_enabled = MagicMock(return_value=True)
    tabs.set_current_column_idx(0)
    tabs.handler.on_column_changed = MagicMock()
    tabs.handler.on_changed = MagicMock()

    tabs.close_all(Tab.TAB_NOTEPAD, 1, force=True)

    tabs.handler.on_column_changed.assert_not_called()
    assert tabs._state.current_pid(1) == 21


def test_next_prev_tab_wrap_in_active_column(tabs_env):
    tabs = tabs_env.tabs
    widget = tabs_env.widgets[0]
    widget.set_count(3)
    widget._current = 2
    tabs.switch_tab_by_idx = MagicMock()
    tabs.next_tab()
    tabs.switch_tab_by_idx.assert_called_once_with(0, 0)

    tabs.switch_tab_by_idx.reset_mock()
    widget._current = 0
    tabs.prev_tab()
    tabs.switch_tab_by_idx.assert_called_once_with(2, 0)


def test_switch_tab_open_by_type_and_missing_type(tabs_env):
    tabs = tabs_env.tabs
    tab = tabs_env.make_tab(pid=31, idx=1, column_idx=0, type=Tab.TAB_NOTEPAD)
    tabs.activate_tab = MagicMock()
    tabs_env.core_tabs.get_first_by_type.side_effect = None
    tabs_env.core_tabs.get_first_by_type.return_value = tab

    tabs.switch_tab(Tab.TAB_NOTEPAD)
    tabs.activate_tab.assert_called_once_with(tab)

    tabs.activate_tab.reset_mock()
    tabs_env.core_tabs.get_first_by_type.return_value = None
    tabs.open_by_type(Tab.TAB_FILES)
    tabs.activate_tab.assert_not_called()


def test_switch_tab_by_idx_validates_and_updates_state_before_widget(tabs_env):
    tabs = tabs_env.tabs
    tab0 = tabs_env.make_tab(pid=40, idx=0, column_idx=0)
    tab1 = tabs_env.make_tab(pid=41, idx=1, column_idx=0)
    tabs_env.install(tab0, tab1)
    widget = tabs_env.widgets[0]
    widget._current = 0
    tabs._state.activate(0, 0, 40)

    result = tabs.switch_tab_by_idx(1, 0)

    assert result is tab1
    assert tabs._state.current_pid(0) == 41
    assert tabs._selection_previous_target.pid == 40
    widget.setCurrentIndex.assert_called_once_with(1)

    assert tabs.switch_tab_by_idx(-1, 0) is None
    assert tabs.switch_tab_by_idx(99, 0) is None


def test_switch_tab_by_idx_calls_handler_when_widget_already_selected(tabs_env):
    tabs = tabs_env.tabs
    tab = tabs_env.make_tab(pid=42, idx=0, column_idx=0)
    tabs_env.install(tab)
    tabs_env.widgets[0]._current = 0
    tabs.handler.on_tab_changed = MagicMock()

    assert tabs.switch_tab_by_idx(0, 0) is tab
    tabs.handler.on_tab_changed.assert_called_once_with(0, 0)


def test_new_tab_and_open_chat_context_pass_explicit_creation_flags(tabs_env):
    tabs = tabs_env.tabs
    tabs_env.core_tabs.get_max_idx_by_column.return_value = 4
    tabs.append = MagicMock(return_value="new")

    assert tabs.new_tab(1) == "new"
    tabs.append.assert_called_once_with(
        type=Tab.TAB_CHAT,
        tool_id=None,
        idx=4,
        column_idx=1,
        activate=True,
        create_chat_context=True,
    )

    tabs.append.reset_mock()
    assert tabs.open_chat_context(77, 1) == "new"
    tabs.append.assert_called_once_with(
        type=Tab.TAB_CHAT,
        idx=4,
        column_idx=1,
        activate=True,
        create_chat_context=False,
        data_id=77,
    )

    tabs.append.reset_mock()
    tabs.open_chat_context(88, 0, after_idx=2)
    assert tabs.append.call_args.kwargs["idx"] == 2


def test_restore_data_restores_persisted_columns_and_publishes_secondary_first(tabs_env):
    tabs = tabs_env.tabs
    left = tabs_env.make_tab(pid=50, idx=1, column_idx=0)
    right = tabs_env.make_tab(pid=51, idx=0, column_idx=1)
    filler = tabs_env.make_tab(pid=52, idx=0, column_idx=0)
    tabs_env.install(filler, left, right)
    tabs_env.config_values["layout.split"] = True
    tabs_env.config_values["tabs.opened"] = {"0": 1, "1": 0}
    tabs.sync_chat_titles = MagicMock(return_value=True)
    tabs.handler.on_tab_changed = MagicMock()
    tabs.debug = MagicMock()

    tabs.restore_data()

    tabs_env.widgets[0].setCurrentIndex.assert_called_with(1)
    tabs_env.widgets[1].setCurrentIndex.assert_called_with(0)
    assert tabs.handler.on_tab_changed.call_args_list == [call(0, 1), call(1, 0)]
    tabs_env.core_tabs.save.assert_called_once_with()
    assert tabs.is_context_sync_suppressed() is False


def test_restore_data_without_saved_selection_uses_first_left_tab(tabs_env):
    tabs = tabs_env.tabs
    tab = tabs_env.make_tab(pid=53, idx=0, column_idx=0)
    tabs_env.install(tab)
    tabs_env.config_values["tabs.opened"] = []
    tabs.sync_chat_titles = MagicMock(return_value=False)
    tabs.handler.on_tab_changed = MagicMock()

    tabs.restore_data()

    tabs_env.widgets[0].setCurrentIndex.assert_called_with(0)
    tabs.handler.on_tab_changed.assert_called_once_with(0, 0)
    tabs_env.core_tabs.save.assert_not_called()


def test_move_tab_is_pid_based_and_reactivates_moved_tab(tabs_env):
    tabs = tabs_env.tabs
    original = tabs_env.make_tab(pid=60, idx=0, column_idx=0)
    moved = tabs_env.make_tab(pid=60, idx=1, column_idx=1)
    tabs_env.install(original)
    tabs_env.core_tabs.get_tab_by_index.side_effect = lambda idx, col: original if (idx, col) == (0, 0) else None
    tabs_env.core_tabs.get_tab_by_pid.side_effect = lambda pid: moved if pid == 60 else None
    tabs.activate_tab = MagicMock()
    tabs.debug = MagicMock()
    tabs_env.widgets[0].set_count(0)

    assert tabs.move_tab(0, 0, 1, new_idx=1) is moved

    tabs_env.core_tabs.move_tab.assert_called_once_with(original, 1, new_idx=1)
    tabs.activate_tab.assert_called_once_with(moved)
    assert tabs.is_locked() is False
    tabs.debug.assert_called_once_with()


def test_move_tab_returns_none_for_missing_source(tabs_env):
    tabs_env.core_tabs.get_tab_by_index.side_effect = lambda *_: None
    assert tabs_env.tabs.move_tab(9, 0, 1) is None
    tabs_env.core_tabs.move_tab.assert_not_called()


def test_current_type_and_tool_scan_each_column(tabs_env):
    tabs = tabs_env.tabs
    chat = tabs_env.make_tab(pid=70, idx=0, column_idx=0, type=Tab.TAB_CHAT)
    tool = tabs_env.make_tab(pid=71, idx=0, column_idx=1, type=Tab.TAB_TOOL, tool_id="x")
    tabs_env.install(chat, tool)
    tabs._state.remember(0, 0, 70)
    tabs._state.remember(1, 0, 71)

    assert tabs.is_current_by_type(Tab.TAB_TOOL) is True
    assert tabs.is_current_by_type(Tab.TAB_FILES) is False
    assert tabs.is_current_tool("x") is True
    assert tabs.is_current_tool("missing") is False


def test_get_current_by_column_prefers_pid_state_then_imports_widget_selection(tabs_env):
    tabs = tabs_env.tabs
    tab = tabs_env.make_tab(pid=80, idx=0, column_idx=0)
    tabs_env.install(tab)
    tabs._state.remember(0, 0, 80)
    assert tabs.get_current_by_column(0) is tab

    tabs._state.clear_column_pid(0)
    tabs_env.widgets[0]._current = 0
    assert tabs.get_current_by_column(0) is tab
    assert tabs._state.current_pid(0) == 80

    tabs_env.widgets[1]._current = -1
    assert tabs.get_current_by_column(1) is None


def test_tool_queries_sort_and_activate_first_instance(tabs_env):
    tabs = tabs_env.tabs
    t3 = tabs_env.make_tab(pid=3, idx=1, column_idx=0, type=Tab.TAB_TOOL, tool_id="x")
    t1 = tabs_env.make_tab(pid=1, idx=0, column_idx=1, type=Tab.TAB_TOOL, tool_id="x")
    other = tabs_env.make_tab(pid=2, idx=0, column_idx=0, type=Tab.TAB_TOOL, tool_id="y")
    tabs_env.install(t3, t1, other)

    assert tabs.get_tabs_by_tool("x") == [t1, t3]
    assert tabs.is_tool("x") is True
    assert tabs.is_tool("none") is False
    assert tabs.get_first_tab_by_tool("x") is t1

    tabs.activate_tab = MagicMock()
    tabs.switch_to_first_tab_by_tool("x")
    tabs.activate_tab.assert_called_once_with(t1)


def test_get_tool_column_only_reports_selected_tool(tabs_env):
    tabs = tabs_env.tabs
    tool = tabs_env.make_tab(pid=90, idx=0, column_idx=1, type=Tab.TAB_TOOL, tool_id="x")
    tabs_env.install(tool)
    tabs._state.remember(1, 0, 90)
    assert tabs.get_tool_column("x") == 1
    assert tabs.get_tool_column("missing") is None
