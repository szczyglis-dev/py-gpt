#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.10 00:00:00                  #
# ================================================== #
import os
import json
import pytest
import random
from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem
from pygpt_net.core.render.web.body import Body

class FakeConfig:
    def __init__(self, data):
        self.data = data
    def get(self, key, default=None):
        return self.data.get(key, default)
    def get_app_path(self):
        return self.data.get("app_path", "/fake/app")

class FakeCoreCtx:
    def __init__(self, first_item=True):
        self.first_item = first_item
    def is_first_item(self, id):
        return self.first_item

class FakeFilesystem:
    def extract_local_url(self, url):
        return (url, "/local" + url)

class FakeMarkdown:
    def get_web_css(self):
        return "body { font-family: sans-serif; } %fonts%"

class FakeWindow:
    def __init__(self, config_data, first_item=True):
        self.core = type("FakeCore", (), {})()
        self.core.config = FakeConfig(config_data)
        self.core.ctx = FakeCoreCtx(first_item)
        self.core.filesystem = FakeFilesystem()
        self.controller = type("FakeController", (), {})()
        self.controller.theme = type("FakeTheme", (), {})()
        self.controller.theme.markdown = FakeMarkdown()
    def dispatch(self, event, all=False):
        if event.data.get("tool") == "plugin_test":
            event.data["html"] = "plugin html"
        elif event.data.get("tool") == "plugin_multiple":
            event.data["html"] = "multiple html"

class FakeCtxItem:
    def __init__(self, id, output="", extra=None):
        self.id = id
        self.output = output
        self.extra = extra

@pytest.fixture
def fake_window():
    config_data = {
        "app_path": "/fake/app",
        "output_timestamp": True,
        "render.code_syntax": "",
        "layout.tooltips": True,
        "render.blocks": True,
        "ctx.edit_icons": True,
        "theme.style": "blocks",
    }
    return FakeWindow(config_data)

@pytest.fixture
def body_instance(fake_window):
    b = Body(fake_window)
    b.highlight.get_style_defs = lambda: "dummy-style"
    return b

def test_is_timestamp_enabled():
    config_data = {"app_path": "/fake/app", "output_timestamp": True}
    win = FakeWindow(config_data)
    b = Body(win)
    assert b.is_timestamp_enabled() is True
    config_data["output_timestamp"] = False
    win = FakeWindow(config_data)
    b = Body(win)
    assert b.is_timestamp_enabled() is False

def test_prepare_styles():
    config_data = {"app_path": "/fake/app", "render.code_syntax": "monokai"}
    win = FakeWindow(config_data)
    b = Body(win)
    b.highlight.get_style_defs = lambda: "dummy-style"
    style = b.prepare_styles()
    assert "dummy-style" in style
    assert "pre { color: #fff; }" in style
    assert "/fake/app/data/fonts" in style
    config_data = {"app_path": "/fake/app", "render.code_syntax": "default"}
    win = FakeWindow(config_data)
    b = Body(win)
    b.highlight.get_style_defs = lambda: "dummy-style"
    style = b.prepare_styles()
    assert "pre { color: #000; }" in style

def test_prepare_action_icons():
    config_data = {"app_path": "/fake/app"}
    win = FakeWindow(config_data, first_item=False)
    b = Body(win)
    b.highlight.get_style_defs = lambda: ""
    ctx = FakeCtxItem("123", output="some output")
    html = b.prepare_action_icons(ctx)
    assert 'class="action-icons"' in html
    assert 'data-id="123"' in html

def test_get_action_icons():
    config_data = {"app_path": "/fake/app"}
    win = FakeWindow(config_data, first_item=True)
    b = Body(win)
    ctx = FakeCtxItem("123", output="value")
    icons = b.get_action_icons(ctx, all=False)
    assert len(icons) == 5
    win = FakeWindow(config_data, first_item=False)
    b = Body(win)
    ctx = FakeCtxItem("123", output="value")
    icons = b.get_action_icons(ctx, all=False)
    assert len(icons) == 6

def test_get_icon():
    config_data = {"app_path": "/fake/app"}
    win = FakeWindow(config_data)
    b = Body(win)
    ctx = FakeCtxItem("123")
    icon_html = b.get_icon("volume", "audio", ctx)
    expected = os.path.join("/fake/app", "data", "icons", "volume.svg")
    assert expected in icon_html
    assert 'title="audio"' in icon_html
    assert 'data-id="123"' in icon_html

def test_get_image_html():
    config_data = {"app_path": "/fake/app"}
    win = FakeWindow(config_data)
    b = Body(win)
    url = "http://example.com/img.png"
    html = b.get_image_html(url, 1, 2)
    assert 'extra-src-img-box' in html
    assert 'img.png' in html

def test_get_url_html():
    config_data = {"app_path": "/fake/app"}
    win = FakeWindow(config_data)
    b = Body(win)
    url = "http://example.com"
    html = b.get_url_html(url, 1, 2)
    assert "url.svg" in html
    assert f'href="{url}"' in html
    assert "[1]" in html

def test_get_docs_html():
    config_data = {"app_path": "/fake/app"}
    win = FakeWindow(config_data)
    b = Body(win)
    docs = [{"uuid1": {"file_path": "path1", "file_name": "name1", "file_type": "text/plain", "file_size": 28, "creation_date": "2024-03-03", "last_modified_date": "2024-03-03", "last_accessed_date": "2024-03-03"}}]
    html = b.get_docs_html(docs)
    assert "db.svg" in html
    assert "uuid1" in html
    assert "[1]" in html

def test_get_file_html():
    config_data = {"app_path": "/fake/app"}
    win = FakeWindow(config_data)
    b = Body(win)
    url = "http://example.com/file.txt"
    html = b.get_file_html(url, 1, 2)
    assert "attachments.svg" in html
    assert f'href="{url}"' in html

def test_prepare_tool_extra_plugin():
    config_data = {"app_path": "/fake/app"}
    win = FakeWindow(config_data)
    b = Body(win)
    ctx = FakeCtxItem("123", extra={"plugin": "plugin_test"})
    html = b.prepare_tool_extra(ctx)
    assert "tool-output-block" in html
    assert "plugin html" in html

def test_prepare_tool_extra_multiple():
    config_data = {"app_path": "/fake/app"}
    win = FakeWindow(config_data)
    b = Body(win)
    ctx = FakeCtxItem("123", extra={"tool_output": [{"plugin": "plugin_multiple"}, {"no_plugin": "x"}]})
    html = b.prepare_tool_extra(ctx)
    assert "tool-output-block" in html
    assert "multiple html" in html

def test_get_all_tips():
    config_data = {"app_path": "/fake/app", "layout.tooltips": True}
    win = FakeWindow(config_data)
    b = Body(win)
    tips_json = b.get_all_tips()
    tips = json.loads(tips_json)
    assert isinstance(tips, list)
    assert len(tips) == Body.NUM_TIPS
    config_data = {"app_path": "/fake/app", "layout.tooltips": False}
    win = FakeWindow(config_data)
    b = Body(win)
    tips_json = b.get_all_tips()
    assert tips_json == "[]"

def test_get_html(body_instance):
    html = body_instance.get_html(0)
    assert html.strip().startswith("<!DOCTYPE html>")