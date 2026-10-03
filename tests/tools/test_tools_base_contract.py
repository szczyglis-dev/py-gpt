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


def test_tool_capabilities_and_legacy_aliases_share_one_policy():
    tool = BaseTool()
    tool.id = 'test'
    tool.window = SimpleNamespace(controller=SimpleNamespace(tabs=MagicMock()))
    tool.window.controller.tabs.get_first_tab_by_tool.return_value = None
    assert not tool.can_add_tab()
    tool.allow_tab = True
    tool.multi_tab = False
    assert tool.can_add_tab()
    tool.window.controller.tabs.get_first_tab_by_tool.return_value = object()
    assert not tool.can_add_tab()
    assert tool.can_open_tab()
    tool.multi_tab = True
    assert tool.can_add_tab()
    tool.has_tab = False
    assert not tool.allow_tab
    tool.single_instance = True
    assert not tool.multi_tab
    assert tool.resolve_dialog_id('first') == 'first'
    assert tool.resolve_dialog_id('second') == 'first'
    tool.multi_dialog = True
    assert tool.resolve_dialog_id('second') == 'second'
    tool.allow_dialog = False
    assert tool.resolve_dialog_id('third') is None
    assert not tool.allows_multiple_dialogs()


def test_menu_policy_routes_each_action_with_and_without_existing_tab():
    from pygpt_net.tools.base import ToolMenuAction
    tool = BaseTool()
    tool.open_tab = MagicMock()
    tool.open_dialog = MagicMock()
    tool.existing_tab = MagicMock()
    for policy, exists, target in [
        (ToolMenuAction.ALWAYS_DIALOG, False, 'dialog'),
        (ToolMenuAction.ALWAYS_TAB, True, 'tab'),
        (ToolMenuAction.DIALOG_IF_TAB_EXISTS, True, 'dialog'),
        (ToolMenuAction.DIALOG_IF_TAB_EXISTS, False, 'tab'),
        (ToolMenuAction.TAB_IF_EXISTS, True, 'tab'),
        (ToolMenuAction.TAB_IF_EXISTS, False, 'dialog'),
    ]:
        tool.on_menu_click = policy
        tool.existing_tab.return_value = object() if exists else None
        tool.open_tab.reset_mock(); tool.open_dialog.reset_mock()
        tool.on_menu_action()
        getattr(tool, 'open_' + target).assert_called_once_with()
        getattr(tool, 'open_' + ('dialog' if target == 'tab' else 'tab')).assert_not_called()
