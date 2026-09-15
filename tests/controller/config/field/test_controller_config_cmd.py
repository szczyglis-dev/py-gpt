from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.controller.config.field.cmd import Cmd


def _cmd():
    window = MagicMock()
    cfg = SimpleNamespace(
        params=SimpleNamespace(items=[], model=MagicMock(), update_item=MagicMock()),
        enabled=SimpleNamespace(box=MagicMock()),
        instruction=MagicMock(),
    )
    window.ui.config = {"parent": {"command": cfg}}
    return Cmd(window), cfg


def test_cmd_apply_invalid_value_disables_tool_without_mutating_metadata():
    handler, cfg = _cmd()
    option = {"value": None}

    handler.apply("parent", "command", option)

    assert option["value"] is None
    cfg.enabled.box.setChecked.assert_called_once_with(False)
    cfg.params.model.updateData.assert_not_called()
    cfg.instruction.setText.assert_not_called()


def test_cmd_apply_reads_only_enabled_flag_from_tool_value():
    handler, cfg = _cmd()
    value = {"enabled": True, "instruction": "fixed", "params": [{"name": "x"}]}
    option = {"value": value}

    handler.apply("parent", "command", option)

    assert option["value"] is value
    assert value == {"enabled": True, "instruction": "fixed", "params": [{"name": "x"}]}
    cfg.enabled.box.setChecked.assert_called_once_with(True)
    cfg.params.model.updateData.assert_not_called()


def test_cmd_apply_row_is_noop_for_read_only_tool_parameters():
    handler, cfg = _cmd()

    assert handler.apply_row("parent", "command.params", {"params": {"x": 1}}, 3) is None

    cfg.params.update_item.assert_not_called()


def test_cmd_get_value_returns_enabled_state_only():
    handler, cfg = _cmd()
    cfg.enabled.box.isChecked.return_value = True

    assert handler.get_value("parent", "command", {}) is True


def test_cmd_to_options_converts_dict_but_not_cmd_schema():
    handler, _ = _cmd()

    dict_result = handler.to_options("root", {
        "type": "dict",
        "keys": {
            "a": "text",
            "b": {"type": "int"},
            "c": {"type": "bool", "label": "custom"},
        },
    })
    assert dict_result["a"] == {"label": "root.a", "type": "text"}
    assert dict_result["b"]["label"] == "root.b"
    assert dict_result["c"]["label"] == "custom"

    assert handler.to_options("root", {
        "type": "cmd",
        "params_keys": {
            "path": "text",
            "count": {"type": "int"},
        },
    }) == {}


def test_cmd_to_options_returns_empty_for_unsupported_or_empty_schema():
    handler, _ = _cmd()

    assert handler.to_options("root", {"type": "dict"}) == {}
    assert handler.to_options("root", {"type": "cmd"}) == {}
    assert handler.to_options("root", {"type": "other"}) == {}
