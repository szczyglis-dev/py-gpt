from unittest.mock import MagicMock


def test_tabs_state_wrappers_cover_lock_init_loading_and_column(tabs_env):
    tabs = tabs_env.tabs

    tabs.lock(); assert tabs.is_locked() is True
    tabs.unlock(); assert tabs.is_locked() is False
    tabs.mark_initialized(); assert tabs.is_initialized() is True
    tabs.mark_uninitialized(); assert tabs.is_initialized() is False
    tabs.begin_widget_loading(); assert tabs.is_widget_loading() is True
    tabs.end_widget_loading(); assert tabs.is_widget_loading() is False

    tabs.set_current_column_idx(1)
    assert tabs.get_current_column_idx() == 1
    tabs.set_pending_focus_column(1)
    assert tabs.get_pending_focus_column() == 1
    tabs.clear_pending_focus_column()
    assert tabs.get_pending_focus_column() is None

    tabs._state.remember(0, 0, 10)
    tabs._state.remember(1, 0, 20)
    assert tabs.get_column_pids() == {0: 10, 1: 20}
    copy = tabs.get_column_pids()
    copy[0] = 99
    assert tabs.get_column_pids()[0] == 10


def test_suspend_context_sync_is_nestable_and_exception_safe(tabs_env):
    tabs = tabs_env.tabs
    assert tabs.is_context_sync_suppressed() is False
    try:
        with tabs.suspend_context_sync():
            assert tabs.is_context_sync_suppressed() is True
            with tabs.suspend_context_sync():
                assert tabs._context_sync_suppressed == 2
            assert tabs._context_sync_suppressed == 1
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    assert tabs.is_context_sync_suppressed() is False


def test_suspend_tab_events_is_nestable_and_exception_safe(tabs_env):
    tabs = tabs_env.tabs
    assert tabs.are_tab_events_suppressed() is False
    try:
        with tabs.suspend_tab_events():
            assert tabs.are_tab_events_suppressed() is True
            with tabs.suspend_tab_events():
                assert tabs._tab_events_suppressed == 2
            assert tabs._tab_events_suppressed == 1
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    assert tabs.are_tab_events_suppressed() is False


def test_event_api_delegates_to_handler(tabs_env):
    tabs = tabs_env.tabs
    tabs.handler = MagicMock()
    tabs.get_current_column_idx = MagicMock(return_value=1)

    assert tabs.on_tab_changed(2, 1) is tabs.handler.on_tab_changed.return_value
    assert tabs.on_changed() is tabs.handler.on_changed.return_value
    assert tabs.on_column_changed() is tabs.handler.on_column_changed.return_value
    assert tabs.on_tab_clicked(3, 1) is tabs.handler.on_tab_clicked.return_value
    assert tabs.on_column_focus(1) is tabs.handler.on_column_focus.return_value
    assert tabs._apply_column_focus() is tabs.handler._apply_column_focus.return_value
    assert tabs.on_tab_dbl_clicked(4, 1) is tabs.handler.on_tab_dbl_clicked.return_value
    assert tabs.on_tab_closed(5, 1) is tabs.handler.on_tab_closed.return_value
    assert tabs.on_tab_moved(6, 1) is tabs.handler.on_tab_moved.return_value

    tabs.handler.on_tab_changed.assert_called_once_with(2, 1)
    tabs.handler.on_changed.assert_called_once_with()
    tabs.handler.on_column_changed.assert_called_once_with(1)
    tabs.handler.on_tab_clicked.assert_called_once_with(3, 1)
    tabs.handler.on_column_focus.assert_called_once_with(1)
    tabs.handler._apply_column_focus.assert_called_once_with()
    tabs.handler.on_tab_dbl_clicked.assert_called_once_with(4, 1)
    tabs.handler.on_tab_closed.assert_called_once_with(5, 1)
    tabs.handler.on_tab_moved.assert_called_once_with(6, 1)


def test_tabs_init_constructs_private_state_and_handler(tabs_env):
    tabs = tabs_env.tabs
    assert tabs.window is tabs_env.window
    assert tabs._state is not None
    assert tabs.handler.tabs is tabs
    assert tabs._focus_sync_scheduled is False
    assert tabs._context_sync_suppressed == 0
    assert tabs._tab_events_suppressed == 0
