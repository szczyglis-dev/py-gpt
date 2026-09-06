from collections import defaultdict
from unittest.mock import MagicMock, patch

from pygpt_net.controller.lang.custom import Custom


def _window(profile_mode="create", auto_capture=False):
    window = MagicMock()
    window.ui.tabs = MagicMock()
    window.ui.plugin_addon = MagicMock()
    window.ui.config = MagicMock()
    window.ui.nodes = defaultdict(MagicMock)
    window.ui.models = MagicMock()
    window.ui.menu = MagicMock()
    window.ui.menu["theme"].__iter__.return_value = iter([])
    profile_dialog = MagicMock()
    profile_dialog.mode = profile_mode
    window.ui.dialog = {"profile.item": profile_dialog}
    window.ui.dialogs.about.prepare_content.return_value = "about.content"

    def cfg_get(key, default=None):
        if key == "vision.capture.auto":
            return auto_capture
        if key == "mode":
            return "chat"
        return default

    window.core.config.get.side_effect = cfg_get
    window.controller.idx.get_modes_keys.return_value = ["a", "b"]
    return window


def test_lang_custom_apply_updates_capture_tooltip_and_delegates_subcontrollers():
    window = _window(profile_mode="create", auto_capture=False)

    with patch("pygpt_net.controller.lang.custom.trans", side_effect=lambda key: f"tr:{key}"):
        Custom(window).apply()

    window.controller.painter.common.retranslate_draw_modes.assert_called_once_with()
    window.ui.nodes["video.preview"].video.setToolTip.assert_called_once_with("tr:vision.capture.label")
    window.controller.attachment.update_tab.assert_called_once_with("chat")
    window.controller.assistant.files.update_tab.assert_called_once_with()
    window.controller.idx.settings.update_text_last_updated.assert_called_once_with()
    window.controller.idx.settings.update_text_loaders.assert_called_once_with()
    window.controller.mode.init_list.assert_called_once_with()
    window.ui.nodes["dialog.profile.item.btn.update"].setText.assert_called_once_with(
        "tr:dialog.profile.item.btn.create"
    )
    window.ui.nodes["llama_index.mode.select"].set_keys.assert_called_once_with(["a", "b"])


def test_lang_custom_apply_uses_auto_capture_tooltip_and_tolerates_missing_painter_helper():
    window = _window(profile_mode="edit", auto_capture=True)
    window.controller.painter.common.retranslate_draw_modes.side_effect = AttributeError("missing")

    with patch("pygpt_net.controller.lang.custom.trans", side_effect=lambda key: f"tr:{key}"):
        Custom(window).apply()

    window.ui.nodes["video.preview"].video.setToolTip.assert_called_once_with("tr:vision.capture.auto.label")
    window.ui.nodes["dialog.profile.item.btn.update"].setText.assert_called_once_with(
        "tr:dialog.profile.item.btn.update"
    )
