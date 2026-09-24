from pygpt_net.controller.tabs.state import TabState, TabTarget


def test_state_lock_unlock_and_flags():
    state = TabState()
    assert state.is_locked() is False
    state.lock()
    assert state.is_locked() is True
    state.unlock()
    assert state.is_locked() is False

    assert state.is_initialized() is False
    state.mark_initialized()
    assert state.is_initialized() is True
    state.mark_uninitialized()
    assert state.is_initialized() is False

    assert state.is_widget_loading() is False
    state.begin_widget_loading()
    assert state.is_widget_loading() is True
    state.end_widget_loading()
    assert state.is_widget_loading() is False


def test_state_active_column_and_pending_focus():
    state = TabState()
    state.set_active_column(3)
    assert state.get_active_column() == 3
    assert state.current_idx(3) == 0

    state.set_pending_focus_column("2")
    assert state.get_pending_focus_column() == 2
    state.clear_pending_focus_column()
    assert state.get_pending_focus_column() is None
    state.set_pending_focus_column(None)
    assert state.get_pending_focus_column() is None


def test_state_activate_remember_current_and_target():
    state = TabState()
    state.activate(1, 4, 42)
    assert state.get_active_column() == 1
    assert state.current_idx() == 4
    assert state.current_pid() == 42
    assert state.target() == TabTarget(pid=42, column_idx=1, idx=4)

    state.remember(0, 2, 10)
    assert state.get_active_column() == 1
    assert state.current_idx(0) == 2
    assert state.current_pid(0) == 10
    assert state.target(0) == TabTarget(pid=10, column_idx=0, idx=2)


def test_state_activate_or_remember_without_pid_clears_column_pid():
    state = TabState()
    state.remember(0, 1, 10)
    state.remember(0, 2, None)
    assert state.current_pid(0) is None
    assert state.target(0) is None

    state.activate(1, 3, 20)
    state.activate(1, 4, None)
    assert state.current_pid(1) is None
    assert state.target(1) is None


def test_state_clear_column_pid_drop_pid_and_reset():
    state = TabState()
    state.remember(0, 1, 7)
    state.remember(1, 2, 7)
    state.clear_column_pid(0)
    assert state.current_pid(0) is None
    assert state.current_pid(1) == 7

    state.drop_pid(7)
    assert state.current_pid(1) is None

    state.activate(1, 9, 99)
    state.set_pending_focus_column(1)
    state.lock()
    state.reset()
    assert state.get_active_column() == 0
    assert state.current_idx(0) == 0
    assert state.current_idx(1) == 0
    assert state.pid_by_column == {}
    assert state.get_pending_focus_column() is None
    assert state.is_locked() is False
