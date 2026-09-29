from types import SimpleNamespace
from unittest.mock import MagicMock

import pygpt_net.controller.tabs.input as input_mod
from pygpt_net.core.tabs.tab import Tab


def test_sync_chat_input_width_schedules_sync_when_supported(monkeypatch, tabs_env):
    tabs = tabs_env.tabs
    single_shot = MagicMock()
    monkeypatch.setattr(input_mod.QTimer, "singleShot", single_shot)
    tabs._sync_chat_input_width()
    single_shot.assert_called_once_with(0, tabs_env.window.ui.nodes["input.container"].sync_width)

    tabs_env.window.ui.nodes["input.container"] = object()
    single_shot.reset_mock()
    tabs._sync_chat_input_width()
    single_shot.assert_not_called()


def test_update_current_remembers_selected_pid_updates_input_and_debugs(tabs_env):
    tabs = tabs_env.tabs
    tab = tabs_env.make_tab(pid=1, idx=2, column_idx=1)
    tabs.get_current_tab = MagicMock(return_value=tab)
    tabs.get_current_column_idx = MagicMock(return_value=1)
    tabs._update_chat_input_visibility = MagicMock()
    tabs.debug = MagicMock()

    tabs.update_current()

    assert tabs._state.current_pid(1) == 1
    assert tabs._state.current_idx(1) == 2
    tabs._update_chat_input_visibility.assert_called_once_with(tab)
    tabs.debug.assert_called_once_with()


def test_get_column_current_tab_resolves_widget_selection(tabs_env):
    tabs = tabs_env.tabs
    tab = tabs_env.make_tab(pid=2, idx=0, column_idx=1)
    tabs_env.install(tab)
    tabs_env.widgets[1]._current = 0
    assert tabs._get_column_current_tab(1) is tab
    tabs_env.widgets[1]._current = -1
    assert tabs._get_column_current_tab(1) is None

    old = tabs.window.ui.layout
    tabs.window.ui.layout = None
    assert tabs._get_column_current_tab(0) is None
    tabs.window.ui.layout = old


def test_chat_input_target_column_handles_none_single_and_two_chat_columns(tabs_env):
    tabs = tabs_env.tabs
    left_tool = tabs_env.make_tab(pid=3, idx=0, column_idx=0, type=Tab.TAB_TOOL)
    right_chat = tabs_env.make_tab(pid=4, idx=0, column_idx=1, type=Tab.TAB_CHAT)
    tabs_env.install(left_tool, right_chat)
    tabs.is_split_screen_enabled = MagicMock(return_value=False)
    assert tabs._get_chat_input_target_column() is None

    left_chat = tabs_env.make_tab(pid=5, idx=0, column_idx=0, type=Tab.TAB_CHAT)
    tabs_env.install(left_chat, right_chat)
    assert tabs._get_chat_input_target_column() == 0

    tabs.is_split_screen_enabled.return_value = True
    tabs.set_current_column_idx(1)
    assert tabs._get_chat_input_target_column() == 1
    assert tabs.get_chat_input_column_idx() == 1
    assert tabs.is_chat_input_visible() is True


def test_chat_input_target_column_uses_first_chat_if_active_column_is_stale(tabs_env):
    tabs = tabs_env.tabs
    left = tabs_env.make_tab(pid=6, idx=0, column_idx=0, type=Tab.TAB_CHAT)
    right = tabs_env.make_tab(pid=7, idx=0, column_idx=1, type=Tab.TAB_CHAT)
    tabs_env.install(left, right)
    tabs.is_split_screen_enabled = MagicMock(return_value=True)
    tabs.get_current_column_idx = MagicMock(return_value=99)
    assert tabs._get_chat_input_target_column() == 0


def test_update_chat_input_visibility_show_mounts_and_restores_saved_sizes(monkeypatch, tabs_env):
    tabs, window = tabs_env.tabs, tabs_env.window
    composer = window.ui.nodes["input.container"]
    root = window.ui.nodes["input.root"]
    tabs._get_chat_input_target_column = MagicMock(return_value=1)
    tabs._is_expanded_chat_input_sizes = MagicMock(side_effect=lambda sizes: bool(sizes))
    tabs._chat_input_splitter_sizes = [400, 200]
    tabs._restore_chat_input_splitter_sizes = MagicMock()
    window.ui.layout.mount_chat_input.return_value = None
    single_shot = MagicMock()
    monkeypatch.setattr(input_mod.QTimer, "singleShot", single_shot)

    tabs._update_chat_input_visibility(None)

    window.ui.layout.mount_chat_input.assert_called_once_with(root, 1)
    root.show.assert_called_once_with()
    composer.show.assert_called_once_with()
    assert tabs._chat_input_suppressed is False
    assert tabs._chat_input_splitter_sizes is None
    tabs._restore_chat_input_splitter_sizes.assert_called()
    assert single_shot.call_count >= 1


def test_update_chat_input_visibility_hide_caches_geometry_and_unmounts(tabs_env):
    tabs, window = tabs_env.tabs, tabs_env.window
    composer = window.ui.nodes["input.container"]
    root = window.ui.nodes["input.root"]
    tabs._get_chat_input_target_column = MagicMock(return_value=None)
    tabs._is_expanded_chat_input_sizes = MagicMock(return_value=True)
    window.ui.layout.hide_chat_input = MagicMock()

    tabs._update_chat_input_visibility(None)

    assert tabs._chat_input_suppressed is True
    assert tabs._chat_input_splitter_sizes == [500, 200]
    composer.hide.assert_called_once_with()
    root.hide.assert_called_once_with()
    window.ui.layout.hide_chat_input.assert_called_once_with(root)


def test_input_root_index_supports_direct_and_ancestor_lookup(tabs_env):
    tabs = tabs_env.tabs
    root = object()
    splitter = MagicMock()
    splitter.indexOf.return_value = 1
    assert tabs._input_root_index(splitter, root) == 1

    splitter.indexOf.return_value = -1
    splitter.count.return_value = 2
    a, b = MagicMock(), MagicMock()
    a.isAncestorOf.return_value = False
    b.isAncestorOf.return_value = True
    splitter.widget.side_effect = [a, b]
    assert tabs._input_root_index(splitter, root) == 1
    assert tabs._input_root_index(None, root) == -1


def test_chat_input_footer_height_is_zero(tabs_env):
    assert tabs_env.tabs._chat_input_footer_height() == 0


def test_is_expanded_chat_input_sizes_validates_shape_total_and_input_height(tabs_env):
    tabs = tabs_env.tabs
    tabs._input_root_index = MagicMock(return_value=1)
    assert tabs._is_expanded_chat_input_sizes([500, 200]) is True
    assert tabs._is_expanded_chat_input_sizes([500, 8]) is False
    assert tabs._is_expanded_chat_input_sizes([0, 0]) is False
    assert tabs._is_expanded_chat_input_sizes([1]) is False
    assert tabs._is_expanded_chat_input_sizes(None) is False


def test_remember_and_get_chat_input_splitter_sizes_for_save(tabs_env):
    tabs = tabs_env.tabs
    tabs._chat_input_suppressed = True
    tabs._is_expanded_chat_input_sizes = MagicMock(return_value=True)
    tabs.remember_restored_chat_input_splitter_sizes([300, 150])
    assert tabs._chat_input_splitter_sizes == [300, 150]
    assert tabs.get_chat_input_splitter_sizes_for_save() == [300, 150]

    tabs._chat_input_suppressed = False
    assert tabs.get_chat_input_splitter_sizes_for_save() is None


def test_ensure_chat_input_splitter_visible_expands_collapsed_input(tabs_env):
    tabs, window = tabs_env.tabs, tabs_env.window
    splitter = tabs_env.splitter
    splitter._sizes = [695, 5]
    output_widget = splitter.widget(0)
    output_widget.minimumSizeHint.return_value.height.return_value = 100
    tabs._input_root_index = MagicMock(return_value=1)
    # expanded only after height is raised
    tabs._is_expanded_chat_input_sizes = MagicMock(side_effect=lambda sizes: bool(sizes) and sizes[1] > 8)
    tabs._chat_input_suppressed = False

    tabs._ensure_chat_input_splitter_visible()

    splitter.setSizes.assert_called()
    assert splitter.sizes()[1] >= 140
    assert window.controller.ui.splitter_output_size_input == splitter.sizes()


def test_ensure_chat_input_splitter_visible_noops_while_suppressed(tabs_env):
    tabs = tabs_env.tabs
    tabs._chat_input_suppressed = True
    tabs._ensure_chat_input_splitter_visible()
    tabs_env.splitter.setSizes.assert_not_called()


def test_collapse_chat_input_splitter_reclaims_input_height(tabs_env):
    tabs = tabs_env.tabs
    tabs._chat_input_suppressed = True
    tabs._input_root_index = MagicMock(return_value=1)
    tabs._is_expanded_chat_input_sizes = MagicMock(return_value=True)
    tabs_env.splitter._sizes = [500, 200]

    tabs._collapse_chat_input_splitter()

    tabs_env.splitter.setSizes.assert_called_once_with([700, 0])
    assert tabs._chat_input_splitter_sizes == [500, 200]


def test_restore_chat_input_splitter_sizes_validates_state_and_restores(tabs_env):
    tabs = tabs_env.tabs
    tabs._chat_input_suppressed = False
    tabs._restore_chat_input_splitter_sizes([450, 250])
    tabs_env.splitter.setSizes.assert_called_once_with([450, 250])

    tabs_env.splitter.setSizes.reset_mock()
    tabs._chat_input_suppressed = True
    tabs._restore_chat_input_splitter_sizes([400, 300])
    tabs_env.splitter.setSizes.assert_not_called()
