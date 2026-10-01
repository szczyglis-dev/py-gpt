from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

import pygpt_net.controller.tabs.handler as handler_mod
from pygpt_net.core.tabs.tab import Tab


def test_handler_init_window_and_resolve(tabs_env):
    handler = tabs_env.tabs.handler
    assert handler.tabs is tabs_env.tabs
    assert handler.window is tabs_env.window
    assert handler._resolve(None, 0) is None
    assert handler._resolve(-1, 0) is None

    tab = tabs_env.make_tab(pid=1, idx=0, column_idx=0)
    tabs_env.install(tab)
    assert handler._resolve(0, 0) is tab


def test_select_state_tracks_previous_target_and_activates_new_tab(tabs_env):
    tabs = tabs_env.tabs
    handler = tabs.handler
    old = tabs_env.make_tab(pid=1, idx=0, column_idx=0)
    new = tabs_env.make_tab(pid=2, idx=0, column_idx=1)
    tabs._state.activate(0, 0, old.pid)

    handler._select_state(new, 0, 1)

    assert tabs._selection_previous_target.pid == old.pid
    assert tabs.get_current_column_idx() == 1
    assert tabs._state.current_pid(1) == new.pid


def test_on_created_binds_activates_creates_context_and_debugs(tabs_env):
    tabs = tabs_env.tabs
    handler = tabs.handler
    tab = tabs_env.make_tab(pid=3, idx=0, column_idx=0, data_id=None)
    tabs.bind_chat = MagicMock()
    tabs.activate_tab = MagicMock()
    tabs.create_chat_context = MagicMock()
    tabs.debug = MagicMock()

    assert handler.on_created(tab, activate=True, create_chat_context=False, data_id=55) is tab
    tabs.bind_chat.assert_called_once_with(tab, 55)
    tabs.activate_tab.assert_called_once_with(tab, sync_context=False)
    tabs.create_chat_context.assert_not_called()
    tabs.debug.assert_called_once_with()

    tabs.bind_chat.reset_mock(); tabs.activate_tab.reset_mock(); tabs.debug.reset_mock()
    tab.data_id = None
    handler.on_created(tab, activate=False, create_chat_context=True, data_id=None)
    tabs.activate_tab.assert_not_called()
    tabs.create_chat_context.assert_called_once_with(tab)

    assert handler.on_created(None) is None


def test_on_deleted_reselects_active_column_or_remembers_inactive(tabs_env):
    tabs = tabs_env.tabs
    handler = tabs.handler
    remaining = tabs_env.make_tab(pid=5, idx=0, column_idx=0)
    tabs_env.install(remaining)
    tabs_env.widgets[0]._current = 0
    tabs.switch_tab_by_idx = MagicMock()
    handler.on_changed = MagicMock()
    tabs.update_current = MagicMock()
    tabs.debug = MagicMock()
    tabs._state.remember(0, 1, 99)

    handler.on_deleted(99, 0, 0, activate_column=True)
    tabs.switch_tab_by_idx.assert_called_once_with(0, 0)
    handler.on_changed.assert_called_once_with()
    tabs.update_current.assert_called_once_with()
    tabs.debug.assert_called_once_with()

    tabs.switch_tab_by_idx.reset_mock(); handler.on_changed.reset_mock(); tabs.update_current.reset_mock()
    handler.on_deleted(123, 0, 0, activate_column=False)
    tabs.switch_tab_by_idx.assert_not_called()
    assert tabs._state.current_pid(0) == remaining.pid


def test_on_deleted_empty_secondary_column_schedules_focus_back_to_primary(tabs_env):
    tabs = tabs_env.tabs
    handler = tabs.handler
    tabs_env.widgets[1].set_count(0)
    handler.on_column_focus = MagicMock()
    handler.on_changed = MagicMock()
    tabs.update_current = MagicMock()
    tabs.debug = MagicMock()

    handler.on_deleted(10, 1, None, activate_column=True)

    assert tabs._state.current_pid(1) is None
    handler.on_column_focus.assert_called_once_with(0)


def test_on_tab_changed_ignores_invalid_lifecycle_and_hidden_secondary(tabs_env):
    tabs = tabs_env.tabs
    handler = tabs.handler
    handler._resolve = MagicMock()

    handler.on_tab_changed(-1, 0)
    tabs.mark_initialized()
    tabs.begin_widget_loading(); handler.on_tab_changed(0, 0); tabs.end_widget_loading()
    with tabs.suspend_tab_events():
        handler.on_tab_changed(0, 0)
    handler.on_tab_changed(0, 1)

    handler._resolve.assert_not_called()


def test_on_tab_changed_chat_loads_context_and_updates_ui(tabs_env, monkeypatch):
    tabs, window = tabs_env.tabs, tabs_env.window
    handler = tabs.handler
    tab = tabs_env.make_tab(pid=11, idx=0, column_idx=0, type=Tab.TAB_CHAT, data_id=77)
    tabs_env.install(tab)
    tabs.mark_initialized()
    meta = SimpleNamespace(id=77)
    window.core.ctx.get_meta_by_id.return_value = meta
    window.controller.chat.render.get_pid_data.return_value = None
    tabs.update_current = MagicMock()
    tabs._sync_chat_input_width = MagicMock()
    tabs.debug = MagicMock()
    handler.on_changed = MagicMock()
    single_shot = MagicMock()
    monkeypatch.setattr(handler_mod.QTimer, "singleShot", single_shot)

    handler.on_tab_changed(0, 0)

    assert tabs._state.current_pid(0) == 11
    window.controller.ui.mode.update.assert_called_once_with()
    window.controller.ui.vision.update.assert_called_once_with()
    window.core.ctx.output.prepare_meta.assert_called_once_with(tab)
    window.controller.ctx.load.assert_called_once_with(77, tab_pid=11)
    assert single_shot.call_count == 2
    window.dispatch.assert_called_once()
    handler.on_changed.assert_called_once_with(tab)
    window.controller.ui.update.assert_called_once_with()
    tabs.update_current.assert_called_once_with()
    tabs._sync_chat_input_width.assert_called_once_with()


def test_on_tab_changed_chat_selects_list_when_renderer_loaded(tabs_env, monkeypatch):
    tabs, window = tabs_env.tabs, tabs_env.window
    handler = tabs.handler
    tab = tabs_env.make_tab(pid=12, idx=0, column_idx=0, type=Tab.TAB_CHAT, data_id=88)
    tabs_env.install(tab)
    tabs.mark_initialized()
    window.core.ctx.get_meta_by_id.return_value = SimpleNamespace(id=88)
    window.controller.chat.render.get_pid_data.return_value = SimpleNamespace(loaded=True)
    monkeypatch.setattr(handler_mod.QTimer, "singleShot", MagicMock())

    handler.on_tab_changed(0, 0)

    window.controller.ctx.select_on_list_only.assert_called_once_with(88)
    window.controller.ctx.load.assert_not_called()


def test_on_tab_changed_dispatches_type_specific_actions(tabs_env, monkeypatch):
    tabs, window = tabs_env.tabs, tabs_env.window
    handler = tabs.handler
    tabs.mark_initialized()
    monkeypatch.setattr(handler_mod.QTimer, "singleShot", MagicMock())

    note = tabs_env.make_tab(pid=20, idx=0, column_idx=0, type=Tab.TAB_NOTEPAD)
    tabs_env.install(note)
    handler.on_tab_changed(0, 0)
    assert window.controller.notepad.opened_once is True
    window.controller.notepad.on_open.assert_called_with(0, 0)

    painter = tabs_env.make_tab(pid=21, idx=0, column_idx=0, type=Tab.TAB_TOOL_PAINTER)
    tabs_env.install(painter)
    window.core.config.get.side_effect = lambda key, default=None: True if key == "vision.capture.enabled" else tabs_env.config_values.get(key, default)
    handler.on_tab_changed(0, 0)
    window.controller.camera.enable_capture.assert_called_once_with()

    calendar = tabs_env.make_tab(pid=22, idx=0, column_idx=0, type=Tab.TAB_TOOL_CALENDAR)
    tabs_env.install(calendar)
    handler.on_tab_changed(0, 0)
    window.controller.calendar.update.assert_called_once_with()
    window.controller.calendar.update_ctx_counters.assert_called_once_with()


def test_on_changed_uses_explicit_or_current_tab(tabs_env):
    tabs, window = tabs_env.tabs, tabs_env.window
    handler = tabs.handler
    tab = tabs_env.make_tab(pid=30)
    tabs.debug = MagicMock()
    handler.on_changed(tab)
    window.controller.audio.on_tab_changed.assert_called_once_with(tab)
    tabs.debug.assert_called_once_with()

    window.controller.audio.on_tab_changed.reset_mock()
    tabs.get_current_tab = MagicMock(return_value=None)
    handler.on_changed()
    window.controller.audio.on_tab_changed.assert_not_called()


def test_on_column_changed_forces_primary_when_split_disabled_and_updates_state(tabs_env):
    tabs, window = tabs_env.tabs, tabs_env.window
    handler = tabs.handler
    tab = tabs_env.make_tab(pid=40, idx=0, column_idx=0, type=Tab.TAB_NOTEPAD)
    tabs_env.install(tab)
    tabs_env.widgets[0]._current = 0
    tabs.is_split_screen_enabled = MagicMock(return_value=False)
    tabs.update_current = MagicMock()
    tabs._sync_chat_input_width = MagicMock()
    tabs.debug = MagicMock()

    handler.on_column_changed(1)

    tabs_env.widgets[0].set_active.assert_called_with(True)
    tabs_env.widgets[1].set_active.assert_called_with(False)
    assert tabs.get_current_column_idx() == 0
    assert tabs._state.current_pid(0) == 40
    window.controller.ui.update.assert_called_once_with()
    tabs.update_current.assert_called_once_with()


def test_on_column_changed_secondary_chat_loads_no_fresh_once(tabs_env):
    tabs, window = tabs_env.tabs, tabs_env.window
    handler = tabs.handler
    tab = tabs_env.make_tab(pid=41, idx=0, column_idx=1, type=Tab.TAB_CHAT, data_id=101)
    tabs_env.install(tab)
    tabs_env.widgets[1]._current = 0
    tabs.is_split_screen_enabled = MagicMock(return_value=True)
    window.core.ctx.get_current.return_value = 999
    window.core.ctx.get_meta_by_id.return_value = SimpleNamespace(id=101)
    window.controller.chat.render.get_pid_data.return_value = None

    handler.on_column_changed(1)

    window.controller.ctx.load.assert_called_once_with(101, no_fresh=True, tab_pid=41)
    assert tab.loaded is True


def test_on_tab_clicked_selects_widget_or_resyncs_same_selection(tabs_env):
    tabs = tabs_env.tabs
    handler = tabs.handler
    tab = tabs_env.make_tab(pid=50, idx=1, column_idx=0)
    tabs_env.install(tab)
    tabs_env.widgets[0].set_count(2)
    tabs_env.widgets[0]._current = 0
    handler.on_column_changed = MagicMock()
    handler.on_changed = MagicMock()

    handler.on_tab_clicked(1, 0)
    tabs_env.widgets[0].setCurrentIndex.assert_called_once_with(1)
    handler.on_column_changed.assert_not_called()

    tabs_env.widgets[0].setCurrentIndex.reset_mock()
    tabs_env.widgets[0]._current = 1
    handler.on_tab_clicked(1, 0)
    handler.on_column_changed.assert_called_once_with(0)
    handler.on_changed.assert_called_once_with(tab)


def test_on_column_focus_coalesces_pending_focus(monkeypatch, tabs_env):
    tabs = tabs_env.tabs
    handler = tabs.handler
    tabs.is_split_screen_enabled = MagicMock(return_value=True)
    tabs.set_current_column_idx(0)
    single_shot = MagicMock()
    monkeypatch.setattr(handler_mod.QTimer, "singleShot", single_shot)

    handler.on_column_focus(1)
    handler.on_column_focus(1)

    assert tabs.get_pending_focus_column() == 1
    assert tabs._focus_sync_scheduled is True
    single_shot.assert_called_once_with(0, handler._apply_column_focus)

    tabs.set_current_column_idx(1)
    handler.on_column_focus(1)
    assert tabs.get_pending_focus_column() is None


def test_apply_column_focus_activates_target_and_restores_widget_focus(monkeypatch, tabs_env):
    tabs = tabs_env.tabs
    handler = tabs.handler
    tab = tabs_env.make_tab(pid=60, idx=0, column_idx=1)
    tabs_env.install(tab)
    tabs_env.widgets[1]._current = 0
    tabs.is_split_screen_enabled = MagicMock(return_value=True)
    tabs.set_current_column_idx(0)
    tabs.set_pending_focus_column(1)
    handler.on_column_changed = MagicMock()
    handler.on_changed = MagicMock()
    focused = MagicMock()
    focused.isVisible.return_value = True
    focused.hasFocus.return_value = False
    app = MagicMock(); app.focusWidget.return_value = focused
    monkeypatch.setattr(handler_mod.QGuiApplication, "instance", MagicMock(return_value=app))

    handler._apply_column_focus()

    assert tabs.get_current_column_idx() == 1
    assert tabs._state.current_pid(1) == 60
    handler.on_column_changed.assert_called_once_with(1)
    handler.on_changed.assert_called_once_with(tab)
    focused.setFocus.assert_called_once_with(handler_mod.Qt.OtherFocusReason)
    assert tabs.get_pending_focus_column() is None
    assert tabs._focus_sync_scheduled is False


def test_on_tab_dbl_clicked_delegates_to_change(tabs_env):
    handler = tabs_env.tabs.handler
    handler.on_tab_changed = MagicMock()
    handler.on_tab_dbl_clicked(2, 1)
    handler.on_tab_changed.assert_called_once_with(2, 1)


def test_on_tab_closed_removes_exact_tab_and_computes_followup(tabs_env):
    tabs = tabs_env.tabs
    handler = tabs.handler
    first = tabs_env.make_tab(pid=70, idx=0, column_idx=0)
    second = tabs_env.make_tab(pid=71, idx=1, column_idx=0)
    tabs_env.install(first, second)
    tabs_env.widgets[0]._current = 1
    tabs._state.activate(0, 1, 71)
    handler.on_deleted = MagicMock()

    handler.on_tab_closed(1, 0)

    tabs_env.core_tabs.remove_tab_by_idx.assert_called_once_with(1, 0)
    handler.on_deleted.assert_called_once_with(71, 0, 0, activate_column=True)
    assert tabs.are_tab_events_suppressed() is False


def test_on_tab_closed_ignores_locked_or_missing_tab(tabs_env):
    tabs = tabs_env.tabs
    handler = tabs.handler
    tabs.lock()
    handler.on_tab_closed(0, 0)
    tabs_env.core_tabs.remove_tab_by_idx.assert_not_called()
    tabs.unlock()
    handler._resolve = MagicMock(return_value=None)
    handler.on_tab_closed(0, 0)
    tabs_env.core_tabs.remove_tab_by_idx.assert_not_called()


def test_on_tab_moved_updates_registry_selection_and_current(tabs_env):
    tabs = tabs_env.tabs
    handler = tabs.handler
    tab = tabs_env.make_tab(pid=80, idx=0, column_idx=0)
    tabs_env.install(tab)
    tabs_env.widgets[0]._current = 0
    tabs.update_current = MagicMock()
    tabs.debug = MagicMock()

    handler.on_tab_moved(0, 0)

    tabs_env.core_tabs.update_column.assert_called_once_with(0)
    assert tabs._state.current_pid(0) == 80
    tabs.update_current.assert_called_once_with()
    tabs.debug.assert_called_once_with()

    tabs_env.core_tabs.update_column.reset_mock()
    tabs.lock(); handler.on_tab_moved(0, 0)
    tabs_env.core_tabs.update_column.assert_not_called()
