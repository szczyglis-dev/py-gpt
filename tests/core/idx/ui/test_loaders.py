from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.core.idx.ui.loaders import Loaders


def _node(value):
    node = MagicMock()
    node.text.return_value = value
    return node


def test_handle_options_converts_loader_args_and_config_values():
    select = SimpleNamespace(get_value=lambda: "demo")
    indexing = SimpleNamespace(
        get_external_instructions=lambda: {"demo": {"args": {
            "count": {"type": "int"},
            "ratio": {"type": "float"},
            "enabled": {"type": "bool"},
            "tags": {"type": "list"},
            "mapping": {"type": "dict"},
        }}},
        get_external_config=lambda: {"demo": {
            "limit": {"type": "int"},
        }},
    )
    nodes = {
        "opt.demo.count": _node("3"),
        "opt.demo.ratio": _node("1.5"),
        "opt.demo.enabled": _node("true"),
        "opt.demo.tags": _node("a,b"),
        "opt.demo.mapping": _node('{"x": 1}'),
        "cfg.demo.limit": _node("9"),
    }
    window = SimpleNamespace(
        core=SimpleNamespace(idx=SimpleNamespace(indexing=indexing), debug=SimpleNamespace(log=MagicMock())),
        ui=SimpleNamespace(nodes=nodes, dialogs=SimpleNamespace(alert=MagicMock())),
    )

    ok, loader, params, config = Loaders(window).handle_options(select, "opt", "cfg")

    assert ok is True
    assert loader == "demo"
    assert params == {"count": 3, "ratio": 1.5, "enabled": True, "tags": ["a", "b"], "mapping": {"x": 1}}
    assert config == {"limit": 9}


def test_handle_options_returns_false_without_selected_loader():
    select = SimpleNamespace(get_value=lambda: "")
    ok, loader, params, config = Loaders(SimpleNamespace()).handle_options(select, "opt", "cfg")
    assert (ok, loader, params, config) == (False, "", {}, {})


def test_handle_options_reports_conversion_errors():
    select = SimpleNamespace(get_value=lambda: "demo")
    indexing = SimpleNamespace(
        get_external_instructions=lambda: {"demo": {"args": {"count": {"type": "int"}}}},
        get_external_config=lambda: {},
    )
    debug = SimpleNamespace(log=MagicMock())
    alert = MagicMock()
    window = SimpleNamespace(
        core=SimpleNamespace(idx=SimpleNamespace(indexing=indexing), debug=debug),
        ui=SimpleNamespace(nodes={"opt.demo.count": _node("nope")}, dialogs=SimpleNamespace(alert=alert)),
    )

    ok, _, params, _ = Loaders(window).handle_options(select, "opt", "cfg")

    assert ok is True
    assert params == {}
    debug.log.assert_called_once()
    alert.assert_called_once()
