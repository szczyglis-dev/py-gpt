#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.24 02:00:00                  #
# ================================================== #
import json
import os
import re
import time
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest

from pygpt_net.core.render.web.pid import PidData
from pygpt_net.core.render.web.renderer import Renderer
from pygpt_net.item.ctx import CtxItem, CtxMeta

@pytest.fixture
def fake_node():
    node = MagicMock()
    page = MagicMock()
    node.page = MagicMock(return_value=page)
    node.reset_current_content = MagicMock()
    node.update_current_content = MagicMock()
    return node

@pytest.fixture
def fake_window(fake_node):
    w = SimpleNamespace()
    w.core = SimpleNamespace()
    w.core.ctx = SimpleNamespace()
    w.core.ctx.output = MagicMock()
    w.core.ctx.output.get_current = MagicMock(return_value=fake_node)
    w.core.ctx.output.get_by_pid = MagicMock(return_value=fake_node)
    w.core.ctx.output.get_all = MagicMock(return_value=[fake_node])
    w.core.ctx.container = MagicMock()
    w.core.ctx.container.get_active_pid = MagicMock(return_value=1)
    w.core.config = MagicMock()
    def config_get(k, d=None):
        mapping = {"debug.render": False, "agent.output.render.all": False, "ctx.sources": False, "render.blocks": False}
        return mapping.get(k, d)
    w.core.config.get = MagicMock(side_effect=config_get)
    w.core.config.get_app_path = MagicMock(return_value="/app/path")
    w.core.config.get_user_dir = MagicMock(return_value="/user/dir")
    w.core.presets = {}
    w.core.platforms = SimpleNamespace(is_windows=lambda: False)
    w.ui = SimpleNamespace(nodes={'input': MagicMock(clear=MagicMock())})
    w.controller = SimpleNamespace(
        agent=SimpleNamespace(legacy=MagicMock(enabled=MagicMock(return_value=False))),
        theme=SimpleNamespace(markdown=MagicMock(load=MagicMock())),
        ctx=MagicMock(refresh_output=MagicMock())
    )
    w.controller.agent.legacy.enabled = MagicMock(return_value=False)
    return w

@pytest.fixture
def renderer(fake_window):
    r = Renderer(fake_window)
    r.is_stream = MagicMock(return_value=False)
    r.parser = MagicMock()
    r.parser.parse = MagicMock(side_effect=lambda x: x)
    r.helpers = MagicMock()
    r.helpers.format_chunk = MagicMock(side_effect=lambda x: x)
    r.helpers.format_user_text = MagicMock(side_effect=lambda x: x)
    r.helpers.post_format_text = MagicMock(side_effect=lambda x: x)
    r.helpers.pre_format_text = MagicMock(side_effect=lambda x: x)
    r.body = MagicMock()
    r.body.get_image_html = MagicMock(side_effect=lambda image, n, c: f"<img>{image}</img>")
    r.body.get_file_html = MagicMock(side_effect=lambda file, n, c: f"<file>{file}</file>")
    r.body.get_url_html = MagicMock(side_effect=lambda url, n, c: f"<url>{url}</url>")
    r.body.get_docs_html = MagicMock(return_value="<docs></docs>")
    r.body.get_html = MagicMock(return_value="<html></html>")
    r.body.prepare_styles = MagicMock(return_value="")
    r.body.prepare_action_icons = MagicMock(return_value="<action_icons>")
    r.body.prepare_tool_extra = MagicMock(return_value="<tool_extra>")
    r.reset_names_by_pid = MagicMock()
    #r.append_context_item = MagicMock()
    return r

class DummyCtxMeta:
    def __init__(self, preset=""):
        self.preset = preset

class DummyPid:
    def __init__(self, preset=""):
        self.preset = preset

class DummyCtxItem:
    def __init__(self):
        self.input = ""
        self.output = ""
        self.extra = {}
        self.hidden = False
        self.first = False
        self.id = 1
        self.idx = 0
        self.input_timestamp = None
        self.output_timestamp = None
        self.images = []
        self.files = []
        self.urls = []
        self.doc_ids = []
        self.internal = False
        self.input_name = ""
        self.output_name = ""
        self.cmds = []
        self.results = None
        self.live = False
        self.extra_ctx = None
        self.meta = DummyCtxMeta()
    def to_dict(self):
        return {"id": self.id}

class TestRenderer:
    def test_prepare(self, renderer):
        renderer.pids = {"1": 1}
        renderer.prepare()
        assert renderer.pids == {}

    def test_on_load(self, renderer, fake_window, fake_node):
        meta = DummyCtxMeta()
        fake_node.set_meta = MagicMock()
        renderer.reset = MagicMock()
        renderer.parser.reset = MagicMock()
        node = fake_window.core.ctx.output.get_current(meta)
        node.page().runJavaScript = MagicMock()
        renderer.on_load(meta)
        fake_node.set_meta.assert_called_with(meta)
        renderer.reset.assert_called_with(meta)
        renderer.parser.reset.assert_called()

    def test_on_page_loaded(self, renderer, fake_window, fake_node):
        meta = DummyCtxMeta()
        tab = SimpleNamespace(pid=1)
        renderer.pids = {1: MagicMock(loaded=False, html="content", use_buffer=False)}
        renderer.clear_chunks_input = MagicMock()
        renderer.clear_chunks_output = MagicMock()
        renderer.clear_nodes = MagicMock()
        renderer.append = MagicMock()
        fake_node.setUpdatesEnabled = MagicMock()
        renderer.on_page_loaded(meta, tab)
        assert renderer.pids[1].loaded is True
        renderer.clear_chunks_input.assert_called_with(1)
        renderer.clear_chunks_output.assert_called_with(1)
        renderer.clear_nodes.assert_called_with(1)
        renderer.append.assert_called_with(1, "content", flush=True)
        assert renderer.pids[1].html == ""

    def test_get_pid(self, renderer, fake_window):
        meta = DummyCtxMeta()
        fake_window.core.ctx.output.get_pid = MagicMock(return_value=42)
        pid = renderer.get_pid(meta)
        assert pid == 42

    def test_get_or_create_pid(self, renderer, fake_window):
        meta = DummyCtxMeta()
        fake_window.core.ctx.output.get_pid = MagicMock(return_value=10)
        renderer.pids = {}
        pid = renderer.get_or_create_pid(meta)
        assert pid == 10
        assert 10 in renderer.pids

    def test_pid_create(self, renderer):
        meta = DummyCtxMeta()
        renderer.pid_create(5, meta)
        assert 5 in renderer.pids
        assert renderer.pids[5].pid == 5
        assert renderer.pids[5].meta == meta

    def test_init_flush(self, renderer):
        pid = 1
        renderer.pids = {1: MagicMock(initialized=False, loaded=False)}
        called = False
        def dummy_flush(x):
            nonlocal called
            called = True
        renderer.flush = dummy_flush
        renderer.init(pid)
        assert called is True
        assert renderer.pids[1].initialized is True

    def test_init_clear_chunks(self, renderer):
        pid = 1
        renderer.pids = {1: MagicMock(initialized=True)}
        renderer.clear_chunks = MagicMock()
        renderer.init(pid)
        renderer.clear_chunks.assert_called_with(pid)

    def test_state_changed_busy(self, renderer, fake_window):
        meta = DummyCtxMeta()
        pid = DummyPid()
        fake_window.core.ctx.output.get_pid = MagicMock(return_value=pid)
        renderer.pids = {1: MagicMock()}
        node = fake_window.core.ctx.output.get_by_pid(1)
        node.page().runJavaScript = MagicMock()
        renderer.state_changed("render.state.busy", meta)
        node.page().runJavaScript.assert_called_with("if (typeof window.showLoading !== 'undefined') showLoading();")

    def test_state_changed_idle(self, renderer, fake_window):
        renderer.pids = {1: MagicMock()}
        node = fake_window.core.ctx.output.get_by_pid(1)
        node.page().runJavaScript = MagicMock()
        renderer.state_changed("render.state.idle", DummyCtxMeta())
        node.page().runJavaScript.assert_called_with("if (typeof window.hideLoading !== 'undefined') hideLoading();")

    def test_state_changed_error(self, renderer, fake_window):
        renderer.pids = {1: MagicMock()}
        node = fake_window.core.ctx.output.get_by_pid(1)
        node.page().runJavaScript = MagicMock()
        renderer.state_changed("render.state.error", DummyCtxMeta())
        node.page().runJavaScript.assert_called_with("if (typeof window.hideLoading !== 'undefined') hideLoading();")

    def test_begin(self, renderer):
        meta = DummyCtxMeta()
        ctx = DummyCtxItem()
        renderer.get_or_create_pid = MagicMock(return_value=1)
        renderer.init = MagicMock()
        renderer.reset_names = MagicMock()
        renderer.tool_output_end = MagicMock()
        renderer.begin(meta, ctx, False)
        renderer.get_or_create_pid.assert_called_with(meta)
        renderer.init.assert_called()
        renderer.reset_names.assert_called_with(meta)
        renderer.tool_output_end.assert_called()
        assert renderer.prev_chunk_replace is False

    def test_end(self, renderer):
        meta = DummyCtxMeta()
        ctx = DummyCtxItem()
        renderer.get_or_create_pid = MagicMock(return_value=1)
        renderer.pids = {1: MagicMock(item="item")}
        renderer.append_context_item = MagicMock()
        renderer.end(meta, ctx, True)
        renderer.append_context_item.assert_called_with(meta, "item")
        assert renderer.pids[1].item is None

    def test_end_extra(self, renderer):
        ctx = DummyCtxItem()
        called = False
        def dummy_to_end(x):
            nonlocal called
            called = True
        renderer.to_end = dummy_to_end
        renderer.end_extra(DummyCtxMeta(), ctx, False)
        assert called is True

    def test_stream_begin(self, renderer, fake_window):
        meta = DummyCtxMeta()
        node = fake_window.core.ctx.output.get_current(meta)
        node.page().runJavaScript = MagicMock()
        renderer.stream_begin(meta, DummyCtxItem())
        node.page().runJavaScript.assert_called_with("beginStream();")

    def test_stream_end(self, renderer, fake_window):
        meta = DummyCtxMeta()
        ctx = DummyCtxItem()
        renderer.get_or_create_pid = MagicMock(return_value=1)
        renderer.pids = {1: MagicMock(item="item")}
        renderer.window.controller.agent.legacy.enabled = MagicMock(return_value=True)
        renderer.append_context_item = MagicMock()
        node = fake_window.core.ctx.output.get_current(meta)
        node.page().runJavaScript = MagicMock()
        renderer.stream_end(meta, ctx)
        renderer.append_context_item.assert_called_with(meta, "item")
        assert renderer.pids[1].item is None
        node.page().runJavaScript.assert_called_with("endStream();")

    def test_append_context(self, renderer):
        meta = DummyCtxMeta()
        item1 = DummyCtxItem()
        item2 = DummyCtxItem()
        renderer.get_or_create_pid = MagicMock(return_value=1)
        renderer.init = MagicMock()
        renderer.reset = MagicMock()
        renderer.update_names = MagicMock()
        renderer.append_context_item = MagicMock()
        renderer.append = MagicMock()
        renderer.pids = {1: MagicMock(use_buffer=True, html="buffer")}
        renderer.append_context(meta, [item1, item2], True)
        renderer.reset.assert_called_with(meta, clear_nodes=False)
        assert renderer.pids[1].use_buffer is False
        #renderer.append.assert_called_with(1, "buffer", flush=True) # TODO: never called

    def test_append_input(self, renderer, fake_window):
        meta = DummyCtxMeta()
        ctx = DummyCtxItem()
        ctx.input = "test input"
        renderer.get_or_create_pid = MagicMock(return_value=1)
        renderer.update_names = MagicMock()
        renderer.tool_output_end = MagicMock()
        renderer.is_stream = MagicMock(return_value=False)
        renderer.append_node = MagicMock()
        renderer.append_input(meta, ctx, True, False)
        renderer.append_node.assert_called_with(meta=meta, ctx=ctx, html="test input", type=renderer.NODE_INPUT)

    def test_append_output(self, renderer):
        meta = DummyCtxMeta()
        ctx = DummyCtxItem()
        ctx.output = "test output"
        renderer.append_node = MagicMock()
        renderer.append_output(meta, ctx, True, None, None)
        renderer.append_node.assert_called_with(meta=meta, ctx=ctx, html="test output", type=renderer.NODE_OUTPUT, prev_ctx=None, next_ctx=None)

    def test_append_chunk(self, renderer, fake_window):
        meta = DummyCtxMeta()
        ctx = DummyCtxItem()
        renderer.get_or_create_pid = MagicMock(return_value=1)
        renderer.pids = {1: MagicMock(buffer="")}
        renderer.is_debug = MagicMock(return_value=False)
        node = fake_window.core.ctx.output.get_current(meta)
        node.page().runJavaScript = MagicMock()
        renderer.prev_chunk_newline = False
        renderer.prev_chunk_replace = False
        renderer.append_chunk(meta, ctx, "chunk", True)
        node.page().runJavaScript.assert_called()

    def test_next_chunk(self, renderer, fake_window):
        meta = DummyCtxMeta()
        ctx = DummyCtxItem()
        renderer.get_or_create_pid = MagicMock(return_value=1)
        renderer.pids = {1: MagicMock(buffer="old")}
        renderer.update_names = MagicMock()
        node = fake_window.core.ctx.output.get_current(meta)
        node.page().runJavaScript = MagicMock()
        renderer.prev_chunk_replace = True
        renderer.prev_chunk_newline = True
        renderer.next_chunk(meta, ctx)
        assert renderer.pids[1].buffer == ""
        node.page().runJavaScript.assert_called_with("nextStream();")

    def test_append_chunk_input(self, renderer, fake_window):
        meta = DummyCtxMeta()
        ctx = DummyCtxItem()
        ctx.input = "input"
        renderer.get_or_create_pid = MagicMock(return_value=1)
        renderer.clear_chunks_input = MagicMock()
        node = fake_window.core.ctx.output.get_current(meta)
        node.page().runJavaScript = MagicMock()
        renderer.append_chunk_input(meta, ctx, "chunk input", False)
        node.page().runJavaScript.assert_called()

    def test_append_live(self, renderer, fake_window):
        meta = DummyCtxMeta()
        ctx = DummyCtxItem()
        pid = DummyPid()
        renderer.get_or_create_pid = MagicMock(return_value=1)
        pid_data = PidData(pid)
        pid_data.loaded = False
        pid_data.use_buffer = False
        pid_data.html = ""
        pid_data.live_buffer = ""
        renderer.pids = {1: pid_data}
        renderer.is_debug = MagicMock(return_value=False)
        node = fake_window.core.ctx.output.get_current(meta)
        node.page().runJavaScript = MagicMock()
        renderer.append_live(meta, ctx, "live chunk", True)
        node.page().runJavaScript.assert_called_with("replaceLive(\"live chunk\");")

    def test_clear_live(self, renderer, fake_window):
        meta = DummyCtxMeta()
        ctx = DummyCtxItem()
        renderer.get_or_create_pid = MagicMock(return_value=1)
        renderer.pids = {1: MagicMock(loaded=False)}
        node = fake_window.core.ctx.output.get_by_pid(1)
        node.page().runJavaScript = MagicMock()
        renderer.clear_live(meta, ctx)
        node.page().runJavaScript.assert_called()
        renderer.pids = {1: MagicMock(loaded=True)}
        node.page().runJavaScript = MagicMock()
        renderer.clear_live(meta, ctx)
        node.page().runJavaScript.assert_called_with("clearLive();")

    def test_append_node(self, renderer):
        meta = DummyCtxMeta()
        ctx = DummyCtxItem()
        ctx.hidden = False
        pid = DummyPid()
        renderer.get_or_create_pid = MagicMock(return_value=pid)
        renderer.prepare_node = MagicMock(return_value="prepared")
        renderer.append = MagicMock()
        renderer.append_node(meta, ctx, "html", 1, None, None)
        renderer.append.assert_called_with(pid, "prepared")

    def test_append(self, renderer, fake_window):
        pid = 1
        pid_data = PidData(pid)
        pid_data.loaded = True
        pid_data.use_buffer = False
        pid_data.html = "buffer"
        renderer.pids = {pid: pid_data}
        node = fake_window.core.ctx.output.get_by_pid(pid)
        node.page().runJavaScript = MagicMock()
        renderer.flush_output = MagicMock()
        renderer.append(pid, "new html", flush=True)
        renderer.flush_output.assert_called_with(pid, "new html", False)
        assert renderer.pids[pid].html == ""
        pid_data = PidData(pid)
        pid_data.loaded = False
        pid_data.use_buffer = False
        pid_data.html = "buffer"
        renderer.pids = {pid: pid_data}
        renderer.append(pid, "more", flush=False)
        assert renderer.pids[pid].html == "buffermore"

    def test_append_context_item(self, renderer):
        meta = DummyCtxMeta()
        ctx = DummyCtxItem()
        renderer.append_input = MagicMock()
        renderer.append_output = MagicMock()
        renderer.append_context_item(meta, ctx, None, None)
        renderer.append_input.assert_called_with(meta, ctx, flush=False)
        renderer.append_output.assert_called_with(meta, ctx, flush=False, prev_ctx=None, next_ctx=None)

    def test_append_extra(self, renderer, fake_window):
        meta = DummyCtxMeta()
        ctx = DummyCtxItem()
        ctx.images = ["img1"]
        ctx.files = ["file1"]
        ctx.urls = ["url1"]
        ctx.doc_ids = [1]
        fake_window.core.config.get = MagicMock(return_value=True)
        renderer.get_pid = MagicMock(return_value=1)
        renderer.body.get_image_html = MagicMock(return_value="<img>img1</img>")
        renderer.body.get_file_html = MagicMock(return_value="<file>file1</file>")
        renderer.body.get_url_html = MagicMock(return_value="<url>url1</url>")
        renderer.body.get_docs_html = MagicMock(return_value="<docs></docs>")
        node = fake_window.core.ctx.output.get_current(meta)
        node.page().runJavaScript = MagicMock()
        renderer.pids = {1: MagicMock(images_appended=[], files_appended=[], urls_appended=[])}
        html = renderer.append_extra(meta, ctx, True, True)
        assert "<img>img1</img>" in html
        assert "<file>file1</file>" in html
        assert "<url>url1</url>" in html
        assert "<docs></docs>" in html

    def test_append_timestamp(self, renderer):
        ctx = DummyCtxItem()
        ctx.input_timestamp = 0
        res = renderer.append_timestamp(ctx, "text", renderer.NODE_INPUT)
        assert "00:00" in res
        ctx.output_timestamp = 0
        res = renderer.append_timestamp(ctx, "text", renderer.NODE_OUTPUT)
        assert "00:00" in res

    def test_reset(self, renderer):
        meta = DummyCtxMeta()
        renderer.get_pid = MagicMock(return_value=1)
        renderer.reset_by_pid = MagicMock()
        renderer.clear_live = MagicMock()
        renderer.reset(meta)
        renderer.reset_by_pid.assert_called_with(1, clear_nodes=True)
        renderer.get_pid = MagicMock(return_value=None)
        renderer.get_or_create_pid = MagicMock(return_value=2)
        renderer.reset(meta)
        renderer.reset_by_pid.assert_called_with(2, clear_nodes=True)

    def test_reset_by_pid(self, renderer, fake_window):
        pid = 1
        node = fake_window.core.ctx.output.get_by_pid(pid)
        node.reset_current_content = MagicMock()
        renderer.pids = {
            1: MagicMock(return_value=DummyPid())
        }
        renderer.parser.reset = MagicMock()
        renderer.clear_nodes = MagicMock()
        renderer.clear_chunks = MagicMock()
        renderer.reset_names_by_pid = MagicMock()
        renderer.reset_by_pid(pid)
        renderer.parser.reset.assert_called()
        renderer.clear_nodes.assert_called_with(pid)
        renderer.clear_chunks.assert_called_with(pid)
        node.reset_current_content.assert_called()
        renderer.reset_names_by_pid.assert_called_with(pid)
        assert renderer.prev_chunk_replace is False

    def test_clear_input(self, renderer):
        input_node = MagicMock()
        renderer.get_input_node = MagicMock(return_value=input_node)
        renderer.clear_input()
        input_node.clear.assert_called()

    def test_clear_output(self, renderer):
        meta = DummyCtxMeta()
        renderer.reset = MagicMock()
        renderer.prev_chunk_replace = True
        renderer.clear_output(meta)
        renderer.reset.assert_called_with(meta)
        assert renderer.prev_chunk_replace is False

    def test_clear_chunks_input(self, renderer, fake_window):
        renderer.get_output_node_by_pid = MagicMock(return_value=fake_window.core.ctx.output.get_by_pid(1))
        renderer.pids = {1: MagicMock(loaded=False)}
        node = fake_window.core.ctx.output.get_by_pid(1)
        node.page().runJavaScript = MagicMock()
        renderer.clear_chunks_input(1)
        node.page().runJavaScript.assert_called()
        renderer.pids = {1: MagicMock(loaded=True)}
        node.page().runJavaScript = MagicMock()
        renderer.clear_chunks_input(1)
        node.page().runJavaScript.assert_called_with("clearInput();")

    def test_clear_chunks_output(self, renderer, fake_window):
        renderer.get_output_node_by_pid = MagicMock(return_value=fake_window.core.ctx.output.get_by_pid(1))
        renderer.pids = {1: MagicMock()}
        node = fake_window.core.ctx.output.get_by_pid(1)
        node.page().runJavaScript = MagicMock()
        renderer.clear_chunks_output(1)
        node.page().runJavaScript.assert_called()

    def test_clear_nodes(self, renderer, fake_window):
        renderer.get_output_node_by_pid = MagicMock(return_value=fake_window.core.ctx.output.get_by_pid(1))
        renderer.pids = {1: MagicMock(loaded=False)}
        node = fake_window.core.ctx.output.get_by_pid(1)
        node.page().runJavaScript = MagicMock()
        renderer.clear_nodes(1)
        node.page().runJavaScript.assert_called()
        renderer.pids = {1: MagicMock(loaded=True)}
        node.page().runJavaScript = MagicMock()
        renderer.clear_nodes(1)
        node.page().runJavaScript.assert_called_with("clearNodes();")

    def test_prepare_node(self, renderer):
        meta = DummyCtxMeta()
        ctx = DummyCtxItem()
        renderer.get_or_create_pid = MagicMock(return_value=1)
        renderer.prepare_node_output = MagicMock(return_value="output")
        renderer.prepare_node_input = MagicMock(return_value="input")
        res = renderer.prepare_node(meta, ctx, "html", renderer.NODE_OUTPUT)
        assert res == "output"
        res = renderer.prepare_node(meta, ctx, "html", renderer.NODE_INPUT)
        assert res == "input"

    def test_prepare_node_input(self, renderer):
        pid = 1
        ctx = DummyCtxItem()
        ctx.id = 100
        renderer.get_or_create_pid = MagicMock(return_value=pid)
        renderer.helpers.format_user_text = MagicMock(return_value="formatted")
        renderer.helpers.post_format_text = MagicMock(side_effect=lambda x: x)
        renderer.append_timestamp = MagicMock(side_effect=lambda ctx, text, type: text)
        renderer.window.core.config.get = MagicMock(return_value=False)
        renderer.pids[pid] = MagicMock(name_user="User")
        res = renderer.prepare_node_input(pid, ctx, "html")
        assert "<p>" in res

    def test_prepare_node_output(self, renderer):
        meta = DummyCtxMeta()
        ctx = DummyCtxItem()
        ctx.id = 200
        renderer.pids = {
            1: MagicMock(return_value=DummyPid())
        }
        renderer.get_or_create_pid = MagicMock(return_value=1)
        renderer.helpers.pre_format_text = MagicMock(side_effect=lambda x: x)
        renderer.parser.parse = MagicMock(side_effect=lambda x: x)
        renderer.helpers.post_format_text = MagicMock(side_effect=lambda x: x)
        renderer.append_timestamp = MagicMock(side_effect=lambda ctx, text, type: text)
        renderer.append_extra = MagicMock(return_value="extra")
        renderer.body.prepare_action_icons = MagicMock(return_value="icons")
        res = renderer.prepare_node_output(meta, ctx, "html", None, None)
        assert "extra" in res

    def test_get_name_header(self, renderer, fake_window, monkeypatch):
        ctx = DummyCtxItem()
        ctx.meta = DummyCtxMeta(preset="preset1")
        preset = SimpleNamespace(ai_personalize=True, ai_name="Bot", ai_avatar="avatar.png")
        fake_window.core.presets = {"preset1": preset}
        monkeypatch.setattr(os.path, "exists", lambda path: True)
        res = renderer.get_name_header(ctx)
        assert "Bot" in res
        preset.ai_personalize = False
        res = renderer.get_name_header(ctx)
        assert res == ""

    def test_flush_output(self, renderer, fake_window):
        pid = 1
        renderer.pids = {pid: MagicMock()}
        node = fake_window.core.ctx.output.get_by_pid(pid)
        node.page().bridge = MagicMock()
        node.page().bridge.node = MagicMock()
        node.update_current_content = MagicMock()
        renderer.flush_output(pid, "html")
        node.page().runJavaScript.assert_called()

    def test_reload(self, renderer, fake_window):
        renderer.window.controller.ctx.refresh_output = MagicMock()
        renderer.reload()
        renderer.window.controller.ctx.refresh_output.assert_called()

    def test_fresh(self, renderer, fake_window):
        meta = DummyCtxMeta()
        pid = 1
        renderer.get_or_create_pid = MagicMock(return_value=pid)
        renderer.body.get_html = MagicMock(return_value="html")
        renderer.pids = {pid: MagicMock()}
        node = fake_window.core.ctx.output.get_by_pid(pid)
        node.resetPage = MagicMock()
        node.setHtml = MagicMock()
        renderer.fresh(meta)
        node.resetPage.assert_called()

    def test_get_output_node(self, renderer, fake_window):
        meta = DummyCtxMeta()
        fake_window.core.ctx.output.get_current = MagicMock(return_value="node")
        res = renderer.get_output_node(meta)
        assert res == "node"

    def test_get_output_node_by_pid(self, renderer, fake_window):
        fake_window.core.ctx.output.get_by_pid = MagicMock(return_value="node_by_pid")
        res = renderer.get_output_node_by_pid(1)
        assert res == "node_by_pid"

    def test_get_input_node(self, renderer, fake_window):
        fake_window.ui.nodes = {'input': "input_node"}
        res = renderer.get_input_node()
        assert res == "input_node"

    def test_remove_item(self, renderer, fake_window):
        meta = DummyCtxMeta()
        ctx = DummyCtxItem()
        node = fake_window.core.ctx.output.get_current(meta)
        node.page().runJavaScript = MagicMock()
        renderer.remove_item(ctx)
        node.page().runJavaScript.assert_called()

    def test_remove_items_from(self, renderer, fake_window):
        ctx = DummyCtxItem()
        node = fake_window.core.ctx.output.get_current(DummyCtxMeta())
        node.page().runJavaScript = MagicMock()
        renderer.remove_items_from(ctx)
        node.page().runJavaScript.assert_called()

    def test_reset_names(self, renderer):
        meta = DummyCtxMeta()
        renderer.get_or_create_pid = MagicMock(return_value=1)
        renderer.reset_names_by_pid = MagicMock()
        renderer.reset_names(meta)
        renderer.reset_names_by_pid.assert_called_with(1)

    def test_reset_names_by_pid(self, renderer):
        pid = 1
        renderer.pids = {pid: MagicMock()}
        renderer.window.core.config.get = MagicMock(side_effect=lambda k,d=None: k)
        renderer.reset_names_by_pid(pid)

    def test_on_reply_submit(self, renderer):
        ctx = DummyCtxItem()
        renderer.remove_items_from = MagicMock()
        renderer.on_reply_submit(ctx)
        renderer.remove_items_from.assert_called_with(ctx)

    def test_on_edit_submit(self, renderer):
        ctx = DummyCtxItem()
        renderer.remove_items_from = MagicMock()
        renderer.on_edit_submit(ctx)
        renderer.remove_items_from.assert_called_with(ctx)

    def test_on_enable_edit(self, renderer, fake_window):
        nodes = [MagicMock()]
        for n in nodes:
            n.page = MagicMock(return_value=MagicMock())
        renderer.get_all_nodes = MagicMock(return_value=nodes)
        for n in nodes:
            n.page().runJavaScript = MagicMock()
        renderer.on_enable_edit(True)
        for n in nodes:
            n.page().runJavaScript.assert_called()
        renderer.on_enable_edit(False)

    def test_on_disable_edit(self, renderer, fake_window):
        nodes = [MagicMock()]
        for n in nodes:
            n.page = MagicMock(return_value=MagicMock())
        renderer.get_all_nodes = MagicMock(return_value=nodes)
        for n in nodes:
            n.page().runJavaScript = MagicMock()
        renderer.on_disable_edit(True)
        for n in nodes:
            n.page().runJavaScript.assert_called()
        renderer.on_disable_edit(False)

    def test_on_enable_timestamp(self, renderer, fake_window):
        nodes = [MagicMock()]
        for n in nodes:
            n.page = MagicMock(return_value=MagicMock())
        renderer.get_all_nodes = MagicMock(return_value=nodes)
        for n in nodes:
            n.page().runJavaScript = MagicMock()
        renderer.on_enable_timestamp(True)
        for n in nodes:
            n.page().runJavaScript.assert_called()
        renderer.on_enable_timestamp(False)

    def test_on_disable_timestamp(self, renderer, fake_window):
        nodes = [MagicMock()]
        for n in nodes:
            n.page = MagicMock(return_value=MagicMock())
        renderer.get_all_nodes = MagicMock(return_value=nodes)
        for n in nodes:
            n.page().runJavaScript = MagicMock()
        renderer.on_disable_timestamp(True)
        for n in nodes:
            n.page().runJavaScript.assert_called()
        renderer.on_disable_timestamp(False)

    def test_update_names(self, renderer):
        meta = DummyCtxMeta()
        ctx = DummyCtxItem()
        ctx.input_name = "Alice"
        ctx.output_name = "Bob"
        renderer.get_or_create_pid = MagicMock(return_value=1)
        renderer.pids = {1: MagicMock()}
        renderer.update_names(meta, ctx)
        assert renderer.pids[1].name_user == "Alice"
        assert renderer.pids[1].name_bot == "Bob"

    def test_clear_all(self, renderer):
        renderer.clear_chunks = MagicMock()
        renderer.clear_nodes = MagicMock()
        renderer.pids = {1: MagicMock(html="something"), 2: MagicMock(html="test")}
        renderer.clear_all()
        renderer.clear_chunks.assert_any_call(1)
        renderer.clear_chunks.assert_any_call(2)
        renderer.clear_nodes.assert_any_call(1)
        renderer.clear_nodes.assert_any_call(2)
        for pid in renderer.pids:
            assert renderer.pids[pid].html == ""

    def test_scroll_to_bottom(self, renderer):
        renderer.scroll_to_bottom()

    def test_append_block(self, renderer):
        renderer.append_block()

    def test_to_end(self, renderer):
        ctx = DummyCtxItem()
        renderer.to_end(ctx)

    def test_get_all_nodes(self, renderer, fake_window):
        renderer.window.core.ctx.output.get_all = MagicMock(return_value=["n1", "n2"])
        res = renderer.get_all_nodes()
        assert res == ["n1", "n2"]

    def test_reload_css(self, renderer, fake_window):
        renderer.pids = {1: MagicMock(loaded=True)}
        nodes = [MagicMock()]
        for n in nodes:
            n.page = MagicMock(return_value=MagicMock())
            n.page().runJavaScript = MagicMock()
        renderer.get_all_nodes = MagicMock(return_value=nodes)
        renderer.window.core.config.get = MagicMock(return_value=False)
        renderer.reload_css()
        for n in nodes:
            n.page().runJavaScript.assert_called()

    def test_on_theme_change(self, renderer, fake_window):
        renderer.window.controller.theme.markdown.load = MagicMock()
        renderer.pids = {1: MagicMock(loaded=True)}
        renderer.reload_css = MagicMock()
        renderer.on_theme_change()
        renderer.window.controller.theme.markdown.load.assert_called()
        renderer.reload_css.assert_called()

    def test_tool_output_append(self, renderer, fake_window):
        meta = DummyCtxMeta()
        renderer.get_output_node = MagicMock(return_value=fake_window.core.ctx.output.get_current(meta))
        node = fake_window.core.ctx.output.get_current(meta)
        node.page().runJavaScript = MagicMock()
        renderer.tool_output_append(meta, "content")
        node.page().runJavaScript.assert_called()

    def test_tool_output_update(self, renderer, fake_window):
        meta = DummyCtxMeta()
        renderer.get_output_node = MagicMock(return_value=fake_window.core.ctx.output.get_current(meta))
        node = fake_window.core.ctx.output.get_current(meta)
        node.page().runJavaScript = MagicMock()
        renderer.tool_output_update(meta, "content")
        node.page().runJavaScript.assert_called()

    def test_tool_output_clear(self, renderer, fake_window):
        meta = DummyCtxMeta()
        renderer.get_output_node = MagicMock(return_value=fake_window.core.ctx.output.get_current(meta))
        node = fake_window.core.ctx.output.get_current(meta)
        node.page().runJavaScript = MagicMock()
        renderer.tool_output_clear(meta)
        node.page().runJavaScript.assert_called()

    def test_tool_output_begin(self, renderer, fake_window):
        meta = DummyCtxMeta()
        renderer.get_output_node = MagicMock(return_value=fake_window.core.ctx.output.get_current(meta))
        node = fake_window.core.ctx.output.get_current(meta)
        node.page().runJavaScript = MagicMock()
        renderer.tool_output_begin(meta)
        node.page().runJavaScript.assert_called()

    def test_tool_output_end(self, renderer, fake_window):
        renderer.get_output_node = MagicMock(return_value=fake_window.core.ctx.output.get_current(DummyCtxMeta()))
        node = fake_window.core.ctx.output.get_current(DummyCtxMeta())
        node.page().runJavaScript = MagicMock()
        renderer.tool_output_end()
        node.page().runJavaScript.assert_called()

    def test_is_debug(self, renderer, fake_window):
        renderer.window.core.config.get = MagicMock(return_value=True)
        assert renderer.is_debug() is True

    def test_remove_pid(self, renderer):
        renderer.pids = {1: "data"}
        renderer.remove_pid(1)
        assert 1 not in renderer.pids