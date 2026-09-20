from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.controller.lang.settings import Settings


def _window(initialized=True):
    window = MagicMock()
    editor = MagicMock()
    editor.initialized = initialized
    window.controller.settings.editor = editor
    window.ui.nodes = {}
    window.ui.config = {"config": {}}
    tabs = MagicMock()
    tabs.currentIndex.return_value = 2
    window.ui.tabs = {"settings.section": tabs}
    window.core.settings.get_sections.return_value = {"general": {}, "audio": {}}
    return window, editor, tabs


def test_lang_settings_apply_initializes_editor_when_needed():
    window, editor, _ = _window(initialized=False)
    editor.options = {}

    Settings(window).apply()

    editor.load_config_options.assert_called_once_with(False)


def test_lang_settings_apply_updates_bool_text_labels_descriptions_and_sections():
    window, editor, tabs = _window(initialized=True)
    bool_widget = MagicMock()
    text_label = MagicMock()
    desc_node = MagicMock()
    alias_desc_node = MagicMock()
    window.ui.config["config"]["flag"] = bool_widget
    window.ui.nodes = {
        "settings.name.label": text_label,
        "settings.name.desc": desc_node,
        "desc.name": alias_desc_node,
    }
    editor.options = {
        "flag": {"label": "label.flag", "type": "bool", "description": ""},
        "name": {"label": "label.name", "type": "text", "description": "desc.name"},
    }

    with patch("pygpt_net.controller.lang.settings.trans", side_effect=lambda key: f"tr:{key}"):
        Settings(window).apply()

    bool_widget.setText.assert_called_once_with("tr:label.flag")
    bool_widget.box.setText.assert_called_once_with("tr:label.flag")
    text_label.setText.assert_called_once_with("tr:label.name")
    desc_node.setText.assert_called_once_with("tr:desc.name")
    alias_desc_node.setText.assert_called_once_with("tr:desc.name")
    assert tabs.setTabText.call_args_list[0].args == (0, "tr:settings.section.general")
    assert tabs.setTabText.call_args_list[1].args == (1, "tr:settings.section.audio")
    window.settings.refresh_list.assert_called_once_with()
    window.controller.settings.set_by_tab.assert_called_once_with(2)
