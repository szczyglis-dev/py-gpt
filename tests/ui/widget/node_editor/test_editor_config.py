from unittest.mock import patch

from pygpt_net.ui.widget.node_editor.config import EditorConfig


def test_editor_config_falls_back_when_translation_missing_empty_or_raises():
    cfg = EditorConfig()

    with patch("pygpt_net.ui.widget.node_editor.config._trans", None):
        assert cfg._t("key", "Default") == "Default"
    with patch("pygpt_net.ui.widget.node_editor.config._trans", return_value="key"):
        assert cfg._t("key", "Default") == "Default"
    with patch("pygpt_net.ui.widget.node_editor.config._trans", return_value=""):
        assert cfg._t("key", "Default") == "Default"
    with patch("pygpt_net.ui.widget.node_editor.config._trans", side_effect=RuntimeError):
        assert cfg._t("key", "Default") == "Default"


def test_editor_config_uses_translation_when_available():
    cfg = EditorConfig()
    with patch("pygpt_net.ui.widget.node_editor.config._trans", return_value="Translated"):
        assert cfg._t("key", "Default") == "Translated"


def test_editor_config_command_and_side_labels_have_stable_english_fallbacks():
    cfg = EditorConfig()
    with patch("pygpt_net.ui.widget.node_editor.config._trans", side_effect=lambda key: key):
        assert cfg.cmd_add_node("Agent") == "Add Agent"
        assert cfg.cmd_move_node() == "Move Node"
        assert cfg.cmd_resize_node() == "Resize Node"
        assert cfg.cmd_connect() == "Connect"
        assert cfg.cmd_delete_connection() == "Delete Connection"
        assert cfg.side_label("input") == "Input"
        assert cfg.side_label("output") == "Output"


def test_editor_config_tooltips_interpolate_runtime_values():
    cfg = EditorConfig()
    with patch("pygpt_net.ui.widget.node_editor.config._trans", side_effect=lambda key: key):
        text = cfg.port_tooltip("Node", "Input", "prompt", "1")
        capacity = cfg.port_capacity_tooltip("2")

    assert "Node" in text
    assert "Input" in text
    assert "prompt" in text
    assert "1" in text
    assert "2" in capacity
