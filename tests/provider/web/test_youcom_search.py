#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.05 18:00:00                  #
# ================================================== #

import json
from unittest.mock import MagicMock

from pygpt_net.provider.web.youcom_search import YouComSearch


def make_plugin(options: dict = None) -> MagicMock:
    """Build a minimal plugin mock with options dict"""
    if options is None:
        options = {}
    plugin = MagicMock()

    def add_option(name, type=None, **kwargs):
        option = dict(kwargs)
        option["id"] = name
        option["type"] = type
        options[name] = option
        return option

    def get_option_value(name):
        return options.get(name)

    plugin.add_option = add_option
    plugin.get_option_value = get_option_value
    plugin.options = options
    return plugin


def make_response(status_code: int = 200, body: str = "", content_type: str = "application/json") -> MagicMock:
    """Build a minimal HTTP response mock"""
    response = MagicMock()
    response.status_code = status_code
    response.text = body
    response.headers = {"Content-Type": content_type}
    return response


def mcp_body(results: dict) -> str:
    """Build a JSON-RPC tools/call response body with given results"""
    return json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({"results": results}),
                }
            ]
        },
    })


def test_options():
    """Test provider options"""
    plugin = make_plugin()
    provider = YouComSearch(plugin=plugin)
    provider.init_options()
    assert "youcom_api_key" in plugin.options
    assert "youcom_endpoint" in plugin.options
    assert plugin.options["youcom_endpoint"]["value"] == "https://api.you.com/mcp?profile=free"


def test_ids():
    """Test provider id and type"""
    plugin = make_plugin()
    provider = YouComSearch(plugin=plugin)
    assert provider.id == "youcom_search"
    assert provider.name == "You.com"
    assert provider.type == ["search_engine"]


def test_search_parses_urls():
    """Test parsing URLs from MCP response"""
    plugin = make_plugin()
    provider = YouComSearch(plugin=plugin)
    body = mcp_body({
        "web": [
            {"url": "https://example.com/1", "title": "one"},
            {"url": "https://example.com/2", "title": "two"},
        ],
    })
    provider._fetch = MagicMock(return_value=[
        "https://example.com/1",
        "https://example.com/2",
    ])
    # direct parse check
    data = provider._parse_response(make_response(body=body))
    urls = [item.get("url") for item in data["results"]["web"]]
    assert urls == ["https://example.com/1", "https://example.com/2"]


def test_parse_response_sse():
    """Test parsing SSE stream response"""
    plugin = make_plugin()
    provider = YouComSearch(plugin=plugin)
    body = mcp_body({"web": [{"url": "https://example.com/sse"}]})
    sse = 'event: message\n' + "data: " + body + "\n\n"
    data = provider._parse_response(make_response(body=sse, content_type="text/event-stream"))
    assert data["results"]["web"][0]["url"] == "https://example.com/sse"


def test_parse_response_error_envelope():
    """Test parsing JSON-RPC error envelope"""
    plugin = make_plugin()
    provider = YouComSearch(plugin=plugin)
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "error": {"code": -32000, "message": "err"}})
    data = provider._parse_response(make_response(body=body))
    assert data == {}


def test_fetch_request_construction(monkeypatch):
    """Test request construction: endpoint, payload, headers"""
    plugin = make_plugin({
        "youcom_endpoint": "https://api.you.com/mcp?profile=free",
        "youcom_api_key": "",
    })
    provider = YouComSearch(plugin=plugin)
    captured = {}

    def fake_post(endpoint, json=None, headers=None, timeout=None):
        captured["endpoint"] = endpoint
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return make_response(body=mcp_body({"web": [{"url": "https://example.com/a"}]}))

    monkeypatch.setattr("pygpt_net.provider.web.youcom_search.requests.post", fake_post)
    urls = provider._fetch("test query", 10)
    assert urls == ["https://example.com/a"]
    assert captured["endpoint"] == "https://api.you.com/mcp?profile=free"
    assert captured["json"]["method"] == "tools/call"
    assert captured["json"]["params"]["name"] == "you-search"
    assert captured["json"]["params"]["arguments"]["query"] == "test query"
    assert "Authorization" not in captured["headers"]


def test_fetch_with_api_key_uses_bearer(monkeypatch):
    """Test that API key is sent as bearer token"""
    plugin = make_plugin({
        "youcom_endpoint": "https://api.you.com/mcp",
        "youcom_api_key": "test-key",
    })
    provider = YouComSearch(plugin=plugin)
    captured = {}

    def fake_post(endpoint, json=None, headers=None, timeout=None):
        captured["headers"] = headers
        return make_response(body=mcp_body({"web": [{"url": "https://example.com/b"}]}))

    monkeypatch.setattr("pygpt_net.provider.web.youcom_search.requests.post", fake_post)
    provider._fetch("q", 10)
    assert captured["headers"]["Authorization"] == "Bearer test-key"


def test_fetch_http_error_returns_empty(monkeypatch):
    """Test fail-safe on HTTP error"""
    plugin = make_plugin({})
    provider = YouComSearch(plugin=plugin)
    response = make_response(status_code=500, body="err")
    monkeypatch.setattr(
        "pygpt_net.provider.web.youcom_search.requests.post",
        MagicMock(return_value=response),
    )
    assert provider._fetch("q", 10) == []


def test_search_fail_safe_on_exception():
    """Test search never raises to the app layer"""
    plugin = make_plugin({})
    provider = YouComSearch(plugin=plugin)
    provider._fetch = MagicMock(side_effect=Exception("network down"))
    assert provider.search("q", 10) == []


def test_search_limit_offset():
    """Test limit and offset handling"""
    plugin = make_plugin({})
    provider = YouComSearch(plugin=plugin)
    web = [{"url": "https://example.com/" + str(i)} for i in range(10)]
    provider._fetch = MagicMock(return_value=[item["url"] for item in web])
    assert len(provider.search("q", 3)) == 3
    urls = provider.search("q", 3, offset=5)
    assert urls == ["https://example.com/5", "https://example.com/6", "https://example.com/7"]


def test_search_dedup():
    """Test de-duplication of urls"""
    plugin = make_plugin({})
    provider = YouComSearch(plugin=plugin)
    provider._fetch = MagicMock(return_value=[
        "https://example.com/1",
        "https://example.com/1",
        "https://example.com/2",
    ])
    assert provider.search("q", 10) == ["https://example.com/1", "https://example.com/2"]


def test_is_configured_keyless():
    """Test keyless endpoint is always configured"""
    plugin = make_plugin({"youcom_endpoint": "https://api.you.com/mcp?profile=free"})
    provider = YouComSearch(plugin=plugin)
    assert provider.is_configured([{"cmd": "web_search"}]) is True


def test_is_configured_auth_requires_key():
    """Test authenticated endpoint requires key"""
    plugin = make_plugin({"youcom_endpoint": "https://api.you.com/mcp"})
    provider = YouComSearch(plugin=plugin)
    provider.get_key = MagicMock(return_value="")
    assert provider.is_configured([{"cmd": "web_search"}]) is False
    provider.get_key = MagicMock(return_value="key")
    assert provider.is_configured([{"cmd": "web_search"}]) is True


def test_get_key_from_env():
    """Test API key fallback to YDC_API_KEY env var"""
    import os
    plugin = make_plugin({"youcom_api_key": ""})
    provider = YouComSearch(plugin=plugin)
    os.environ["YDC_API_KEY"] = "env-key"
    try:
        assert provider.get_key() == "env-key"
    finally:
        del os.environ["YDC_API_KEY"]
    assert provider.get_key() == ""


def test_get_config_message():
    """Test config message"""
    plugin = make_plugin({})
    provider = YouComSearch(plugin=plugin)
    assert "You.com API key" in provider.get_config_message()
