from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.tools.base import BaseTool, TabWidget


def test_base_tool_defaults_and_noop_contract():
    tool = BaseTool()

    assert tool.window is None
    assert tool.id == ""
    assert tool.has_tab is False
    assert tool.tab_title == ""
    assert tool.tab_icon == ":/icons/build.svg"
    assert tool.setup_menu() == {}
    assert tool.get_instance("anything") is None
    assert tool.as_tab(object()) is None
    assert tool.get_lang_mappings() == {}

    # Explicitly exercise lifecycle hooks to protect the base no-op contract.
    assert tool.setup() is None
    assert tool.post_setup() is None
    assert tool.on_update() is None
    assert tool.on_post_update() is None
    assert tool.on_exit() is None
    assert tool.on_reload() is None
    assert tool.handle(SimpleNamespace()) is None
    assert tool.setup_dialogs() is None
    assert tool.setup_theme() is None


def test_base_tool_attach_sets_window_reference():
    tool = BaseTool()
    window = object()
    tool.attach(window)
    assert tool.window is window


def test_tab_widget_from_tool_propagates_tool_and_window(qapp):
    widget = TabWidget()
    tool = SimpleNamespace(window=object())

    widget.from_tool(tool)
    assert widget.tool is tool
    assert widget.window is tool.window

    widget.from_tool(None)
    assert widget.tool is None
    assert widget.window is None


def test_tab_widget_setup_uses_tool_layout(qapp):
    widget = TabWidget()
    layout = MagicMock()
    widget.tool = MagicMock()
    widget.tool.setup.return_value = layout
    widget.setLayout = MagicMock()

    widget.setup()

    widget.tool.setup.assert_called_once_with(all=False)
    widget.setLayout.assert_called_once_with(layout)


def test_tab_widget_on_delete_calls_optional_tool_hook(qapp):
    widget = TabWidget()
    tool = MagicMock()
    widget.tool = tool

    widget.on_delete()
    tool.on_delete.assert_called_once_with()

    widget.tool = SimpleNamespace()
    assert widget.on_delete() is None
