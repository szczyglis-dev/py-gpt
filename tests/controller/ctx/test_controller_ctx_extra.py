from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.controller.ctx.extra import Extra
from pygpt_net.core.events import KernelEvent, RenderEvent


def _extra():
    extra = Extra(MagicMock())
    extra.window.ui.nodes = {
        "input.send_btn": MagicMock(),
        "input.update_btn": MagicMock(),
        "input.cancel_btn": MagicMock(),
    }
    return extra


def test_ctx_extra_delete_actions_delegate_to_ctx_controller():
    extra = _extra()

    extra.delete_item(3)
    extra.delete_item_chain(4, 8)

    extra.window.controller.ctx.delete_item.assert_called_once_with(3)
    extra.window.controller.ctx.delete_item_chain.assert_called_once_with(4, 8)


def test_ctx_extra_copy_item_uses_clipboard_only_for_non_empty_item_output():
    extra = _extra()
    clipboard = MagicMock()
    item = SimpleNamespace(output="  hello  ")
    extra.window.core.ctx.get_item_by_id.return_value = item

    with patch("pygpt_net.controller.ctx.extra.QApplication.clipboard", return_value=clipboard), \
            patch("pygpt_net.controller.ctx.extra.trans", return_value="copied"):
        extra.copy_item(1)

    clipboard.setText.assert_called_once_with("hello")
    extra.window.update_status.assert_called_once_with("copied")


def test_ctx_extra_copy_code_block_handles_missing_and_existing_blocks():
    extra = _extra()
    clipboard = MagicMock()
    parser = MagicMock()
    parser.get_code_blocks.return_value = {2: "print('hello world')"}
    extra.window.controller.chat.render.instance.return_value.parser = parser

    with patch("pygpt_net.controller.ctx.extra.QApplication.clipboard", return_value=clipboard), \
            patch("pygpt_net.controller.ctx.extra.trans", return_value="copied"):
        extra.copy_code_block(9)
        clipboard.setText.assert_not_called()
        extra.copy_code_block(2)

    clipboard.setText.assert_called_once_with("print('hello world')")
    assert extra.window.update_status.call_count == 1


def test_ctx_extra_copy_code_text_trims_clipboard_value_and_shortens_status():
    extra = _extra()
    clipboard = MagicMock()
    value = "  " + "x" * 30 + "  "

    with patch("pygpt_net.controller.ctx.extra.QApplication.clipboard", return_value=clipboard), \
            patch("pygpt_net.controller.ctx.extra.trans", return_value="copied"):
        extra.copy_code_text(value)

    clipboard.setText.assert_called_once_with("x" * 30)
    assert "..." in extra.window.update_status.call_args.args[0]


def test_ctx_extra_preview_and_run_code_delegate_to_code_interpreter_plugin():
    extra = _extra()
    plugin = MagicMock()
    extra.window.core.plugins.get.return_value = plugin

    extra.preview_code_text("<b>x</b>")
    extra.run_code_text("print(1)")

    plugin.handle_html_output.assert_called_once_with("<b>x</b>")
    plugin.handle_python_run.assert_called_once_with("print(1)")


def test_ctx_extra_edit_item_populates_input_and_edit_state():
    extra = _extra()
    item = SimpleNamespace(input="question", meta=SimpleNamespace(id=11))
    extra.window.core.ctx.get_item_by_id.return_value = item
    extra.edit_show = MagicMock()

    extra.edit_item(5)

    assert extra.window.controller.ctx.edit_meta_id == 11
    assert extra.window.controller.ctx.edit_item_id == 5
    extra.window.controller.chat.common.clear_input.assert_called_once_with()
    extra.window.controller.chat.common.append_to_input.assert_called_once_with("question")
    extra.edit_show.assert_called_once_with()


def test_ctx_extra_edit_show_and_hide_toggle_expected_buttons():
    extra = _extra()

    extra.edit_show()
    extra.window.ui.nodes["input.send_btn"].setVisible.assert_called_with(False)
    extra.window.ui.nodes["input.update_btn"].setVisible.assert_called_with(True)
    extra.window.ui.nodes["input.cancel_btn"].setVisible.assert_called_with(True)

    extra.edit_hide()
    extra.window.ui.nodes["input.send_btn"].setVisible.assert_called_with(True)
    extra.window.ui.nodes["input.update_btn"].setVisible.assert_called_with(False)
    extra.window.ui.nodes["input.cancel_btn"].setVisible.assert_called_with(False)


def test_ctx_extra_edit_submit_dispatches_render_action_and_resends_input():
    extra = _extra()
    item = SimpleNamespace(meta=SimpleNamespace(id=7))
    extra.window.controller.ctx.edit_item_id = 3
    extra.window.controller.ctx.edit_meta_id = 7
    extra.window.core.ctx.get_current.return_value = 2
    extra.window.core.ctx.get_item_by_id.return_value = item
    extra.window.core.config.get.side_effect = lambda key: {"model": "m", "mode": "chat"}[key]
    extra.edit_hide = MagicMock()

    extra.edit_submit()

    extra.window.controller.kernel.resume.assert_called_once_with()
    extra.window.controller.ctx.select.assert_called_once_with(7)
    extra.window.core.ctx.remove_items_from.assert_called_once_with(7, 3)
    extra.window.core.ctx.set_model.assert_called_once_with("m")
    event = extra.window.dispatch.call_args.args[0]
    assert isinstance(event, RenderEvent)
    assert event.name == RenderEvent.ACTION_EDIT_SUBMIT
    extra.window.controller.model.set.assert_called_once_with("chat", "m")
    extra.window.controller.chat.input.send_input.assert_called_once_with(force=True)
    assert extra.window.controller.ctx.edit_item_id is None
    assert extra.window.controller.ctx.edit_meta_id is None
    extra.edit_hide.assert_called_once_with()


def test_ctx_extra_is_editing_and_cancel_reset_state():
    extra = _extra()
    extra.window.controller.ctx.edit_item_id = 4
    extra.window.controller.ctx.edit_meta_id = 9
    extra.edit_hide = MagicMock()

    assert extra.is_editing() is True
    extra.edit_cancel()
    assert extra.is_editing() is False
    assert extra.window.controller.ctx.edit_meta_id is None
    extra.window.controller.chat.common.clear_input.assert_called_once_with()
    extra.edit_hide.assert_called_once_with()


def test_ctx_extra_replay_requests_confirmation_before_force():
    extra = _extra()

    with patch("pygpt_net.controller.ctx.extra.trans", return_value="confirm"):
        extra.replay_item(8, force=False)

    extra.window.controller.kernel.resume.assert_called_once_with()
    extra.window.ui.dialogs.confirm.assert_called_once_with(type="ctx.replay_item", id=8, msg="confirm")
    extra.window.dispatch.assert_not_called()


def test_ctx_extra_replay_force_dispatches_render_and_kernel_events():
    extra = _extra()
    item = SimpleNamespace(input="again", meta=SimpleNamespace(id=5))
    extra.window.core.ctx.get_item_by_id.return_value = item
    extra.window.core.config.get.side_effect = lambda key: {"model": "m", "mode": "chat"}[key]

    extra.replay_item(8, force=True)

    assert extra.window.dispatch.call_count == 2
    render_event = extra.window.dispatch.call_args_list[0].args[0]
    kernel_event = extra.window.dispatch.call_args_list[1].args[0]
    assert isinstance(render_event, RenderEvent)
    assert render_event.name == RenderEvent.ACTION_REGEN_SUBMIT
    assert isinstance(kernel_event, KernelEvent)
    assert kernel_event.name == KernelEvent.INPUT_SYSTEM
    assert kernel_event.data["context"].ctx is item
    assert kernel_event.data["context"].prompt == "again"
    extra.window.controller.model.set.assert_called_once_with("chat", "m")


def test_ctx_extra_audio_read_item_tracks_current_playback_without_real_audio():
    extra = _extra()
    item = SimpleNamespace(output="answer")
    extra.window.core.ctx.get_item_by_id.return_value = item

    extra.audio_read_item(2)
    extra.window.controller.audio.stop_output.assert_called_once_with()
    extra.window.controller.audio.read_text.assert_called_once_with("answer")
    assert extra.audio_play_id == 2

    extra.window.controller.audio.stop_output.reset_mock()
    extra.window.controller.audio.read_text.reset_mock()
    extra.audio_read_item(2)
    extra.window.controller.audio.stop_output.assert_not_called()
    extra.window.controller.audio.read_text.assert_called_once_with("answer")
