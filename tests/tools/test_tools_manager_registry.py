from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.tools import Tools


def _tool(tool_id, **overrides):
    tool = MagicMock()
    tool.id = tool_id
    tool.setup_menu.return_value = {}
    tool.get_lang_mappings.return_value = {}
    for key, value in overrides.items():
        setattr(tool, key, value)
    return tool


def test_tools_register_attaches_window_and_replaces_same_id():
    window = object()
    manager = Tools(window)
    first = _tool("x")
    second = _tool("x")

    manager.register(first)
    manager.register(second)

    assert manager.get("x") is second
    assert manager.get("missing") is None
    second.attach.assert_called_once_with(window)
    assert manager.get_all() == {"x": second}


def test_tools_setup_runs_dialogs_tools_theme_and_marks_initialized():
    manager = Tools(object())
    a, b = _tool("a"), _tool("b")
    manager.tools = {"a": a, "b": b}
    manager.setup_dialogs = MagicMock()
    manager.setup_theme = MagicMock()

    manager.setup()

    manager.setup_dialogs.assert_called_once_with()
    a.setup.assert_called_once_with()
    b.setup.assert_called_once_with()
    manager.setup_theme.assert_called_once_with()
    assert manager.initialized is True


def test_tools_lifecycle_fans_out_to_every_tool():
    manager = Tools(object())
    a, b = _tool("a"), _tool("b")
    manager.tools = {"a": a, "b": b}

    manager.post_setup()
    manager.on_update()
    manager.on_post_update()
    manager.on_exit()
    manager.on_reload()
    manager.setup_dialogs()

    for tool in (a, b):
        tool.post_setup.assert_called_once_with()
        tool.on_update.assert_called_once_with()
        tool.on_post_update.assert_called_once_with()
        tool.on_exit.assert_called_once_with()
        tool.on_reload.assert_called_once_with()
        tool.setup_dialogs.assert_called_once_with()


def test_tools_handle_stops_dispatch_after_event_is_stopped():
    manager = Tools(object())
    event = SimpleNamespace(stop=False)
    first = _tool("first")
    second = _tool("second")

    def stop_event(_event):
        _event.stop = True

    first.handle.side_effect = stop_event
    manager.tools = {"first": first, "second": second}

    manager.handle(event)

    first.handle.assert_called_once_with(event)
    second.handle.assert_not_called()


def test_tools_handle_dispatches_to_all_when_event_remains_active():
    manager = Tools(object())
    event = SimpleNamespace(stop=False)
    first, second = _tool("first"), _tool("second")
    manager.tools = {"first": first, "second": second}

    manager.handle(event)

    first.handle.assert_called_once_with(event)
    second.handle.assert_called_once_with(event)


def test_tools_setup_menu_actions_prefixes_keys_and_ignores_non_dict_results():
    manager = Tools(object())
    a = _tool("a")
    b = _tool("b")
    c = _tool("c")
    action_a = object()
    action_b = object()
    a.setup_menu.return_value = {"alpha": action_a}
    b.setup_menu.return_value = {"beta": action_b}
    c.setup_menu.return_value = ["not", "a", "dict"]
    manager.tools = {"a": a, "b": b, "c": c}

    assert manager.setup_menu_actions() == {
        "tools.alpha": action_a,
        "tools.beta": action_b,
    }


def test_tools_setup_theme_is_noop_before_initialization_and_fans_out_after():
    manager = Tools(object())
    tool = _tool("x")
    manager.tools = {"x": tool}

    manager.setup_theme()
    tool.setup_theme.assert_not_called()

    manager.initialized = True
    manager.setup_theme()
    tool.setup_theme.assert_called_once_with()


def test_tools_get_instance_returns_first_non_none_result():
    manager = Tools(object())
    first, second, third = _tool("a"), _tool("b"), _tool("c")
    instance = object()
    first.get_instance.return_value = None
    second.get_instance.return_value = instance
    third.get_instance.return_value = object()
    manager.tools = {"a": first, "b": second, "c": third}

    assert manager.get_instance("viewer", "id-1") is instance
    first.get_instance.assert_called_once_with("viewer", "id-1")
    second.get_instance.assert_called_once_with("viewer", "id-1")
    third.get_instance.assert_not_called()


def test_tools_get_lang_mappings_merges_sections_without_overwriting_existing_entries():
    manager = Tools(object())
    a, b, c = _tool("a"), _tool("b"), _tool("c")
    a.get_lang_mappings.return_value = {
        "menu.text": {"a": "key.a"},
        "menu.tooltip": {"x": "tip.x"},
    }
    b.get_lang_mappings.return_value = {
        "menu.text": {"b": "key.b"},
    }
    c.get_lang_mappings.return_value = None
    manager.tools = {"a": a, "b": b, "c": c}

    assert manager.get_lang_mappings() == {
        "menu.text": {"a": "key.a", "b": "key.b"},
        "menu.tooltip": {"x": "tip.x"},
    }
