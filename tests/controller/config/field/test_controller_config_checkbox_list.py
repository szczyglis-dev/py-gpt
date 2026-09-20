from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.controller.config.field.checkbox_list import CheckboxList


def _handler(boxes=None):
    window = MagicMock()
    entry = SimpleNamespace(boxes=boxes or {})
    window.ui.config = {"parent": {"option": entry}}
    return CheckboxList(window), window, entry


def test_checkbox_list_apply_updates_only_changed_boxes():
    a = MagicMock()
    b = MagicMock()
    c = MagicMock()
    a.isChecked.return_value = False
    b.isChecked.return_value = True
    c.isChecked.return_value = False
    handler, _, _ = _handler({"a": a, "b": b, "c": c, "none": None})

    handler.apply("parent", "option", {"value": " a, b "})

    a.setChecked.assert_called_once_with(True)
    b.setChecked.assert_not_called()
    c.setChecked.assert_not_called()


def test_checkbox_list_apply_ignores_missing_value_and_missing_ui_entry():
    box = MagicMock()
    handler, _, _ = _handler({"a": box})

    handler.apply("parent", "option", {})
    handler.apply("missing", "option", {"value": "a"})
    handler.apply("parent", "missing", {"value": "a"})

    box.setChecked.assert_not_called()


def test_checkbox_list_apply_treats_non_string_value_as_empty_selection():
    box = MagicMock()
    box.isChecked.return_value = True
    handler, _, _ = _handler({"a": box})

    handler.apply("parent", "option", {"value": ["a"]})

    box.setChecked.assert_called_once_with(False)


def test_checkbox_list_on_update_calls_registered_hook_and_logs_hook_errors():
    handler, window, _ = _handler()
    hook = MagicMock()
    window.ui.has_hook.return_value = True
    window.ui.get_hook.return_value = hook

    handler.on_update("parent", "option", {}, True)
    hook.assert_called_once_with("option", True, "bool_list")

    hook.reset_mock()
    error = RuntimeError("hook")
    hook.side_effect = error
    handler.on_update("parent", "option", {}, False)
    window.core.debug.log.assert_called_once_with(error)


def test_checkbox_list_on_update_skips_hooks_when_disabled():
    handler, window, _ = _handler()

    handler.on_update("parent", "option", {}, True, hooks=False)

    window.ui.has_hook.assert_not_called()


def test_checkbox_list_select_all_toggles_between_all_selected_and_unselected():
    a = MagicMock()
    b = MagicMock()
    a.isChecked.return_value = True
    b.isChecked.return_value = False
    handler, _, _ = _handler({"a": a, "b": b, "none": None})

    handler.on_select_all("parent", "option", {})
    a.setChecked.assert_called_once_with(True)
    b.setChecked.assert_called_once_with(True)

    a.reset_mock()
    b.reset_mock()
    a.isChecked.return_value = True
    b.isChecked.return_value = True
    handler.on_select_all("parent", "option", {})
    a.setChecked.assert_called_once_with(False)
    b.setChecked.assert_called_once_with(False)


def test_checkbox_list_get_value_returns_checked_names_in_mapping_order():
    a = MagicMock()
    b = MagicMock()
    c = MagicMock()
    a.isChecked.return_value = True
    b.isChecked.return_value = False
    c.isChecked.return_value = True
    handler, _, _ = _handler({"a": a, "b": b, "c": c, "none": None})

    assert handler.get_value("parent", "option", {}) == "a,c"
    assert handler.get_value("missing", "option", {}) == ""


def test_checkbox_list_update_list_delegates_to_widget():
    handler, _, entry = _handler()
    entry.update_boxes_list = MagicMock()
    items = [{"id": "a"}]

    handler.update_list("parent", "option", items)

    entry.update_boxes_list.assert_called_once_with(items)
