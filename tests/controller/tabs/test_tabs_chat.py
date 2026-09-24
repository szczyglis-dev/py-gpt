from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.core.tabs.tab import Tab


def test_request_active_handles_normal_and_exception(tabs_env):
    tabs = tabs_env.tabs
    tabs_env.output.has_request.return_value = True
    assert tabs._request_active() is True
    tabs_env.output.has_request.side_effect = RuntimeError("x")
    assert tabs._request_active() is False


def test_get_effective_current_pid_prefers_pending_focus_column(tabs_env):
    tabs = tabs_env.tabs
    left = tabs_env.make_tab(pid=1, idx=0, column_idx=0)
    right = tabs_env.make_tab(pid=2, idx=0, column_idx=1)
    tabs_env.install(left, right)
    tabs._state.remember(0, 0, 1)
    tabs._state.remember(1, 0, 2)
    tabs.set_current_column_idx(0)

    assert tabs.get_effective_current_pid() == 1
    tabs.set_pending_focus_column(1)
    assert tabs.get_effective_current_pid() == 2


def test_get_preferred_chat_tab_uses_requested_visible_column_then_fallback(tabs_env):
    tabs = tabs_env.tabs
    tool = tabs_env.make_tab(pid=3, idx=0, column_idx=0, type=Tab.TAB_TOOL)
    chat = tabs_env.make_tab(pid=4, idx=0, column_idx=1, type=Tab.TAB_CHAT)
    tabs_env.install(tool, chat)
    tabs._state.remember(0, 0, 3)
    tabs._state.remember(1, 0, 4)
    tabs.is_split_screen_enabled = MagicMock(return_value=True)

    assert tabs.get_preferred_chat_tab(1) is chat
    assert tabs.get_preferred_chat_tab(0) is chat

    tabs.is_split_screen_enabled.return_value = False
    tabs_env.core_tabs.get_first_by_type.side_effect = None
    tabs_env.core_tabs.get_first_by_type.return_value = chat
    assert tabs.get_preferred_chat_tab(0) is chat


def test_bind_chat_rejects_non_chat_and_detaches_none_context(tabs_env):
    tabs = tabs_env.tabs
    tool = tabs_env.make_tab(pid=5, type=Tab.TAB_TOOL)
    assert tabs.bind_chat(None, 1) is None
    assert tabs.bind_chat(tool, 1) is None

    chat = tabs_env.make_tab(pid=6, data_id=1)
    assert tabs.bind_chat(chat, None) is chat
    assert chat.data_id is None
    assert chat.loaded is False
    tabs_env.output.remove_pid.assert_called_once_with(6)


def test_bind_chat_stores_existing_meta_and_updates_automatic_title(tabs_env):
    tabs = tabs_env.tabs
    chat = tabs_env.make_tab(pid=7)
    meta = SimpleNamespace(id=77, name="Context title")
    tabs_env.core_ctx.get_meta_by_id.return_value = meta
    tabs.update_title_by_tab = MagicMock()

    assert tabs.bind_chat(chat, 77) is chat

    assert chat.data_id == 77
    tabs_env.output.store.assert_called_once_with(meta, pid=7)
    tabs.update_title_by_tab.assert_called_once_with(chat, "Context title")


def test_bind_chat_prepares_missing_meta_without_destroying_binding(tabs_env):
    tabs = tabs_env.tabs
    chat = tabs_env.make_tab(pid=8)
    tabs_env.core_ctx.get_meta_by_id.return_value = None

    tabs.bind_chat(chat, 88)

    assert chat.data_id == 88
    tabs_env.output.prepare_meta.assert_called_once_with(chat)


def test_create_chat_context_is_atomic_and_pid_targeted(tabs_env):
    tabs, window = tabs_env.tabs, tabs_env.window
    chat = tabs_env.make_tab(pid=9, idx=0, column_idx=1)
    current = tabs_env.make_tab(pid=10, idx=0, column_idx=0)
    tabs.get_current_tab = MagicMock(return_value=current)
    tabs.activate_tab = MagicMock()
    meta = SimpleNamespace(id=123)
    window.controller.ctx.new.return_value = meta
    tabs.bind_chat = MagicMock()

    assert tabs.create_chat_context(chat) is meta
    tabs.activate_tab.assert_called_once_with(chat)
    window.controller.ctx.new.assert_called_once_with(tab_pid=9)
    tabs.bind_chat.assert_called_once_with(chat, 123)

    window.controller.ctx.new.reset_mock()
    chat.data_id = 123
    assert tabs.create_chat_context(chat) is None
    window.controller.ctx.new.assert_not_called()


def test_create_chat_context_is_blocked_during_request(tabs_env):
    tabs = tabs_env.tabs
    chat = tabs_env.make_tab(pid=11)
    tabs._request_active = MagicMock(return_value=True)
    assert tabs.create_chat_context(chat) is None
    tabs_env.window.controller.ctx.new.assert_not_called()


def test_sync_focused_chat_context_creates_missing_binding(tabs_env):
    tabs = tabs_env.tabs
    chat = tabs_env.make_tab(pid=12, data_id=None)
    tabs.get_current_tab = MagicMock(return_value=chat)
    tabs.create_chat_context = MagicMock()

    tabs.sync_focused_chat_context()
    tabs.create_chat_context.assert_called_once_with(chat)


def test_sync_focused_chat_context_loads_or_selects_existing_context(tabs_env):
    tabs, window = tabs_env.tabs, tabs_env.window
    chat = tabs_env.make_tab(pid=13, data_id=44)
    meta = SimpleNamespace(id=44)
    tabs.get_current_tab = MagicMock(return_value=chat)
    tabs_env.core_ctx.get_current.return_value = 99
    tabs_env.core_ctx.get_meta_by_id.return_value = meta
    window.controller.chat.render.get_pid_data.return_value = None

    tabs.sync_focused_chat_context()
    window.controller.ctx.load.assert_called_once_with(44, tab_pid=13)

    window.controller.ctx.load.reset_mock()
    window.controller.chat.render.get_pid_data.return_value = SimpleNamespace(loaded=True)
    tabs.sync_focused_chat_context()
    window.controller.ctx.select_on_list_only.assert_called_once_with(44)


def test_sync_focused_chat_context_noops_for_request_nonchat_current_or_missing_meta(tabs_env):
    tabs = tabs_env.tabs
    tabs._request_active = MagicMock(return_value=True)
    tabs.sync_focused_chat_context()
    tabs_env.window.controller.ctx.load.assert_not_called()

    tabs._request_active.return_value = False
    tabs.get_current_tab = MagicMock(return_value=tabs_env.make_tab(type=Tab.TAB_NOTEPAD))
    tabs.sync_focused_chat_context()
    tabs_env.window.controller.ctx.load.assert_not_called()

    chat = tabs_env.make_tab(pid=14, data_id=55)
    tabs.get_current_tab.return_value = chat
    tabs_env.core_ctx.get_current.return_value = 1
    tabs_env.core_ctx.get_meta_by_id.return_value = None
    tabs.sync_focused_chat_context()
    tabs_env.window.controller.ctx.load.assert_not_called()


def test_on_load_ctx_targets_explicit_pid_and_debugs(tabs_env):
    tabs = tabs_env.tabs
    chat = tabs_env.make_tab(pid=15)
    tabs_env.install(chat)
    tabs.bind_chat = MagicMock()
    tabs.debug = MagicMock()
    meta = SimpleNamespace(id=77)

    tabs.on_load_ctx(meta, pid=15)
    tabs.bind_chat.assert_called_once_with(chat, 77)
    tabs.debug.assert_called_once_with()


def test_get_chat_tab_by_data_id_prefers_active_column_then_index_pid(tabs_env):
    tabs = tabs_env.tabs
    a = tabs_env.make_tab(pid=30, idx=3, column_idx=0, data_id=7)
    b = tabs_env.make_tab(pid=20, idx=1, column_idx=1, data_id=7)
    c = tabs_env.make_tab(pid=10, idx=0, column_idx=1, data_id=7)
    tabs_env.install(a, b, c)
    tabs.set_current_column_idx(1)

    assert tabs.get_chat_tab_by_data_id(7) is c
    assert tabs.get_chat_tab_by_data_id(None) is None
    assert tabs.get_chat_tab_by_data_id(999) is None


def test_focus_chat_by_data_id_reveals_secondary_and_activates(tabs_env):
    tabs = tabs_env.tabs
    chat = tabs_env.make_tab(pid=31, idx=0, column_idx=1, data_id=8)
    tabs.get_chat_tab_by_data_id = MagicMock(return_value=chat)
    tabs.is_split_screen_enabled = MagicMock(return_value=False)
    tabs.enable_split_screen = MagicMock()
    tabs.activate_tab = MagicMock()

    assert tabs.focus_chat_by_data_id(8) is True
    tabs.enable_split_screen.assert_called_once_with(update_switch=True)
    tabs.activate_tab.assert_called_once_with(chat)

    tabs.get_chat_tab_by_data_id.return_value = None
    assert tabs.focus_chat_by_data_id(9) is False


def test_detach_chat_contexts_clears_each_matching_pid_and_leaves_tabs_open(tabs_env):
    tabs, window = tabs_env.tabs, tabs_env.window
    a = tabs_env.make_tab(pid=40, idx=0, column_idx=0, data_id=7, title="A")
    b = tabs_env.make_tab(pid=41, idx=0, column_idx=1, data_id="8", title="B")
    keep = tabs_env.make_tab(pid=42, idx=1, column_idx=0, data_id=9, title="Keep")
    tabs_env.install(a, b, keep)
    tabs.set_chat_placeholder = MagicMock(side_effect=lambda tab: setattr(tab, "title", "...") or True)

    assert tabs.detach_chat_contexts([7, "8", "bad"]) == 2

    assert window.controller.chat.render.clear_pid.call_args_list == [
        ((40,), {}), ((41,), {})
    ]
    assert tabs_env.output.remove_pid.call_args_list == [((40,), {}), ((41,), {})]
    assert a.data_id is None and b.data_id is None
    assert a.loaded is False and b.loaded is False
    assert keep.data_id == 9
    assert tabs.set_chat_placeholder.call_count == 2
    tabs_env.core_tabs.save.assert_called_once_with()

    tabs_env.core_tabs.save.reset_mock()
    assert tabs.detach_chat_contexts(None) == 0
    assert tabs.detach_chat_contexts(["bad"]) == 0
    tabs_env.core_tabs.save.assert_not_called()


def test_switch_to_first_chat_keeps_current_chat_or_activates_visible_fallback(tabs_env):
    tabs = tabs_env.tabs
    current = tabs_env.make_tab(pid=50, type=Tab.TAB_CHAT)
    tabs.get_current_tab = MagicMock(return_value=current)
    tabs.activate_tab = MagicMock()
    tabs.switch_to_first_chat()
    tabs.activate_tab.assert_not_called()

    tool = tabs_env.make_tab(pid=51, type=Tab.TAB_TOOL)
    visible_chat = tabs_env.make_tab(pid=52, column_idx=1, type=Tab.TAB_CHAT)
    tabs.get_current_tab.return_value = tool
    tabs.get_current_by_column = MagicMock(side_effect=[tool, visible_chat])
    tabs.switch_to_first_chat()
    tabs.activate_tab.assert_called_once_with(visible_chat)


def test_switch_to_first_chat_uses_core_fallback_when_no_selected_chat(tabs_env):
    tabs = tabs_env.tabs
    tool = tabs_env.make_tab(pid=53, type=Tab.TAB_TOOL)
    fallback = tabs_env.make_tab(pid=54, type=Tab.TAB_CHAT)
    tabs.get_current_tab = MagicMock(return_value=tool)
    tabs.get_current_by_column = MagicMock(return_value=tool)
    tabs_env.core_tabs.get_first_by_type.side_effect = None
    tabs_env.core_tabs.get_first_by_type.return_value = fallback
    tabs.activate_tab = MagicMock()

    tabs.switch_to_first_chat()
    tabs.activate_tab.assert_called_once_with(fallback)


def test_focus_by_type_resolves_closest_binds_meta_and_activates_without_context_sync(tabs_env):
    tabs, window = tabs_env.tabs, tabs_env.window
    current = tabs_env.make_tab(pid=60, idx=0, column_idx=0, type=Tab.TAB_NOTEPAD)
    target = tabs_env.make_tab(pid=61, idx=2, column_idx=1, type=Tab.TAB_CHAT)
    tabs.get_current_tab = MagicMock(return_value=current)
    tabs_env.core_tabs.get_closest_idx_by_type_exists.return_value = (2, 1, True)
    tabs_env.core_tabs.get_tab_by_index.side_effect = lambda idx, col: target if (idx, col) == (2, 1) else None
    tabs.is_split_screen_enabled = MagicMock(return_value=False)
    tabs.enable_split_screen = MagicMock()
    tabs.bind_chat = MagicMock()
    tabs.update_title_by_tab = MagicMock()
    tabs.activate_tab = MagicMock()
    tabs.debug = MagicMock()
    meta = SimpleNamespace(id=99)
    tabs_env.core_ctx.get_current.return_value = 1

    assert tabs.focus_by_type(Tab.TAB_CHAT, data_id=88, title="Topic", meta=meta) is target

    tabs.enable_split_screen.assert_called_once_with(update_switch=True)
    tabs.bind_chat.assert_called_once_with(target, 99)
    tabs.update_title_by_tab.assert_called_once_with(target, "Topic")
    tabs.activate_tab.assert_called_once_with(target, sync_context=False)
    window.controller.ctx.load.assert_called_once_with(99, tab_pid=61)
    tabs.debug.assert_called_once_with()


def test_focus_by_type_returns_none_when_type_absent(tabs_env):
    tabs = tabs_env.tabs
    tabs.get_current_tab = MagicMock(return_value=None)
    tabs_env.core_tabs.get_first_by_type.side_effect = None
    tabs_env.core_tabs.get_first_by_type.return_value = None
    assert tabs.focus_by_type(Tab.TAB_FILES) is None
