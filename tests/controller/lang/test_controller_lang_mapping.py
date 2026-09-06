from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.controller.lang.mapping import Mapping


def test_lang_mapping_apply_map_updates_changed_values_and_skips_missing_targets():
    mapping = Mapping(MagicMock())
    changed = MagicMock()
    changed.text.return_value = "old"
    same = MagicMock()
    same.text.return_value = "tr:same"
    targets = {"changed": changed, "same": same}

    with patch("pygpt_net.controller.lang.mapping.trans", side_effect=lambda key: f"tr:{key}"):
        mapping._apply_map(
            {"changed": "new", "same": "same", "missing": "x"},
            targets,
            "text",
            "setText",
        )

    changed.setText.assert_called_once_with("tr:new")
    same.setText.assert_not_called()


def test_lang_mapping_apply_map_tolerates_broken_getters_and_setters():
    mapping = Mapping(MagicMock())
    broken_getter = MagicMock()
    broken_getter.text.side_effect = RuntimeError("getter")
    broken_setter = MagicMock()
    del broken_setter.setText

    with patch("pygpt_net.controller.lang.mapping.trans", side_effect=lambda key: key):
        mapping._apply_map(
            {"a": "a", "b": "b"},
            {"a": broken_getter, "b": broken_setter},
            "text",
            "setText",
        )

    broken_getter.setText.assert_called_once_with("a")


def test_lang_mapping_apply_builds_mapping_once_and_translates_tool_menu_labels():
    window = MagicMock()
    node = MagicMock()
    node.text.return_value = "old"
    node.setText.side_effect = lambda value: setattr(node.text, "return_value", value)
    tool_menu = MagicMock()
    tool_menu.text.return_value = "old"
    tool_menu.setText.side_effect = lambda value: setattr(tool_menu.text, "return_value", value)
    window.ui.nodes = {"node": node}
    window.ui.menu = {"tool.files": tool_menu}
    window.ui.dialog = {}
    window.controller.tools.get_tab_tools.return_value = {
        "tool.files": ["files", "folder", 1],
    }

    mapping = Mapping(window)
    mapping.get_mapping = MagicMock(return_value={
        "nodes": {"node": "node.label"},
        "menu.title": {},
        "menu.text": {},
        "menu.tooltip": {},
        "dialog.title": {},
        "tooltip": {},
        "placeholder": {},
    })

    with patch("pygpt_net.controller.lang.mapping.trans", side_effect=lambda key: f"tr:{key}"):
        mapping.apply()
        mapping.apply()

    mapping.get_mapping.assert_called_once_with()
    assert node.setText.call_count == 1
    tool_menu.setText.assert_called_with("tr:output.tab.files")


def test_lang_mapping_get_mapping_contains_expected_sections_and_stable_keys():
    result = Mapping(MagicMock()).get_mapping()

    assert set(result) == {
        "nodes",
        "menu.title",
        "menu.text",
        "menu.tooltip",
        "dialog.title",
        "tooltip",
        "placeholder",
    }
    assert result["nodes"]["output.timestamp"] == "output.timestamp"
    assert result["nodes"]["input.send_btn"] == "input.btn.send"
    assert result["menu.title"]["menu.theme"] == "menu.theme"
    assert result["dialog.title"]["info.about"] == "dialog.about.title"
