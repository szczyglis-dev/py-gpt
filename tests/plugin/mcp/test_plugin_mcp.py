from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem
from pygpt_net.plugin.mcp import Plugin
from pygpt_net.plugin.mcp.worker import Worker
from tests.mocks import mock_window


def test_mcp_no_active_servers_produces_no_commands(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.set_option_value("servers", [])
    data = {"cmd": []}
    plugin.cmd_syntax(data)
    assert data["cmd"] == []
    assert plugin.tools_index == {}


def test_mcp_cmd_syntax_builds_unique_sanitized_tool_and_index(mock_window):
    plugin = Plugin(window=mock_window)
    server = {
        "active": True,
        "label": "My Server!",
        "server_address": "https://example.test/mcp",
        "authorization": "",
        "allowed_commands": "",
        "disabled_commands": "",
    }
    plugin.set_option_value("servers", [server])
    tool = SimpleNamespace(
        name="search.web",
        description="Search the web",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Query"},
                "limit": {"type": "integer"},
            },
            "required": ["query"],
        },
    )
    plugin._discover_tools_sync = MagicMock(return_value=[(0, "tag", "http", tool, server)])
    data = {"cmd": []}
    plugin.cmd_syntax(data)
    assert data["cmd"] == [{
        "cmd": "My_Server__search_web",
        "instruction": "Search the web (server: My Server!)",
        "params": [
            {"name": "query", "type": "str", "description": "Query [required]"},
            {"name": "limit", "type": "int", "description": "limit"},
        ],
        "enabled": True,
    }]
    assert plugin.tools_index["My_Server__search_web"]["tool_name"] == "search.web"
    assert plugin.tools_index["My_Server__search_web"]["transport"] == "http"


def test_mcp_cmd_syntax_invalidates_cache_when_config_changes(mock_window):
    plugin = Plugin(window=mock_window)
    server = {"active": True, "label": "A", "server_address": "stdio: tool", "authorization": ""}
    plugin.set_option_value("servers", [server])
    plugin._tools_cache = {"old": {"tools": []}}
    plugin._last_config_signature = "old"
    plugin._discover_tools_sync = MagicMock(return_value=[])
    plugin.cmd_syntax({"cmd": []})
    assert plugin._tools_cache == {}
    assert plugin._last_config_signature != "old"


def test_mcp_handle_routes_syntax_and_execute(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.cmd_syntax = MagicMock()
    event = Event()
    event.name = Event.CMD_SYNTAX
    event.data = {"cmd": []}
    event.ctx = CtxItem()
    plugin.handle(event)
    plugin.cmd_syntax.assert_called_once_with(event.data)

    plugin.cmd = MagicMock()
    event.name = Event.CMD_EXECUTE
    event.data = {"commands": [{"cmd": "x", "params": {}}]}
    plugin.handle(event)
    plugin.cmd.assert_called_once_with(event.ctx, event.data["commands"])


def test_mcp_cmd_filters_against_discovery_index_and_routes_worker(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.tools_index = {
        "srv__tool": {"server": {}, "transport": "stdio", "tool_name": "tool"}
    }
    plugin.cmd_prepare = MagicMock()
    plugin.is_async = MagicMock(return_value=False)
    ctx = CtxItem()
    worker = MagicMock()
    fake_mod = ModuleType("pygpt_net.plugin.mcp.worker")
    fake_mod.Worker = MagicMock(return_value=worker)

    with patch.dict("sys.modules", {"pygpt_net.plugin.mcp.worker": fake_mod}):
        plugin.cmd(ctx, [{"cmd": "other", "params": {}}])
        fake_mod.Worker.assert_not_called()
        request = {"cmd": "srv__tool", "params": {"x": 1}}
        plugin.cmd(ctx, [request])

    worker.from_defaults.assert_called_once_with(plugin)
    assert worker.plugin is plugin
    assert worker.cmds == [request]
    assert worker.ctx is ctx
    assert worker.tools_index is plugin.tools_index
    worker.run.assert_called_once_with()


def test_mcp_schema_helpers_cover_supported_json_types(mock_window):
    plugin = Plugin(window=mock_window)
    assert plugin.extract_params(None) == []
    assert plugin.extract_params("a, ,b") == [
        {"name": "a", "type": "str", "description": "a"},
        {"name": "b", "type": "str", "description": "b"},
    ]
    schema = {
        "properties": {
            "s": {"type": "string"},
            "i": {"type": "integer"},
            "n": {"type": "number"},
            "b": {"type": "boolean"},
            "a": {"type": "array"},
            "o": {"type": "object"},
        },
        "required": ["i"],
    }
    params = plugin.extract_params_from_schema(schema)
    assert {p["name"]: p["type"] for p in params} == {
        "s": "str", "i": "int", "n": "float", "b": "bool", "a": "str", "o": "str"
    }
    assert next(p for p in params if p["name"] == "i")["description"] == "[required]"


def test_mcp_csv_transport_and_stdio_helpers(mock_window):
    plugin = Plugin(window=mock_window)
    assert plugin._parse_csv(None) is None
    assert plugin._parse_csv(" a, b, a ") == {"a", "b"}
    assert plugin._detect_transport("stdio: python server.py") == "stdio"
    assert plugin._detect_transport("https://example.test/mcp") == "http"
    assert plugin._detect_transport("https://example.test/sse") == "sse"
    assert plugin._detect_transport("sse+https://example.test") == "sse"
    assert plugin._parse_stdio_command('stdio: python "my server.py" --x 1') == (
        "python", ["my server.py", "--x", "1"]
    )
    with pytest.raises(ValueError):
        plugin._parse_stdio_command("stdio:   ")


def test_mcp_server_tag_headers_slug_and_key_helpers(mock_window):
    plugin = Plugin(window=mock_window)
    assert plugin._make_server_tag({"label": " Label ", "server_address": "x"}, 0) == "Label"
    assert plugin._make_server_tag({"server_address": "stdio: python server.py"}, 1) == "python"
    assert plugin._make_server_tag({"server_address": "https://host.test/path/mcp"}, 2) == "host.test_mcp"
    assert plugin._build_headers({"authorization": "Bearer token"}) == {"Authorization": "Bearer token"}
    assert plugin._build_headers({"authorization": ""}) is None
    assert plugin._slugify(" A weird/tool.name ") == "A_weird_tool_name"
    assert plugin._slugify("") == "srv"
    assert plugin._server_key({"server_address": "https://host.test/mcp?q=1"}) == "http::host.test/mcp"
    assert plugin._server_key({"server_address": "stdio: python x.py"}) == "stdio::python x.py"


def test_mcp_truncate_and_compose_command_names_are_bounded_and_unique(mock_window):
    plugin = Plugin(window=mock_window)
    long = "x" * 100
    truncated = plugin._truncate_with_hash(long, 64)
    assert len(truncated) <= 64
    assert truncated != long
    used = set()
    first = plugin._compose_cmd_name("server", "tool", used)
    used.add(first)
    second = plugin._compose_cmd_name("server", "tool", used)
    assert first == "server__tool"
    assert second == "server__tool-2"
    assert len(plugin._compose_cmd_name("s" * 50, "t" * 50, set())) <= 64


def test_mcp_config_signature_is_deterministic_and_auth_value_is_not_embedded(mock_window):
    plugin = Plugin(window=mock_window)
    active = [(0, {
        "label": "A",
        "server_address": "https://host.test/mcp",
        "authorization": "secret-token",
        "allowed_commands": "b,a",
        "disabled_commands": "x",
    })]
    sig1 = plugin._config_signature(active)
    sig2 = plugin._config_signature(active)
    assert sig1 == sig2
    assert "secret-token" not in sig1
    assert len(sig1) == 64


def test_worker_argument_coercion():
    worker = Worker()
    schema = {
        "properties": {
            "i": {"type": "integer"},
            "n": {"type": "number"},
            "b": {"type": "boolean"},
            "arr": {"type": "array"},
            "obj": {"type": "object"},
            "s": {"type": "string"},
        }
    }
    out = worker._coerce_arguments({
        "i": "2", "n": "2.5", "b": "yes", "arr": "[1, 2]", "obj": '{"x": 1}', "s": 7
    }, schema)
    assert out == {"i": 2, "n": 2.5, "b": True, "arr": [1, 2], "obj": {"x": 1}, "s": 7}
    assert worker._coerce_arguments({"x": 1}, None) == {"x": 1}


def test_worker_extract_structured_result_without_mcp_sdk():
    worker = Worker()
    result = SimpleNamespace(structuredContent={"ż": 1}, content=None)
    text = worker._extract_text_result(result)
    assert '"ż": 1' in text


def test_worker_extract_text_blocks_with_fake_mcp_types():
    worker = Worker()
    class TextContent:
        def __init__(self, text):
            self.text = text
            self.type = "text"
    mcp_mod = ModuleType("mcp")
    mcp_mod.types = SimpleNamespace(TextContent=TextContent)
    result = SimpleNamespace(structuredContent=None, content=[TextContent("hello"), SimpleNamespace(type="image")])
    with patch.dict("sys.modules", {"mcp": mcp_mod}):
        assert worker._extract_text_result(result) == "hello\n[image]"


def test_worker_misc_server_helpers_match_plugin_behavior():
    worker = Worker()
    assert worker._parse_stdio_command("stdio: python x.py --a") == ("python", ["x.py", "--a"])
    assert worker._build_headers({"authorization": "Bearer x"}) == {"Authorization": "Bearer x"}
    assert worker._server_key({"server_address": "https://host.test/mcp"}) == "http::host.test/mcp"


def test_worker_run_uses_mocked_asyncio_without_external_mcp():
    worker = Worker()
    worker._run_async = MagicMock()
    worker.reply_more = MagicMock()
    worker.cleanup = MagicMock()
    with patch("pygpt_net.plugin.mcp.worker.asyncio.run", return_value=[{"result": "ok"}]) as run:
        worker.run()
    run.assert_called_once()
    worker.reply_more.assert_called_once_with([{"result": "ok"}])
    worker.cleanup.assert_called_once_with()
