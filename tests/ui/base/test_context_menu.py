from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.ui.base.context_menu import ContextMenu


def test_zoom_menu_font_size_actions_change_by_two(qapp):
    callback = MagicMock()
    menu_builder = ContextMenu()

    with patch("pygpt_net.ui.base.context_menu.trans", side_effect=lambda key: key):
        menu = menu_builder.get_zoom_menu(None, "font_size", 12, callback)

    actions = menu.actions()
    assert len(actions) == 2
    actions[0].trigger()
    actions[1].trigger()
    assert [call.args[0] for call in callback.call_args_list] == [14, 10]


def test_zoom_menu_scale_actions_change_by_tenth(qapp):
    callback = MagicMock()
    menu_builder = ContextMenu()

    with patch("pygpt_net.ui.base.context_menu.trans", side_effect=lambda key: key):
        menu = menu_builder.get_zoom_menu(None, "zoom", 1.0, callback)

    actions = menu.actions()
    actions[0].trigger()
    actions[1].trigger()
    assert callback.call_args_list[0].args[0] == 1.1
    assert callback.call_args_list[1].args[0] == 0.9


def test_zoom_menu_unknown_type_has_no_actions(qapp):
    with patch("pygpt_net.ui.base.context_menu.trans", side_effect=lambda key: key):
        menu = ContextMenu().get_zoom_menu(None, "unknown", 1.0, MagicMock())
    assert menu.actions() == []


def test_copy_to_menu_routes_to_all_available_targets(qapp):
    controller = MagicMock()
    interpreter = MagicMock()
    translator = MagicMock()
    tabs = [SimpleNamespace(title="Notes A", data_id="a"), SimpleNamespace(title="Notes B", data_id="b")]
    core_tabs = MagicMock()
    core_tabs.get_tabs_by_type.return_value = tabs
    window = SimpleNamespace(
        controller=controller,
        tools={"interpreter": interpreter, "translator": translator},
        core=SimpleNamespace(tabs=core_tabs),
    )

    with patch("pygpt_net.ui.base.context_menu.trans", side_effect=lambda key: key):
        menu = ContextMenu(window).get_copy_to_menu(None, "hello")

    non_separators = [a for a in menu.actions() if not a.isSeparator()]
    assert len(non_separators) == 8
    for action in non_separators:
        action.trigger()

    controller.chat.common.append_to_input.assert_called_once_with("hello")
    controller.calendar.note.append_text.assert_called_once_with("hello")
    controller.notepad.append_text.assert_any_call("hello", "a")
    controller.notepad.append_text.assert_any_call("hello", "b")
    interpreter.append_to_edit.assert_called_once_with("hello")
    interpreter.append_to_input.assert_called_once_with("hello")
    translator.append_content.assert_any_call("left", "hello")
    translator.append_content.assert_any_call("right", "hello")
    core_tabs.get_tabs_by_type.assert_called_once_with(Tab.TAB_NOTEPAD)


def test_copy_to_menu_respects_exclusions(qapp):
    window = SimpleNamespace(
        controller=MagicMock(),
        tools={"interpreter": MagicMock(), "translator": MagicMock()},
        core=SimpleNamespace(tabs=MagicMock()),
    )
    window.core.tabs.get_tabs_by_type.return_value = [SimpleNamespace(title="N", data_id="n")]

    excluded = ["input", "calendar", "notepad", "interpreter_edit", "translator_right"]
    with patch("pygpt_net.ui.base.context_menu.trans", side_effect=lambda key: key):
        menu = ContextMenu(window).get_copy_to_menu(None, "x", excluded=excluded)

    labels = [a.text() for a in menu.actions() if not a.isSeparator()]
    assert labels == [
        "text.context_menu.copy_to.python.input",
        "text.context_menu.copy_to.translator_left",
    ]
