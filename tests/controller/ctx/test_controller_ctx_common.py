from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.controller.ctx.common import Common
from pygpt_net.core.tabs.tab import Tab


def _common():
    common = Common.__new__(Common)
    common.window = MagicMock()
    common.summarizer = MagicMock()
    return common


def test_ctx_common_update_label_by_current_uses_mode_and_assistant_name():
    common = _common()
    common.window.core.ctx.get_mode.return_value = "assistant"
    common.window.core.ctx.get_assistant.return_value = "a1"
    common.window.core.assistants.get_by_id.return_value = SimpleNamespace(name="Helper")

    with patch("pygpt_net.controller.ctx.common.trans", return_value="Assistant"):
        common.update_label_by_current()

    common.window.controller.ui.update_ctx_label.assert_called_once_with("Assistant (Helper)")


def test_ctx_common_update_label_falls_back_to_config_mode_and_handles_none():
    common = _common()
    common.window.core.ctx.get_mode.return_value = None
    common.window.core.config.get.return_value = "chat"

    with patch("pygpt_net.controller.ctx.common.trans", return_value="Chat"):
        common.update_label_by_current()
        common.update_label(None)

    common.window.controller.ui.update_ctx_label.assert_called_once_with("Chat")


def test_ctx_common_update_label_uses_explicit_assistant_id():
    common = _common()
    common.window.core.assistants.get_by_id.return_value = SimpleNamespace(name="A")

    with patch("pygpt_net.controller.ctx.common.trans", return_value="Assistant"):
        common.update_label("assistant", "a")

    common.window.controller.ui.update_ctx_label.assert_called_once_with("Assistant (A)")


def test_ctx_common_duplicate_copies_attachments_and_schedules_single_refresh():
    common = _common()
    common.window.core.ctx.duplicate.side_effect = [10, None, 12]

    with patch("pygpt_net.controller.ctx.common.QTimer.singleShot") as single_shot:
        common.duplicate([1, 2, 3])

    assert common.window.core.ctx.duplicate.call_args_list[0].args == (1,)
    common.window.core.attachments.context.duplicate.assert_any_call(1, 10)
    common.window.core.attachments.context.duplicate.assert_any_call(3, 12)
    assert common.window.update_status.call_count == 2
    single_shot.assert_called_once_with(10, common._update_ctx_no_scroll)


def test_ctx_common_dismiss_rename_and_focus_chat_delegate_ui_actions():
    common = _common()
    common.window.ui.dialog = {"rename": MagicMock()}
    meta = SimpleNamespace(id=4, name="Topic")

    common.dismiss_rename()
    common.focus_chat(meta)

    common.window.ui.dialog["rename"].close.assert_called_once_with()
    common.window.controller.ui.tabs.focus_by_type.assert_called_once_with(
        Tab.TAB_CHAT,
        data_id=4,
        title="Topic",
        meta=meta,
    )


def test_ctx_common_toggle_display_filter_builds_expected_core_filter():
    common = _common()

    common.toggle_display_filter("pinned")
    common.window.core.ctx.set_display_filters.assert_called_with({"is_important": {"mode": "=", "value": 1}})

    common.toggle_display_filter("indexed")
    common.window.core.ctx.set_display_filters.assert_called_with({"indexed_ts": {"mode": ">", "value": 0}})

    common.toggle_display_filter("all")
    common.window.core.ctx.set_display_filters.assert_called_with({})
    assert common.window.controller.ctx.update.call_count == 3


def test_ctx_common_restore_filters_labels_restores_saved_values():
    common = _common()
    common.window.core.config.get.return_value = ["red", "blue"]
    common.window.ui.nodes = {"filter.ctx.labels": MagicMock()}

    common.restore_filters_labels()

    assert common.window.core.ctx.filters_labels == ["red", "blue"]
    common.window.ui.nodes["filter.ctx.labels"].restore.assert_called_once_with(["red", "blue"])


def test_ctx_common_copy_id_uses_clipboard_without_real_qt_clipboard():
    common = _common()
    clipboard = MagicMock()

    with patch("pygpt_net.controller.ctx.common.QApplication.clipboard", return_value=clipboard):
        common.copy_id([3, 7])

    common.window.controller.chat.common.append_to_input.assert_called_once_with("@3 @7", separator=" ")
    clipboard.setText.assert_called_once_with("@3 @7")


def test_ctx_common_reset_requests_confirmation_or_resets_selected_contexts():
    common = _common()

    with patch("pygpt_net.controller.ctx.common.trans", return_value="confirm"):
        common.reset(5, force=False)
    common.window.ui.dialogs.confirm.assert_called_once_with(type="ctx.reset_meta", id=5, msg="confirm")

    common.window.core.ctx.get_current.return_value = 6
    common.reset([5, 6], force=True)
    common.window.core.ctx.reset_meta.assert_any_call(5)
    common.window.core.ctx.reset_meta.assert_any_call(6)
    common.window.core.attachments.context.reset_by_meta_id.assert_any_call(5, delete_files=True)
    common.window.core.attachments.context.reset_by_meta_id.assert_any_call(6, delete_files=True)
    common.window.controller.ctx.load.assert_called_once_with(6)
