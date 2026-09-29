from types import SimpleNamespace
from unittest.mock import MagicMock, call

from pygpt_net.core.tabs.tab import Tab


def test_setup_loads_widgets_notepad_options_and_marks_initialized(tabs_env):
    tabs, window = tabs_env.tabs, tabs_env.window
    tabs.setup_options = MagicMock()

    tabs.setup()

    window.core.tabs.load.assert_called_once_with()
    window.controller.notepad.load.assert_called_once_with()
    tabs.setup_options.assert_called_once_with()
    assert tabs.is_widget_loading() is False
    assert tabs.is_initialized() is True


def test_setup_reload_skips_options_but_still_marks_initialized(tabs_env):
    tabs = tabs_env.tabs
    tabs.setup_options = MagicMock()
    tabs.setup(reload=True)
    tabs.setup_options.assert_not_called()
    assert tabs.is_initialized() is True


def test_setup_options_syncs_split_switch_geometry_and_input_width(tabs_env):
    tabs, window = tabs_env.tabs, tabs_env.window
    tabs_env.config_values["layout.split"] = False
    tabs._sync_chat_input_width = MagicMock()

    tabs.setup_options()

    window.ui.nodes["layout.split"].setChecked.assert_called_once_with(False)
    window.ui.splitters["columns"].setSizes.assert_called_once_with([1, 0])
    tabs._sync_chat_input_width.assert_called_once_with()


def test_unload_resets_state_disables_columns_and_removes_all_in_suppressed_transaction(tabs_env):
    tabs, window = tabs_env.tabs, tabs_env.window
    tabs._state.activate(1, 3, 99)
    tabs.lock()

    tabs.unload()

    assert tabs.get_current_column_idx() == 0
    assert tabs.get_current_pid() is None
    assert tabs.is_locked() is False
    for col in window.ui.layout.columns:
        assert col.setUpdatesEnabled.call_args_list == [call(False), call(True)]
    window.core.tabs.remove_all.assert_called_once_with()
    assert tabs.are_tab_events_suppressed() is False


def test_reload_rebuilds_and_optionally_restores_after_context_reload(tabs_env):
    tabs, window = tabs_env.tabs, tabs_env.window
    tabs.unload = MagicMock()
    tabs.setup = MagicMock()
    tabs.restore_after_ctx_reload = MagicMock()
    tabs.debug = MagicMock()

    tabs.reload(restore_data=True)

    tabs.unload.assert_called_once_with()
    tabs.setup.assert_called_once_with(reload=True)
    tabs.restore_after_ctx_reload.assert_called_once_with()
    tabs.debug.assert_called_once_with()
    for col in window.ui.layout.columns:
        assert col.setUpdatesEnabled.call_args_list == [call(False), call(True)]

    tabs.restore_after_ctx_reload.reset_mock()
    tabs.reload(restore_data=False)
    tabs.restore_after_ctx_reload.assert_not_called()


def test_restore_after_ctx_reload_prepares_render_then_restores_data(tabs_env):
    tabs, window = tabs_env.tabs, tabs_env.window
    tabs.restore_data = MagicMock()
    tabs.debug = MagicMock()

    tabs.restore_after_ctx_reload()

    window.dispatch.assert_called_once()
    event = window.dispatch.call_args.args[0]
    assert event.name == event.PREPARE
    tabs.restore_data.assert_called_once_with()
    tabs.debug.assert_called_once_with()


def test_reload_after_applies_plain_or_web_visibility_per_pid(tabs_env):
    tabs, window = tabs_env.tabs, tabs_env.window
    web = MagicMock(); plain = MagicMock()
    window.ui.nodes["output"] = {1: web}
    window.ui.nodes["output_plain"] = {1: plain}
    tabs.debug = MagicMock()

    tabs_env.config_values["render.plain"] = True
    tabs.reload_after()
    plain.setVisible.assert_called_with(True)
    web.setVisible.assert_called_with(False)

    plain.setVisible.reset_mock(); web.setVisible.reset_mock()
    tabs_env.config_values["render.plain"] = False
    tabs.reload_after()
    plain.setVisible.assert_called_with(False)
    web.setVisible.assert_called_with(True)


def test_finalize_profile_reload_rebuilds_visible_chat_and_reapplies_footer(tabs_env):
    tabs, window = tabs_env.tabs, tabs_env.window
    chat = tabs_env.make_tab(pid=20, idx=0, column_idx=0, type=Tab.TAB_CHAT, data_id=77)
    tabs_env.install(chat)
    tabs_env.widgets[0]._current = 0
    meta = SimpleNamespace(id=77, mode="chat", assistant=None)
    tabs_env.core_ctx.get_meta_by_id.return_value = meta
    tabs_env.output.get_pinned_pid.return_value = None
    tabs_env.output.pin_render_pid.return_value = 20
    tabs.update_current = MagicMock()
    tabs.debug = MagicMock()

    tabs.finalize_profile_reload()

    window.controller.ctx.fresh_output.assert_called_once_with(meta)
    window.controller.ctx.refresh_output.assert_called_once_with(meta)
    tabs_env.output.unpin_render_pid.assert_called_once_with(meta=meta)
    assert tabs.get_current_column_idx() == 0
    assert tabs._state.current_pid(0) == 20
    window.controller.ui.mode.update.assert_called_once_with()
    window.controller.ui.vision.update.assert_called_once_with()
    window.controller.audio.on_tab_changed.assert_called_once_with(chat)
    window.controller.ui.mode.show_chat_footer.assert_called_once_with()
    window.controller.plugins.update_info.assert_called_once_with()
    window.controller.ui.update_chat_label.assert_called_once_with()
    window.controller.ui.update_tokens.assert_called_once_with()
    window.controller.ctx.common.update_label.assert_called_once_with("chat", None)
    tabs.update_current.assert_called_once_with()
    tabs.debug.assert_called_once_with()


def test_finalize_profile_reload_hides_chat_footer_for_non_chat_active_tab(tabs_env):
    tabs, window = tabs_env.tabs, tabs_env.window
    note = tabs_env.make_tab(pid=21, idx=0, column_idx=0, type=Tab.TAB_NOTEPAD)
    tabs_env.install(note)
    tabs_env.widgets[0]._current = 0
    tabs.update_current = MagicMock()
    tabs.debug = MagicMock()

    tabs.finalize_profile_reload()

    window.controller.ui.mode.hide_chat_footer.assert_called_once_with()
    window.controller.ctx.fresh_output.assert_not_called()
