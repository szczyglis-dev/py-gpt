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


def test_cmd_apply_normalizes_invalid_value_and_updates_all_widgets():
    handler, cfg = _cmd()
    option = {"value": None}

    handler.apply("parent", "command", option)

    assert option["value"] == {"enabled": False, "instruction": "", "params": []}
    assert cfg.params.items == []
    cfg.params.model.updateData.assert_called_once_with([])
    cfg.enabled.box.setChecked.assert_called_once_with(False)
    cfg.instruction.setText.assert_called_once_with("")


def test_cmd_apply_fills_missing_defaults_without_replacing_dict():
    handler, cfg = _cmd()
    value = {"enabled": True, "params": [{"name": "x"}]}
    option = {"value": value}

    handler.apply("parent", "command", option)

    assert option["value"] is value
    assert value["instruction"] == ""
    cfg.params.model.updateData.assert_called_once_with([{"name": "x"}])
    cfg.enabled.box.setChecked.assert_called_once_with(True)


def test_cmd_apply_row_accepts_base_or_params_key():
    handler, cfg = _cmd()

    handler.apply_row("parent", "command.params", {"params": {"x": 1}}, 3)

    cfg.params.update_item.assert_called_once_with(3, {"x": 1})


def test_cmd_get_value_reads_widget_state():
    handler, cfg = _cmd()
    cfg.enabled.box.isChecked.return_value = True
    cfg.instruction.toPlainText.return_value = "do it"
    cfg.params.model.items = [{"name": "p"}]

    assert handler.get_value("parent", "command", {}) == {
        "enabled": True,
        "instruction": "do it",
        "params": [{"name": "p"}],
    }


def test_cmd_to_options_converts_dict_and_cmd_schemas_and_preserves_explicit_labels():
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

    cmd_result = handler.to_options("root", {
        "type": "cmd",
        "params_keys": {
            "path": "text",
            "count": {"type": "int"},
        },
    })
    assert cmd_result["path"] == {"label": "dictionary.cmd.param.path", "type": "text"}
    assert cmd_result["count"]["label"] == "dictionary.cmd.param.count"


def test_cmd_to_options_returns_empty_for_unsupported_or_empty_schema():
    handler, _ = _cmd()

    assert handler.to_options("root", {"type": "dict"}) == {}
    assert handler.to_options("root", {"type": "cmd"}) == {}
    assert handler.to_options("root", {"type": "other"}) is None
