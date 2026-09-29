from types import SimpleNamespace

from pygpt_net.provider.loaders.base import BaseLoader


def test_base_loader_initial_state_and_attach():
    loader = BaseLoader()
    assert loader.window is None
    assert loader.id == ""
    assert loader.name == ""
    assert loader.extensions == []
    assert loader.type == ["file"]
    assert loader.allow_compiled is True
    window = object()
    loader.attach_window(window)
    assert loader.window is window


def test_set_args_explode_and_get_args_override_defaults():
    loader = BaseLoader()
    loader.init_args = {"a": 1, "b": 2}
    loader.set_args({"b": 20, "extra": 99})
    assert loader.args == {"b": 20, "extra": 99}
    assert loader.explode(" a, b ,c ") == ["a", "b", "c"]
    assert loader.explode("") == []
    assert loader.get_args() == {"a": 1, "b": 20}


def test_prepare_args_and_external_id():
    loader = BaseLoader()
    payload = {"url": "https://example.com", "x": 1}
    assert loader.prepare_args(**payload) == payload
    assert loader.get_external_id(payload) == "https://example.com"
    assert loader.get_external_id({}) == ""


def test_attachment_and_get_base_contract():
    loader = BaseLoader()
    assert loader.is_supported_attachment("file.txt") is False
    assert loader.get() is None
