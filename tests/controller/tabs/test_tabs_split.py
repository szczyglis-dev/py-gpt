from types import SimpleNamespace
from unittest.mock import MagicMock

import pygpt_net.controller.tabs.split as split_mod
from pygpt_net.core.tabs.tab import Tab


def test_restore_revealed_split_chat_skips_while_request_active(tabs_env):
    tabs = tabs_env.tabs
    tabs._request_active = MagicMock(return_value=True)
    tabs._restore_revealed_split_chat(1)
    tabs_env.core_tabs.get_tab_by_index.assert_not_called()


def test_restore_revealed_split_chat_rebuilds_hidden_chat_without_selecting_context(tabs_env):
    tabs, window = tabs_env.tabs, tabs_env.window
    chat = tabs_env.make_tab(pid=10, idx=0, column_idx=1, type=Tab.TAB_CHAT, data_id=77)
    tabs_env.install(chat)
    tabs_env.widgets[1]._current = 0
    meta = SimpleNamespace(id=77)
    tabs_env.core_ctx.get_meta_by_id.return_value = meta
    window.controller.chat.render.get_pid_data.return_value = None
    tabs_env.output.get_pinned_pid.return_value = None
    tabs_env.output.pin_render_pid.return_value = 10

    tabs._restore_revealed_split_chat(1)

    tabs_env.output.pin_render_pid.assert_called_once_with(meta, pid=10, force=True)
    window.controller.ctx.refresh_output.assert_called_once_with(meta)
    tabs_env.output.unpin_render_pid.assert_called_once_with(meta=meta)
    window.controller.ctx.load.assert_not_called()


def test_restore_revealed_split_chat_restores_previous_render_pin(tabs_env):
    tabs, window = tabs_env.tabs, tabs_env.window
    chat = tabs_env.make_tab(pid=11, idx=0, column_idx=1, data_id=88)
    tabs_env.install(chat)
    tabs_env.widgets[1]._current = 0
    meta = SimpleNamespace(id=88)
    tabs_env.core_ctx.get_meta_by_id.return_value = meta
    window.controller.chat.render.get_pid_data.return_value = None
    tabs_env.output.get_pinned_pid.return_value = 5
    tabs_env.output.pin_render_pid.return_value = 11

    tabs._restore_revealed_split_chat(1)

    assert tabs_env.output.render_pids[88] == 5
    tabs_env.output.unpin_render_pid.assert_not_called()


def test_restore_revealed_split_chat_skips_invalid_or_already_rendered_targets(tabs_env):
    tabs, window = tabs_env.tabs, tabs_env.window
    tabs_env.widgets[1]._current = -1
    tabs._restore_revealed_split_chat(1)
    window.controller.ctx.refresh_output.assert_not_called()

    chat = tabs_env.make_tab(pid=12, idx=0, column_idx=1, data_id=90)
    tabs_env.install(chat); tabs_env.widgets[1]._current = 0
    tabs_env.core_ctx.get_meta_by_id.return_value = SimpleNamespace(id=90)
    window.controller.chat.render.get_pid_data.return_value = object()
    tabs._restore_revealed_split_chat(1)
    window.controller.ctx.refresh_output.assert_not_called()


def test_schedule_revealed_split_chat_restore_uses_qtimer(monkeypatch, tabs_env):
    tabs = tabs_env.tabs
    single_shot = MagicMock()
    monkeypatch.setattr(split_mod.QTimer, "singleShot", single_shot)
    tabs._schedule_revealed_split_chat_restore()
    assert single_shot.call_count == 1
    delay, callback = single_shot.call_args.args
    assert delay == 0
    tabs._restore_revealed_split_chat = MagicMock()
    callback()
    tabs._restore_revealed_split_chat.assert_called_once_with(1)


def test_is_split_screen_enabled_reads_config(tabs_env):
    tabs_env.config_values["layout.split"] = True
    assert tabs_env.tabs.is_split_screen_enabled() is True
    tabs_env.config_values["layout.split"] = False
    assert tabs_env.tabs.is_split_screen_enabled() is False


def test_on_split_screen_changed_persists_only_real_change_and_syncs_width(tabs_env):
    tabs, window = tabs_env.tabs, tabs_env.window
    tabs_env.config_values["layout.split"] = False
    # reflect set() into the fake config backing map
    window.core.config.set.side_effect = lambda key, value: tabs_env.config_values.__setitem__(key, value)
    window.ui.nodes["layout.split"].box.isChecked.return_value = False
    tabs._schedule_revealed_split_chat_restore = MagicMock()
    tabs.update_current = MagicMock()
    tabs._sync_chat_input_width = MagicMock()

    tabs.on_split_screen_changed(True)

    window.core.config.set.assert_called_once_with("layout.split", True)
    window.ui.nodes["layout.split"].box.setChecked.assert_called_once_with(True)
    window.core.config.save.assert_called_once_with()
    tabs._schedule_revealed_split_chat_restore.assert_called_once_with()
    tabs.update_current.assert_called_once_with()
    tabs._sync_chat_input_width.assert_called_once_with()

    window.core.config.save.reset_mock(); tabs.update_current.reset_mock(); tabs._sync_chat_input_width.reset_mock()
    tabs.on_split_screen_changed(True)
    window.core.config.save.assert_not_called()
    tabs.update_current.assert_not_called()
    tabs._sync_chat_input_width.assert_called_once_with()


def test_enable_split_screen_sets_geometry_config_and_optional_switch(tabs_env):
    tabs, window = tabs_env.tabs, tabs_env.window
    tabs.is_split_screen_enabled = MagicMock(return_value=False)
    tabs._schedule_revealed_split_chat_restore = MagicMock()
    tabs.update_current = MagicMock()
    tabs._sync_chat_input_width = MagicMock()

    tabs.enable_split_screen(update_switch=True)

    window.ui.splitters["columns"].setSizes.assert_called_once_with([1, 1])
    window.core.config.set.assert_called_once_with("layout.split", True)
    window.core.config.save.assert_called_once_with()
    tabs._schedule_revealed_split_chat_restore.assert_called_once_with()
    tabs.update_current.assert_called_once_with()
    tabs._sync_chat_input_width.assert_called_once_with()
    window.ui.nodes["layout.split"].box.setChecked.assert_called_once_with(True)


def test_enable_split_screen_is_noop_when_already_enabled(tabs_env):
    tabs = tabs_env.tabs
    tabs.is_split_screen_enabled = MagicMock(return_value=True)
    tabs.enable_split_screen()
    tabs_env.window.ui.splitters["columns"].setSizes.assert_not_called()


def test_disable_split_screen_forces_primary_and_updates_state(tabs_env):
    tabs, window = tabs_env.tabs, tabs_env.window
    tabs.set_current_column_idx = MagicMock()
    tabs.on_column_changed = MagicMock()
    tabs.update_current = MagicMock()
    tabs._sync_chat_input_width = MagicMock()

    tabs.disable_split_screen()

    window.ui.splitters["columns"].setSizes.assert_called_once_with([1, 0])
    tabs.set_current_column_idx.assert_called_once_with(0)
    tabs.on_column_changed.assert_called_once_with()
    window.core.config.set.assert_called_once_with("layout.split", False)
    window.core.config.save.assert_called_once_with()
    tabs.update_current.assert_called_once_with()
    tabs._sync_chat_input_width.assert_called_once_with()


def test_toggle_split_screen_delegates_by_state(tabs_env):
    tabs = tabs_env.tabs
    tabs.enable_split_screen = MagicMock()
    tabs.disable_split_screen = MagicMock()
    tabs.toggle_split_screen(True)
    tabs.enable_split_screen.assert_called_once_with()
    tabs.toggle_split_screen(False)
    tabs.disable_split_screen.assert_called_once_with()
