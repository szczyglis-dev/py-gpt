import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pygpt_net


def load(name, relpath):
    path = Path(pygpt_net.__file__).parent / "provider" / "api" / "anthropic" / relpath
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tools_mod = load("anthropic_tools_under_test", "tools.py")
utils_mod = load("anthropic_utils_under_test", "utils.py")
vision_mod = load("anthropic_vision_under_test", "vision.py")
computer_mod = load("anthropic_computer_under_test", "computer.py")


def test_as_int_coercion():
    assert utils_mod.as_int(None) is None
    assert utils_mod.as_int(7) == 7
    assert utils_mod.as_int("8") == 8
    assert utils_mod.as_int("8.9") == 8
    assert utils_mod.as_int("bad") is None


def test_tools_sanitize_schema_removes_unsupported_and_normalizes_nested_types():
    tools = tools_mod.Tools()
    schema = {
        "$schema": "x",
        "type": ["null", "OBJECT"],
        "properties": {
            "name": {"type": "STRING", "enum": ["a", "b"], "examples": ["a"]},
            "count": {"type": "integer", "enum": [1, 2]},
            "items": {"type": "array", "items": [{"type": "string"}]},
        },
        "required": ["name"],
        "additionalProperties": False,
    }
    out = tools._sanitize_schema(schema)
    assert out["type"] == "object"
    assert "$schema" not in out and "additionalProperties" not in out
    assert out["properties"]["name"] == {"type": "string", "enum": ["a", "b"]}
    assert "enum" not in out["properties"]["count"]
    assert out["properties"]["items"]["items"] == {"type": "string"}
    assert out["required"] == ["name"]


def test_tools_sanitize_schema_handles_inference_invalid_required_and_scalars():
    tools = tools_mod.Tools()
    assert tools._sanitize_schema([]) == {}
    assert tools._sanitize_schema("x") == "x"
    assert tools._sanitize_schema({"properties": {"x": {"enum": ["a"]}}, "required": []}) == {
        "properties": {"x": {"enum": ["a"], "type": "string"}},
        "type": "object",
    }
    assert tools._sanitize_schema({"items": "bad"}) == {"items": {"type": "string"}, "type": "array"}


def test_tools_prepare_skips_invalid_functions_and_mocks_no_external_api():
    tools = tools_mod.Tools()
    funcs = [
        {"name": "", "desc": "skip"},
        {"name": "search", "desc": "Search", "params": '{"type":"object","properties":{"q":{"type":"string"}}}'},
        {"name": "bad", "params": "not-json", "defer_loading": True},
    ]
    out = tools.prepare(None, funcs)
    assert [x["name"] for x in out] == ["search", "bad"]
    assert out[0]["input_schema"]["properties"]["q"]["type"] == "string"
    assert out[1]["input_schema"] == {"type": "object"}
    assert out[1]["defer_loading"] is True
    assert tools.prepare(None, None) == []


def test_tools_merge_dedup_by_name_mcp_and_type():
    tools = tools_mod.Tools()
    primary = [
        {"name": "a", "type": "function"},
        {"type": "mcp_toolset", "mcp_server_name": "srv"},
        {"type": "web_search"},
    ]
    secondary = [
        {"name": "a", "type": "other"},
        {"name": "b"},
        {"type": "mcp_toolset", "mcp_server_name": "srv"},
        {"type": "web_search"},
    ]
    out = tools.merge_tools_dedup(primary, secondary)
    assert out == [primary[0], primary[1], primary[2], secondary[1]]


def test_tools_get_all_tools_combines_remote_tools():
    remote = MagicMock()
    remote.build_remote_tools.return_value = [{"name": "remote"}]
    window = SimpleNamespace(core=SimpleNamespace(api=SimpleNamespace(anthropic=SimpleNamespace(remote_tools=remote))))
    tools = tools_mod.Tools(window)
    out = tools.get_all_tools(None, [{"name": "local", "params": "{}"}])
    assert [x["name"] for x in out] == ["local", "remote"]
    remote.build_remote_tools.assert_called_once_with(None)


def attachment(path):
    return SimpleNamespace(path=str(path), consumed=False)


def test_vision_build_blocks_encodes_only_existing_images(tmp_path):
    png = tmp_path / "a.png"; png.write_bytes(b"abc")
    txt = tmp_path / "b.txt"; txt.write_text("x")
    missing = tmp_path / "missing.jpg"
    vision = vision_mod.Vision()
    images = {"a": attachment(png), "b": attachment(txt), "c": attachment(missing)}
    blocks = vision.build_blocks("ignored", images)
    assert blocks == [{
        "type": "image",
        "source": {"type": "base64", "media_type": "image/png", "data": "YWJj"},
    }]
    assert vision.get_attachments() == {"a": str(png)}
    assert images["a"].consumed is True
    assert images["b"].consumed is False


def test_vision_helpers_reset_and_mime_detection():
    vision = vision_mod.Vision()
    for path, mime in [
        ("a.JPG", "image/jpeg"), ("a.png", "image/png"), ("a.gif", "image/gif"),
        ("a.webp", "image/webp"), ("a.bmp", "image/bmp"), ("a.tiff", "image/tiff"),
        ("a.unknown", "image/jpeg"),
    ]:
        assert vision._guess_mime(path) == mime
    assert vision.is_image("x.WEBP") is True
    assert vision.is_image("x.txt") is False
    vision.window = SimpleNamespace(core=SimpleNamespace(filesystem=SimpleNamespace(make_local_list=lambda paths: ["local:" + p for p in paths])))
    vision.attachments = {"x": "p"}; vision.urls = ["u"]; vision.input_tokens = 5
    ctx = SimpleNamespace(images=[])
    vision.append_images(ctx)
    assert ctx.images == ["local:p"]
    vision.reset_tokens(); assert vision.get_used_tokens() == 0
    vision.reset()
    assert vision.get_attachments() == {} and vision.get_urls() == [] and vision.get_used_tokens() == 0


def test_computer_safe_json_prune_id_and_ctx_memory(monkeypatch):
    comp = computer_mod.Computer()
    assert comp._safe_json_loads(None) is None
    assert comp._safe_json_loads(" ") is None
    assert comp._safe_json_loads('{"a":1}') == {"a": 1}
    assert comp._safe_json_loads('{"a":1') == {"a": 1}
    assert comp._safe_json_loads("bad") is None
    assert comp._prune_none({"a": 1, "b": None}) == {"a": 1}
    assert comp._prune_none(None) is None
    monkeypatch.setattr(computer_mod.time, "time", lambda: 1700000000.123)
    assert comp._gen_id("x") == "x-1700000000123"

    ctx = SimpleNamespace(extra=None)
    mem = comp._ensure_ctx_memory(ctx)
    assert mem == {"buffers": {}, "index_to_id": {}, "active_ids": []}
    ctx.extra["anthropic_computer"] = {"active_ids": "bad"}
    mem = comp._ensure_ctx_memory(ctx)
    assert mem == {"buffers": {}, "index_to_id": {}, "active_ids": []}


def test_computer_coordinate_key_and_scroll_normalization():
    comp = computer_mod.Computer()
    assert comp._extract_xy({"coordinate": [10, "20"]}) == (10, 20)
    assert comp._extract_xy({"x": "3", "y": 4}) == (3, 4)
    assert comp._extract_dxdy({"delta": [5, -6]}) == (5, -6)
    assert comp._parse_keys_list("CTRL+SHIFT A") == ["CTRL", "SHIFT", "A"]
    assert comp._parse_keys_list(["CTRL", 1, "A"]) == ["CTRL", 1, "A"]

    name, args = comp._retarget_function_name_and_args("right_click", {"coordinate": [1, 2]})
    assert name == "mouse_click"
    assert args["button"] == "right" and args["num_clicks"] == 1
    assert args["x"] == 1 and args["y"] == 2

    filtered = comp._filter_args_for_plugin("mouse_scroll", {"x": 1, "dy": 2, "unit": "pixels", "junk": 9})
    assert filtered == {"x": 1, "dy": 2, "unit": "px"}
    filtered = comp._filter_args_for_plugin("unknown", {"coordinate": [1, 2], "action": "x", "foo": 3})
    assert filtered == {"foo": 3, "x": 1, "y": 2}


def test_computer_build_call_filters_none_and_adds_no_screenshot():
    comp = computer_mod.Computer()
    call = comp._build_call("id", "call", "mouse_click", {"x": 1, "y": 2, "button": None, "junk": 9})
    assert call["id"] == "id" and call["call_id"] == "call" and call["type"] == "computer_call"
    assert call["function"]["name"] == "mouse_click"
    args = json.loads(call["function"]["arguments"])
    assert args == {"x": 1, "y": 2, "no_screenshot": True}
    shot = comp._build_call("id", "call", "get_screenshot", {})
    assert json.loads(shot["function"]["arguments"]) == {}
