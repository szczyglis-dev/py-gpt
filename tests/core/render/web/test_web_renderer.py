#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.02 18:00:00                  #
# ================================================== #
import json
import os
import re
import time
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import ANY, MagicMock, call
import pytest

from pygpt_net.core.render.protocol import RenderOp
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
    w.core.command = MagicMock()
    w.core.command.visible_tool_names.side_effect = lambda names: names
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
    r.helpers.format_cmd_data = MagicMock(side_effect=lambda x, indent=False: x)
    r.helpers.format_user_text = MagicMock(side_effect=lambda x: x)
    r.helpers.post_format_text = MagicMock(side_effect=lambda x: x)
    r.helpers.pre_format_text = MagicMock(side_effect=lambda x: x)
    r.helpers.extract_tool_calls = MagicMock(return_value=[])
    r.helpers.extract_extra_tool_calls = MagicMock(return_value=[])
    r.helpers.strip_tool_calls = MagicMock(side_effect=lambda x: x)
    r.body = MagicMock()
    r.body.build_extras_dicts = MagicMock(return_value=({}, {}, {}, {}))
    r.body.get_image_html = MagicMock(side_effect=lambda image, n, c, ctx=None: f"<img>{image}</img>")
    r.body.get_file_html = MagicMock(side_effect=lambda file, n, c, ctx=None: f"<file>{file}</file>")
    r.body.get_url_html = MagicMock(side_effect=lambda url, n, c: f"<url>{url}</url>")
    r.body.get_collapsible_extra_rows_html = MagicMock(
        side_effect=lambda rows: f'<div class="extra-items-list">{"<br/>".join(rows)}</div>'
    )
    r.body.get_docs_html = MagicMock(return_value="<docs></docs>")
    r.body.get_html = MagicMock(return_value="<html></html>")
    r.body.prepare_styles = MagicMock(return_value="")
    r.body.prepare_action_icons = MagicMock(return_value="<action_icons>")
    r.body.prepare_tool_extra = MagicMock(return_value="<tool_extra>")
    r.view.reset_names_by_pid = MagicMock()
    #r.append_context_item = MagicMock()
    return r

class DummyCtxMeta:
    def __init__(self, preset=""):
        self.preset = preset


def test_attachment_only_user_block_is_built_for_history(renderer):
    meta = CtxMeta()
    ctx = CtxItem()
    ctx.id = 12
    ctx.input = ''
    ctx.images = ['/image.png']
    renderer.session.get_or_create_pid = MagicMock(return_value=1)
    renderer.state.pids = {1: MagicMock()}
    renderer.body.build_extras_dicts.return_value = ({'1': {'url': 'file:///image.png'}}, {}, {}, {})
    block = renderer.messages.build_input_block(meta, ctx)
    assert block.input['text'] == ''
    assert block.extra['user_attachments']['images']['1']['url'] == 'file:///image.png'


def test_attachment_only_live_input_is_not_skipped(renderer):
    from pygpt_net.core.render.web.parts.block import RenderBlock
    meta = CtxMeta()
    ctx = CtxItem()
    ctx.id = 12
    ctx.input = ''
    renderer.session.get_or_create_pid = MagicMock(return_value=1)
    renderer.view.update_names = MagicMock()
    renderer.messages.input_attachment_snapshot = MagicMock(return_value={
        'images': {'1': {'url': 'file:///image.png'}}, 'files': {}, 'connections': {}})
    renderer.messages.build_render_block = MagicMock(return_value=RenderBlock(id=12))
    renderer.bridge.emit_mutation = MagicMock()
    renderer.messages.append_input(meta, ctx)
    mutation = renderer.bridge.emit_mutation.call_args.args[1]
    assert mutation.block['input']['text'] == ''
    assert mutation.block['extra']['user_attachments']['images']

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
    def get_display_output(self, output=None):
        return self.output if output is None else output

    def get_agents_v2_response_output(self):
        return None

    def get_agents_v2_final_output(self):
        return None

    def get_part_tool_calls(self, visible_only=False, part=None):
        return []

    def get_active_part(self):
        return None

    def to_dict(self):
        return {"id": self.id}

class TestRenderer:
    def test_prepare(self, renderer):
        renderer.state.pids = {"1": 1}
        renderer.prepare()
        assert renderer.state.pids == {}

    def test_on_load(self, renderer, fake_window, fake_node):
        meta = DummyCtxMeta()
        fake_node.set_meta = MagicMock()
        renderer.session.reset = MagicMock()
        renderer.parser.reset = MagicMock()
        node = fake_window.core.ctx.output.get_current(meta)
        node.page().runJavaScript = MagicMock()
        renderer.on_load(meta)
        fake_node.set_meta.assert_called_with(meta)
        renderer.session.reset.assert_called_with(meta)

    def test_on_page_loaded(self, renderer, fake_window, fake_node):
        meta = DummyCtxMeta()
        tab = SimpleNamespace(pid=1)
        renderer.state.pids = {1: MagicMock(loaded=False, html="content", use_buffer=False)}
        renderer.session.clear_chunks_input = MagicMock()
        renderer.session.clear_chunks_output = MagicMock()
        renderer.bridge.clear_nodes = MagicMock()
        renderer.bridge.append = MagicMock()
        fake_node.setUpdatesEnabled = MagicMock()
        renderer.on_page_loaded(meta, tab)
        assert renderer.state.pids[1].loaded is True
        renderer.session.clear_chunks_input.assert_called_with(1)
        renderer.session.clear_chunks_output.assert_called_with(1)
        renderer.bridge.clear_nodes.assert_called_with(1)
        renderer.bridge.append.assert_called_with(1, "content", flush=True)
        assert renderer.state.pids[1].html == ""

    def test_pid_create(self, renderer):
        meta = DummyCtxMeta()
        renderer.session.pid_create(5, meta)
        assert 5 in renderer.state.pids
        assert renderer.state.pids[5].pid == 5
        assert renderer.state.pids[5].meta == meta

    def test_init_flush(self, renderer):
        pid = 1
        renderer.state.pids = {1: MagicMock(initialized=False, loaded=False)}
        called = False
        def dummy_flush(x):
            nonlocal called
            called = True
        renderer.session.flush = dummy_flush
        renderer.session.init(pid)
        assert called is True
        assert renderer.state.pids[1].initialized is True

    def test_init_clear_chunks(self, renderer):
        pid = 1
        renderer.state.pids = {1: MagicMock(initialized=True)}
        renderer.session.clear_chunks = MagicMock()
        renderer.session.init(pid)
        renderer.session.clear_chunks.assert_called_with(pid)

    def test_state_changed_busy(self, renderer, fake_window):
        meta = DummyCtxMeta()
        pid = DummyPid()
        fake_window.core.ctx.output.get_pid = MagicMock(return_value=pid)
        renderer.state.pids = {1: MagicMock()}
        node = fake_window.core.ctx.output.get_by_pid(1)
        node.page().runJavaScript = MagicMock()
        renderer.state_changed("render.state.busy", meta)
        node.page().runJavaScript.assert_called_with("if (typeof window.showLoading !== 'undefined') showLoading(0, false);")

    def test_state_changed_idle(self, renderer, fake_window):
        renderer.state.pids = {1: MagicMock()}
        node = fake_window.core.ctx.output.get_by_pid(1)
        node.page().runJavaScript = MagicMock()
        renderer.state_changed("render.state.idle", DummyCtxMeta())
        node.page().runJavaScript.assert_called_with("if (typeof window.hideLoading !== 'undefined') hideLoading();"
            "if (typeof window.clearAgentWorking !== 'undefined') clearAgentWorking();")

    def test_state_changed_error(self, renderer, fake_window):
        renderer.state.pids = {1: MagicMock()}
        node = fake_window.core.ctx.output.get_by_pid(1)
        node.page().runJavaScript = MagicMock()
        renderer.state_changed("render.state.error", DummyCtxMeta())
        node.page().runJavaScript.assert_called_with("if (typeof window.hideLoading !== 'undefined') hideLoading();"
            "if (typeof window.clearAgentWorking !== 'undefined') clearAgentWorking();")

    def test_begin(self, renderer):
        meta = DummyCtxMeta()
        ctx = DummyCtxItem()
        renderer.session.get_or_create_pid = MagicMock(return_value=1)
        renderer.session.init = MagicMock()
        renderer.view.reset_names = MagicMock()
        renderer.tools.tool_output_end = MagicMock()
        renderer.begin(meta, ctx, False)
        renderer.session.get_or_create_pid.assert_called_with(meta)
        renderer.session.init.assert_called()
        renderer.view.reset_names.assert_called_with(meta)
        renderer.tools.tool_output_end.assert_called()
        assert renderer.state.prev_chunk_replace is False

    def test_end(self, renderer):
        meta = DummyCtxMeta()
        ctx = DummyCtxItem()
        pctx = PidData(1, meta)
        pctx.item = "item"
        renderer.session.get_or_create_pid = MagicMock(return_value=1)
        renderer.state.pids = {1: pctx}
        renderer.auto_cleanup = MagicMock()

        renderer.end(meta, ctx, True)

        renderer.session.get_or_create_pid.assert_called_once_with(meta)
        assert pctx.item is None
        assert pctx.buffer == ""
        renderer.auto_cleanup.assert_called_once_with(meta)

    def test_end_extra(self, renderer):
        ctx = DummyCtxItem()
        called = False
        def dummy_to_end(x):
            nonlocal called
            called = True
        renderer.view.to_end = dummy_to_end
        renderer.end_extra(DummyCtxMeta(), ctx, False)
        assert called is True

    def test_stream_begin(self, renderer, fake_window):
        meta = DummyCtxMeta()
        node = fake_window.core.ctx.output.get_current(meta)
        node.page().runJavaScript = MagicMock()
        renderer.stream_begin(meta, DummyCtxItem())
        node.page().runJavaScript.assert_called()

    def test_stream_end(self, renderer, fake_window):
        meta = DummyCtxMeta()
        ctx = DummyCtxItem()
        pctx = PidData(1, meta)
        pctx.item = "item"
        pctx.buffer = "pending"
        renderer.session.get_or_create_pid = MagicMock(return_value=1)
        renderer.state.pids = {1: pctx}
        renderer.streaming.stream_flush = MagicMock()
        renderer.streaming.flush_part_streams = MagicMock()
        renderer.streaming.partial_stream_reset = MagicMock()
        renderer.bridge.finalize_output = MagicMock()
        renderer.streaming.stream_reset = MagicMock()
        renderer.auto_cleanup = MagicMock()

        renderer.stream_end(meta, ctx)

        renderer.streaming.stream_flush.assert_called_once_with(1, force=True)
        renderer.streaming.flush_part_streams.assert_called_once_with(meta)
        renderer.bridge.finalize_output.assert_called_once_with(
            meta, ctx, replace_text=False, reason="stream_end"
        )
        assert pctx.item == "item"
        assert pctx.buffer == ""
        assert renderer.streaming.partial_stream_reset.call_count == 2
        renderer.streaming.stream_reset.assert_called_once_with(1)
        renderer.auto_cleanup.assert_called_once_with(meta)

    def test_append_context(self, renderer):
        meta = DummyCtxMeta()
        item1 = DummyCtxItem()
        item2 = DummyCtxItem()
        renderer.session.get_or_create_pid = MagicMock(return_value=1)
        renderer.session.init = MagicMock()
        renderer.session.reset = MagicMock()
        renderer.view.update_names = MagicMock()
        renderer.bridge.append_context_item = MagicMock()
        renderer.bridge.append = MagicMock()
        renderer.state.pids = {1: MagicMock(use_buffer=True, html="buffer")}
        renderer.append_context(meta, [item1, item2], True)
        renderer.session.reset.assert_called_with(meta, clear_nodes=False)
        assert renderer.state.pids[1].use_buffer is False
        #renderer.append.assert_called_with(1, "buffer", flush=True) # TODO: never called

    def test_append_input(self, renderer, fake_window):
        meta = DummyCtxMeta()
        ctx = DummyCtxItem()
        ctx.input = "test input"
        renderer.session.get_or_create_pid = MagicMock(return_value=1)
        renderer.view.update_names = MagicMock()
        renderer.tools.tool_output_end = MagicMock()
        renderer.messages.prepare_input = MagicMock(return_value="prepared input")
        block = MagicMock()
        block.to_dict.return_value = {"id": 1, "input": {"text": "prepared input"}}
        renderer.messages.build_render_block = MagicMock(return_value=block)
        renderer.bridge.emit_mutation = MagicMock()
        renderer.state.pids = {1: MagicMock()}

        renderer.append_input(meta, ctx, flush=True, append=False)

        renderer.tools.tool_output_end.assert_called_once_with()
        renderer.session.get_or_create_pid.assert_called_once_with(meta)
        renderer.view.update_names.assert_called_once_with(meta, ctx)
        renderer.messages.prepare_input.assert_called_once_with(meta, ctx, True, False)
        renderer.messages.build_render_block.assert_called_once_with(
            meta, ctx, input_text="prepared input", output_text=None, history_date_label=None
        )
        block.to_dict.assert_called_once_with()
        renderer.bridge.emit_mutation.assert_called_once()
        mutation_meta, mutation = renderer.bridge.emit_mutation.call_args.args
        assert mutation_meta is meta
        assert mutation.op == RenderOp.APPEND_INPUT
        assert mutation.msg_id == ctx.id
        assert mutation.block == block.to_dict.return_value

    def test_append_chunk(self, renderer, fake_window):
        meta = DummyCtxMeta()
        ctx = DummyCtxItem()
        ctx.id = 2
        previous = DummyCtxItem()
        previous.id = 1
        pctx = PidData(1, meta)
        pctx.item = previous
        pctx.header = ""
        renderer.session.get_or_create_pid = MagicMock(return_value=1)
        renderer.state.pids = {1: pctx}
        renderer.history.hide_previous_agent_action_icons = MagicMock()
        renderer.streaming.stream_reset = MagicMock()
        renderer.streaming.stream_push = MagicMock()
        renderer.view.update_names = MagicMock()
        renderer.messages.get_name_header = MagicMock(return_value="header")
        node = fake_window.core.ctx.output.get_current(meta)
        renderer.get_output_node = MagicMock(return_value=node)
        node.page().runJavaScript = MagicMock()

        renderer.append_chunk(meta, ctx, "chunk", begin=True)

        assert pctx.item is ctx
        assert pctx.header == "header"
        assert renderer.state.loading_visible[1] is False
        renderer.history.hide_previous_agent_action_icons.assert_called_once_with(meta, ctx)
        renderer.streaming.stream_reset.assert_called_once_with(1)
        renderer.view.update_names.assert_called_once_with(meta, ctx)
        assert node.page().runJavaScript.call_args_list == [
            call(
                "if (typeof window.bindStreamOwner !== 'undefined') bindStreamOwner(\"2\");"
            ),
            call("if (typeof window.hideLoading !== 'undefined') hideLoading(false);"),
            call(
                "if (typeof window.freezeWorkflowStatus !== 'undefined') freezeWorkflowStatus(\"2\");"
                "if (typeof window.beginStream !== 'undefined') beginStream(true, \"2\");"
                "if (typeof window.bindWorkflowStream !== 'undefined') bindWorkflowStream(\"2\", \"header\", [],\"\", \"\");",
                0,
                ANY,
            ),
        ]
        renderer.streaming.stream_push.assert_called_once_with(1, "header", "chunk")

    def test_next_chunk(self, renderer, fake_window):
        meta = DummyCtxMeta()
        ctx = DummyCtxItem()
        renderer.session.get_or_create_pid = MagicMock(return_value=1)
        renderer.state.pids = {1: MagicMock(buffer="old")}
        renderer.view.update_names = MagicMock()
        node = fake_window.core.ctx.output.get_current(meta)
        node.page().runJavaScript = MagicMock()
        renderer.state.prev_chunk_replace = True
        renderer.state.prev_chunk_newline = True
        renderer.next_chunk(meta, ctx)
        assert renderer.state.pids[1].buffer == ""
        node.page().runJavaScript.assert_called()

    def test_append_chunk_input(self, renderer, fake_window):
        meta = DummyCtxMeta()
        ctx = DummyCtxItem()
        ctx.input = "input"
        renderer.session.get_or_create_pid = MagicMock(return_value=1)
        renderer.session.clear_chunks_input = MagicMock()
        node = fake_window.core.ctx.output.get_current(meta)
        node.page().runJavaScript = MagicMock()
        renderer.streaming.append_chunk_input(meta, ctx, "chunk input", False)
        # node.page().runJavaScript.assert_called()  # moved to signals

    def test_append_live(self, renderer, fake_window):
        meta = DummyCtxMeta()
        ctx = DummyCtxItem()
        pid = DummyPid()
        renderer.session.get_or_create_pid = MagicMock(return_value=1)
        pid_data = PidData(pid)
        pid_data.loaded = False
        pid_data.use_buffer = False
        pid_data.html = ""
        pid_data.live_buffer = ""
        renderer.state.pids = {1: pid_data}
        renderer.is_debug = MagicMock(return_value=False)
        node = fake_window.core.ctx.output.get_current(meta)
        node.page().runJavaScript = MagicMock()
        renderer.append_live(meta, ctx, "live chunk", True)
        node.page().runJavaScript.assert_called()

    def test_clear_live(self, renderer, fake_window):
        meta = DummyCtxMeta()
        ctx = DummyCtxItem()
        renderer.session.get_or_create_pid = MagicMock(return_value=1)
        renderer.state.pids = {1: MagicMock(loaded=False)}
        node = fake_window.core.ctx.output.get_by_pid(1)
        node.page().runJavaScript = MagicMock()
        renderer.clear_live(meta, ctx)
        node.page().runJavaScript.assert_called()
        renderer.state.pids = {1: MagicMock(loaded=True)}
        node.page().runJavaScript = MagicMock()
        renderer.clear_live(meta, ctx)
        node.page().runJavaScript.assert_called()

    def test_append_node(self, renderer):
        meta = DummyCtxMeta()
        ctx = DummyCtxItem()
        ctx.hidden = False
        pid = DummyPid()
        renderer.session.get_or_create_pid = MagicMock(return_value=pid)
        renderer.messages.prepare_node = MagicMock(return_value="prepared")
        renderer.bridge.append = MagicMock()
        renderer.state.pids = {pid: MagicMock()}

    def test_append(self, renderer, fake_window):
        pid = 1
        pid_data = PidData(pid)
        pid_data.loaded = True
        pid_data.use_buffer = False
        pid_data.html = "buffer"
        renderer.state.pids = {pid: pid_data}
        node = fake_window.core.ctx.output.get_by_pid(pid)
        node.page().runJavaScript = MagicMock()
        renderer.bridge.flush_output = MagicMock()
        renderer.bridge.append(pid, "new html", flush=True)
        renderer.bridge.flush_output.assert_called_with(pid, "new html", False)
        assert renderer.state.pids[pid].html == ""
        pid_data = PidData(pid)
        pid_data.loaded = False
        pid_data.use_buffer = False
        pid_data.html = "buffer"
        renderer.state.pids = {pid: pid_data}
        renderer.bridge.append(pid, "more", flush=False)
        assert renderer.state.pids[pid].html == "buffermore"

    def test_append_context_item(self, renderer):
        meta = DummyCtxMeta()
        ctx = DummyCtxItem()
        renderer.bridge.append = MagicMock()
        renderer.bridge.append_context_item(meta, ctx, None, None)
        renderer.bridge.append.assert_called()

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
        renderer.state.pids = {1: MagicMock(images_appended=[], files_appended=[], urls_appended=[])}
        html = renderer.append_extra(meta, ctx, True, True)
        assert "<img>img1</img>" in html
        assert "<file>file1</file>" in html
        assert "<url>url1</url>" in html
        assert "<docs></docs>" in html
        assert renderer.body.get_collapsible_extra_rows_html.call_count == 2
        renderer.body.get_collapsible_extra_rows_html.assert_any_call(["<file>file1</file>"])
        renderer.body.get_collapsible_extra_rows_html.assert_any_call(["<url>url1</url>"])

    def test_append_extra_groups_files_and_urls_for_collapsing(self, renderer):
        meta = DummyCtxMeta()
        ctx = DummyCtxItem()
        ctx.files = [f"file{i}" for i in range(1, 8)]
        ctx.urls = [f"url{i}" for i in range(1, 8)]

        renderer.get_pid = MagicMock(return_value=1)
        renderer.state.pids = {
            1: MagicMock(images_appended=[], files_appended=[], urls_appended=[])
        }

        html = renderer.append_extra(meta, ctx, footer=False, render=False)

        assert renderer.body.get_collapsible_extra_rows_html.call_count == 2
        file_rows = renderer.body.get_collapsible_extra_rows_html.call_args_list[0].args[0]
        url_rows = renderer.body.get_collapsible_extra_rows_html.call_args_list[1].args[0]

        assert len(file_rows) == 7
        assert len(url_rows) == 7
        assert file_rows[0] == "<file>file1</file>"
        assert file_rows[-1] == "<file>file7</file>"
        assert url_rows[0] == "<url>url1</url>"
        assert url_rows[-1] == "<url>url7</url>"
        assert 'class="extra-items-list"' in html

    def test_append_timestamp(self, renderer):
        ctx = DummyCtxItem()
        ctx.input_timestamp = 0
        res = renderer.messages.append_timestamp(ctx, "text", renderer.NODE_INPUT)
        assert "00:00" in res
        ctx.output_timestamp = 0
        res = renderer.messages.append_timestamp(ctx, "text", renderer.NODE_OUTPUT)
        assert "00:00" in res

    def test_reset(self, renderer):
        meta = DummyCtxMeta()
        renderer.get_pid = MagicMock(return_value=1)
        renderer.session.reset_by_pid = MagicMock()
        renderer.streaming.clear_live = MagicMock()
        renderer.reset(meta)
        renderer.session.reset_by_pid.assert_called_with(1, clear_nodes=True)
        renderer.get_pid = MagicMock(return_value=None)
        renderer.session.get_or_create_pid = MagicMock(return_value=2)
        renderer.reset(meta)
        renderer.session.reset_by_pid.assert_called_with(2, clear_nodes=True)

    def test_reset_by_pid(self, renderer, fake_window):
        pid = 1
        node = fake_window.core.ctx.output.get_by_pid(pid)
        node.reset_current_content = MagicMock()
        renderer.state.pids = {
            1: MagicMock(return_value=DummyPid())
        }
        renderer.parser.reset = MagicMock()
        renderer.bridge.clear_nodes = MagicMock()
        renderer.session.clear_chunks = MagicMock()
        renderer.view.reset_names_by_pid = MagicMock()
        renderer.session.reset_by_pid(pid)
        renderer.bridge.clear_nodes.assert_called_with(pid)
        renderer.session.clear_chunks.assert_called_with(pid)
        node.reset_current_content.assert_called()
        renderer.view.reset_names_by_pid.assert_called_with(pid)
        assert renderer.state.prev_chunk_replace is False

    def test_clear_input(self, renderer):
        input_node = MagicMock()
        renderer.get_input_node = MagicMock(return_value=input_node)
        renderer.clear_input()
        input_node.clear.assert_called()

    def test_clear_output(self, renderer):
        meta = DummyCtxMeta()
        renderer.session.reset = MagicMock()
        renderer.state.prev_chunk_replace = True
        renderer.clear_output(meta)
        renderer.session.reset.assert_called_with(meta)
        assert renderer.state.prev_chunk_replace is False

    def test_clear_chunks_input(self, renderer, fake_window):
        renderer.get_output_node_by_pid = MagicMock(return_value=fake_window.core.ctx.output.get_by_pid(1))
        renderer.state.pids = {1: MagicMock(loaded=False)}
        node = fake_window.core.ctx.output.get_by_pid(1)
        node.page().runJavaScript = MagicMock()
        renderer.session.clear_chunks_input(1)
        node.page().runJavaScript.assert_called()
        renderer.state.pids = {1: MagicMock(loaded=True)}
        node.page().runJavaScript = MagicMock()
        renderer.session.clear_chunks_input(1)
        node.page().runJavaScript.assert_called()

    def test_clear_chunks_output(self, renderer, fake_window):
        renderer.get_output_node_by_pid = MagicMock(return_value=fake_window.core.ctx.output.get_by_pid(1))
        renderer.state.pids = {1: MagicMock()}
        node = fake_window.core.ctx.output.get_by_pid(1)
        node.page().runJavaScript = MagicMock()
        renderer.session.clear_chunks_output(1)
        node.page().runJavaScript.assert_called()

    def test_clear_nodes(self, renderer, fake_window):
        renderer.get_output_node_by_pid = MagicMock(return_value=fake_window.core.ctx.output.get_by_pid(1))
        renderer.state.pids = {1: MagicMock(loaded=False)}
        node = fake_window.core.ctx.output.get_by_pid(1)
        node.page().runJavaScript = MagicMock()
        renderer.bridge.clear_nodes(1)
        node.page().runJavaScript.assert_called()
        renderer.state.pids = {1: MagicMock(loaded=True)}
        node.page().runJavaScript = MagicMock()
        renderer.bridge.clear_nodes(1)
        node.page().runJavaScript.assert_called()

    def test_get_name_header(self, renderer, fake_window, monkeypatch):
        ctx = DummyCtxItem()
        ctx.meta = DummyCtxMeta(preset="preset1")
        preset = SimpleNamespace(ai_personalize=True, ai_name="Bot", ai_avatar="avatar.png")
        fake_window.core.presets = {"preset1": preset}
        monkeypatch.setattr(os.path, "exists", lambda path: True)
        res = renderer.messages.get_name_header(ctx)
        assert "Bot" in res
        preset.ai_personalize = False
        res = renderer.messages.get_name_header(ctx)
        assert res == ""

    def test_flush_output(self, renderer, fake_window):
        pid = 1
        renderer.state.pids = {pid: MagicMock()}
        node = fake_window.core.ctx.output.get_by_pid(pid)
        node.page().bridge = MagicMock()
        node.page().bridge.node = MagicMock()
        node.update_current_content = MagicMock()
        renderer.bridge.flush_output(pid, "html")
        node.page().runJavaScript.assert_called()

    def test_reload(self, renderer, fake_window):
        renderer.window.controller.ctx.refresh_output = MagicMock()
        renderer.reload()
        renderer.window.controller.ctx.refresh_output.assert_called()

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
        renderer.session.get_or_create_pid = MagicMock(return_value=1)
        renderer.view.reset_names_by_pid = MagicMock()
        renderer.view.reset_names(meta)
        renderer.view.reset_names_by_pid.assert_called_with(1)

    def test_reset_names_by_pid(self, renderer):
        pid = 1
        renderer.state.pids = {pid: MagicMock()}
        renderer.window.core.config.get = MagicMock(side_effect=lambda k,d=None: k)
        renderer.view.reset_names_by_pid(pid)

    def test_on_reply_submit(self, renderer):
        ctx = DummyCtxItem()
        renderer.view.remove_items_from = MagicMock()
        renderer.on_reply_submit(ctx)
        renderer.view.remove_items_from.assert_called_with(ctx)

    def test_on_edit_submit(self, renderer):
        ctx = DummyCtxItem()
        renderer.view.remove_items_from = MagicMock()
        renderer.on_edit_submit(ctx)
        renderer.view.remove_items_from.assert_called_with(ctx)

    def test_on_enable_edit(self, renderer, fake_window):
        nodes = [MagicMock()]
        for n in nodes:
            n.page = MagicMock(return_value=MagicMock())
        renderer.view.get_all_nodes = MagicMock(return_value=nodes)
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
        renderer.view.get_all_nodes = MagicMock(return_value=nodes)
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
        renderer.view.get_all_nodes = MagicMock(return_value=nodes)
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
        renderer.view.get_all_nodes = MagicMock(return_value=nodes)
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
        renderer.session.get_or_create_pid = MagicMock(return_value=1)
        renderer.state.pids = {1: MagicMock()}
        renderer.view.update_names(meta, ctx)
        assert renderer.state.pids[1].name_user == "Alice"
        assert renderer.state.pids[1].name_bot == "Bob"

    def test_clear_all(self, renderer):
        renderer.session.clear_chunks = MagicMock()
        renderer.bridge.clear_nodes = MagicMock()
        renderer.state.pids = {1: MagicMock(html="something"), 2: MagicMock(html="test")}
        renderer.clear_all()
        renderer.session.clear_chunks.assert_any_call(1)
        renderer.session.clear_chunks.assert_any_call(2)
        renderer.bridge.clear_nodes.assert_any_call(1)
        renderer.bridge.clear_nodes.assert_any_call(2)
        for pid in renderer.state.pids:
            assert renderer.state.pids[pid].html == ""

    def test_scroll_to_bottom(self, renderer):
        renderer.view.scroll_to_bottom()

    def test_append_block(self, renderer):
        renderer.view.append_block()

    def test_to_end(self, renderer):
        ctx = DummyCtxItem()
        renderer.view.to_end(ctx)

    def test_get_all_nodes(self, renderer, fake_window):
        renderer.window.core.ctx.output.get_all = MagicMock(return_value=["n1", "n2"])
        res = renderer.view.get_all_nodes()
        assert res == ["n1", "n2"]

    def test_reload_css(self, renderer, fake_window):
        renderer.state.pids = {1: MagicMock(loaded=True)}
        nodes = [MagicMock()]
        for n in nodes:
            n.page = MagicMock(return_value=MagicMock())
            n.page().runJavaScript = MagicMock()
        renderer.view.get_all_nodes = MagicMock(return_value=nodes)
        renderer.window.core.config.get = MagicMock(return_value=False)
        renderer.view.reload_css()
        for n in nodes:
            n.page().runJavaScript.assert_called()

    def test_on_theme_change(self, renderer, fake_window):
        renderer.window.controller.theme.markdown.load = MagicMock()
        renderer.state.pids = {1: MagicMock(loaded=True)}
        renderer.view.reload_css = MagicMock()
        renderer.on_theme_change()
        renderer.window.controller.theme.markdown.load.assert_called()
        renderer.view.reload_css.assert_called()

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
        renderer.helpers.format_cmd_data.assert_called_once_with("content", indent=True)
        node.page().runJavaScript.assert_called_once()

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
        fake_window.core.command.realtime_visible_tool_names.return_value = ["fs_read_file"]
        ctx = DummyCtxItem()
        renderer.agents.workflow_status_key = MagicMock(return_value=((1, "1"), 1, ctx))
        renderer.agents.workflow_status_add = MagicMock(return_value="read_file-status")
        renderer.agents.update_agent_working = MagicMock()
        renderer.tool_output_begin(meta, ["fs_read_file"], ctx)
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
        renderer.state.pids = {1: "data"}
        renderer.remove_pid(1)
        assert 1 not in renderer.state.pids


def test_auto_cleanup_excludes_audio_provider_memory(renderer, fake_window, monkeypatch):
    """Whisper/Torch memory excluded by audio providers must not trigger renderer cleanup."""
    meta = DummyCtxMeta()
    fake_window.core.config.get = MagicMock(
        side_effect=lambda key, default=None: 2500 if key == "render.memory.limit" else default
    )
    fake_window.core.audio = SimpleNamespace(
        get_memory_excluded_bytes=MagicMock(return_value=1000)
    )
    monkeypatch.setattr(
        "pygpt_net.core.render.web.renderer.mem_used_bytes",
        lambda: 3000,
    )
    renderer.session.fresh = MagicMock()
    renderer.auto_cleanup_soft = MagicMock()

    renderer.auto_cleanup(meta)

    renderer.session.fresh.assert_not_called()
    renderer.auto_cleanup_soft.assert_called_once_with(meta)
    fake_window.core.audio.get_memory_excluded_bytes.assert_called_once()


def test_auto_cleanup_uses_effective_memory_after_exclusion(renderer, fake_window, monkeypatch):
    """Cleanup still runs when RSS minus excluded Whisper/Torch memory exceeds the limit."""
    meta = DummyCtxMeta()
    fake_window.core.config.get = MagicMock(
        side_effect=lambda key, default=None: 2500 if key == "render.memory.limit" else default
    )
    fake_window.core.audio = SimpleNamespace(
        get_memory_excluded_bytes=MagicMock(return_value=1000)
    )
    monkeypatch.setattr(
        "pygpt_net.core.render.web.renderer.mem_used_bytes",
        lambda: 4000,
    )
    renderer.session.fresh = MagicMock()
    renderer.auto_cleanup_soft = MagicMock()

    renderer.auto_cleanup(meta)

    renderer.session.fresh.assert_called_once_with(meta, force=True)
    renderer.auto_cleanup_soft.assert_not_called()


@pytest.mark.parametrize('mode', ['agent_llama', 'agent_v2'])
@pytest.mark.parametrize('full_workflow', [False, True])
@pytest.mark.parametrize('rebuild', [False, True])
def test_completed_workflow_respects_display_setting(renderer, mode, full_workflow, rebuild):
    ctx = CtxItem()
    ctx.mode = mode
    ctx.extra = {'agent_timeline': True}
    ctx.id = 1
    ctx.output = 'Final'
    from pygpt_net.item.ctx_part import CtxItemPart
    ctx.extra['response_final'] = True
    ctx.parts = [CtxItemPart(output='Final', extra={'agents_v2_final': True})]
    renderer.state.pids[1] = MagicMock()
    renderer.helpers.pre_format_text.side_effect = lambda text, **kwargs: text
    renderer.session.get_or_create_pid = MagicMock(return_value=1)
    original_get = renderer.window.core.config.get.side_effect
    renderer.window.core.config.get.side_effect = lambda key, default=None: (
        full_workflow if key == "agent.v2.display_full_workflow" else original_get(key, default)
    )
    renderer.agents.ctx_has_final_answer = MagicMock(return_value=True)
    renderer.timeline.build_partial_timeline = MagicMock(return_value=[
        {'kind': 'text', 'text': 'First', 'part_uuid': 'first'},
        {'kind': 'text', 'text': 'Second', 'part_uuid': 'second'},
    ])
    renderer.agents.agent_v2_timeline_without_final_text = MagicMock(side_effect=lambda ctx, timeline: timeline)
    renderer.agents.agent_v2_collapsed_workflow_step_count = MagicMock(return_value=2)
    block = renderer.messages.build_render_block(CtxMeta(), ctx, None, 'Final', action_state={}, rebuild=rebuild)
    if full_workflow:
        assert block.extra['collapsed_workflow'] is None
        assert len(block.extra['partial_timeline']) == 2
    else:
        assert block.extra['collapsed_workflow']['expanded'] is False
        assert len(block.extra['collapsed_workflow']['timeline']) == 2


@pytest.mark.parametrize("mode,extra", [("agent_v2", {}), ("agent", {"agent_timeline": True})])
def test_working_timer_requires_real_work(renderer, monkeypatch, mode, extra):
    monkeypatch.setattr("pygpt_net.core.render.web.parts.agents.trans", lambda key: key)
    ctx = CtxItem()
    ctx.mode = mode
    ctx.extra = extra
    ctx.input_timestamp = 123
    ctx.parts = [SimpleNamespace(extra={}, tasks=[])]
    assert renderer.agents.agent_working_payload(ctx) is None
    assert renderer.agents.agent_working_payload(ctx, tool_started=True)["started"] == 123
    ctx.parts.append(SimpleNamespace(extra={}, tasks=[]))
    assert renderer.agents.agent_working_payload(ctx) is not None
    ctx.parts[-1].extra["agents_v2_final"] = True
    assert renderer.agents.agent_working_payload(ctx, tool_started=True) is None


@pytest.mark.parametrize("ending", ["stopped", "response_final", "response_interrupted"])
def test_working_timer_does_not_restart_after_end(renderer, ending):
    ctx = CtxItem()
    ctx.mode = "agent_v2"
    if ending == "stopped":
        ctx.stopped = True
    else:
        ctx.extra[ending] = True
    assert renderer.agents.agent_working_payload(ctx, tool_started=True) is None


def test_working_timer_not_shown_for_regular_chat(renderer):
    ctx = CtxItem()
    ctx.mode = "chat"
    assert renderer.agents.agent_working_payload(ctx, tool_started=True) is None


def test_live_tool_snapshot_preserves_readiness_and_repeated_calls(renderer, fake_window):
    from pygpt_net.item.ctx_part_task import CtxItemPartTask
    from pygpt_net.item.ctx_part import CtxItemPart
    from pygpt_net.item.ctx import CtxItem
    ctx = CtxItem()
    ctx.id = 42
    part = CtxItemPart()
    tasks = []
    for call_id, visible, ready in [('a', True, False), ('b', True, False), ('hidden', False, False), ('old', True, True)]:
        task = CtxItemPartTask()
        task.tool_call_id = call_id
        task.tool_input = {'query': call_id}
        task.extra = {'tool_name': 'search', 'ui_visible': visible, 'ui_ready': ready}
        tasks.append(task)
    tasks[0].set_result({'found': 1})
    part.tasks = tasks
    ctx.parts = [part]
    renderer.tools.show_tool_chain_for_ctx = MagicMock(return_value=True)
    from pygpt_net.core.render.web.helpers import Helpers
    renderer.helpers = Helpers(fake_window)
    renderer.helpers.is_tool_hidden = MagicMock(return_value=False)
    renderer.get_output_node = MagicMock(return_value=fake_window.core.ctx.output.get_current())
    renderer.state.workflow_statuses = {(1, "42"): [{"kind": "tool", "active": True}]}
    renderer.tool_output_snapshot(None, ctx)
    assert not tasks[0].is_ui_ready()
    tasks[0].mark_ui_ready(True)
    renderer.tool_output_snapshot(None, ctx)
    script = renderer.get_output_node().page().runJavaScript.call_args.args[0]
    assert 'syncLiveTools("42"' in script
    assert '"call_id": "a"' in script and '"call_id": "b"' in script
    assert '"call_id": "hidden"' not in script and '"call_id": "old"' not in script
    assert '"response"' in script
    assert tasks[0].is_ui_ready()
    assert not tasks[1].is_ui_ready()


def test_live_tool_snapshot_respects_json_visibility(renderer, fake_window):
    from pygpt_net.item.ctx import CtxItem
    renderer.tools.show_tool_chain_for_ctx = MagicMock(return_value=False)
    renderer.get_output_node = MagicMock()
    renderer.tool_output_snapshot(None, CtxItem())
    renderer.get_output_node.assert_not_called()


def test_stream_barrier_ignores_stale_callback_and_delivers_buffer(renderer, fake_node):
    """A late callback from a superseded begin must never release pending text."""
    from pygpt_net.core.render.web.parts.buffer import AppendBuffer

    renderer.state.pids = {1: MagicMock()}
    renderer.state.stream_acc[1] = AppendBuffer()
    renderer.state.stream_acc[1].append("pierwszy fragment")
    renderer.state.stream_header[1] = "header"
    stale = renderer.streaming.stream_begin_arm(1)
    current = renderer.streaming.stream_begin_arm(1)

    renderer.streaming.stream_begin_release(1, stale)
    fake_node.page().bridge.chunk.emit.assert_not_called()
    assert not renderer.state.stream_acc[1].is_empty()

    renderer.streaming.stream_begin_release(1, current)
    fake_node.page().bridge.chunk.emit.assert_called_once_with("header", "pierwszy fragment", "text_delta")
    assert renderer.state.stream_acc[1].is_empty()


def test_pid_teardown_stops_owned_timers_and_keeps_other_chat(renderer):
    renderer.state.pids = {1: MagicMock(), 2: MagicMock()}
    key = (1, 10, "part")
    other = (2, 20, "part")
    main_timer, partial_timer, pending_timer = MagicMock(), MagicMock(), MagicMock()
    renderer.state.stream_timer.update({1: main_timer, 2: MagicMock()})
    renderer.state.partial_stream_timer.update({key: partial_timer, other: MagicMock()})
    renderer.state.pending_timer[1] = pending_timer
    renderer.state.workflow_statuses.update({(1, "10"): [{"text": "working"}], (2, "20"): []})
    renderer.state.loading_visible.update({1: True, 2: True})

    renderer.remove_pid(1)

    main_timer.stop.assert_called()
    partial_timer.stop.assert_called_once()
    pending_timer.stop.assert_called_once()
    assert 1 not in renderer.state.pids and 2 in renderer.state.pids
    assert 1 not in renderer.state.stream_timer and 2 in renderer.state.stream_timer
    assert key not in renderer.state.partial_stream_timer and other in renderer.state.partial_stream_timer
    assert (1, "10") not in renderer.state.workflow_statuses
    assert (2, "20") in renderer.state.workflow_statuses
    assert renderer.state.loading_visible == {2: True}


@pytest.mark.parametrize("boundary", [
    {"text": "answer"}, {"status_id": "working"},
    {"status_kind": "tool"}, {"inline_message": True},
])
def test_tool_grouping_respects_chronological_boundaries(boundary):
    from pygpt_net.core.render.web.parts.tools import Tools

    first = {"tool_calls": [{"name": "a"}]}
    second = {"tool_calls": [{"name": "b"}]}
    third = {"tool_calls": [{"name": "c"}]}
    fourth = {"tool_calls": [{"name": "d"}]}
    timeline = Tools.group_adjacent_calls([first, second, boundary, third, fourth])
    assert timeline == [
        {"tool_calls": [{"name": "a"}, {"name": "b"}]},
        boundary,
        {"tool_calls": [{"name": "c"}, {"name": "d"}]},
    ]


def test_renderer_sessions_do_not_share_runtime_state(fake_window):
    first, second = Renderer(fake_window), Renderer(fake_window)
    first.state.workflow_statuses[(1, "turn")] = [{"text": "working"}]
    first.state.stream_begin_pending.add(1)
    first.state.loading_visible[1] = True
    assert second.state.workflow_statuses == {}
    assert second.state.stream_begin_pending == set()
    assert second.state.loading_visible == {}


def test_block_artifacts_hide_duplicates_without_modifying_context(renderer, fake_window):
    """Carried attachments appear on the last tool reply while stored data stays intact."""
    first, reply = CtxItem(), CtxItem()
    first.id, reply.id = 10, 11
    first.tool_calls = [{"name": "search"}]
    reply.internal = True
    first.images, reply.images = ["/image.png"], ["file:///image.png"]
    first.files, reply.files = ["/report.pdf"], ["file:///report.pdf"]
    first.urls, reply.urls = [" https://example.org "], ["https://example.org"]
    fake_window.core.ctx.get_items = MagicMock(return_value=[first, reply])
    fake_window.core.filesystem = SimpleNamespace(
        extract_local_url=lambda value: (None, value.removeprefix("file://")),
    )
    renderer.body.build_extras_dicts.return_value = (
        {"1": {"path": "/image.png"}},
        {"1": {"path": "/report.pdf"}, "2": {"path": "/keep.pdf"}},
        {"1": {"url": "https://example.org"}},
        {"edit_replay_id": 10},
    )
    from pygpt_net.core.render.web.parts.block import RenderBlock
    block = RenderBlock(id=10)

    renderer.artifacts.apply_to_block(block, first, 1, {})

    assert block.images == {} and block.urls == {}
    assert block.files == {"1": {"path": "/keep.pdf"}}
    assert block.extra["edit_replay_id"] == 10
    assert first.images == ["/image.png"]
    assert first.files == ["/report.pdf"]
    assert first.urls == [" https://example.org "]


def test_first_legacy_delta_refreshes_agent_label_after_stream_begin(renderer, fake_node):
    from pygpt_net.item.ctx import CtxItemPart

    ctx = CtxItem()
    ctx.id = 42
    ctx.mode = "agent_llama"
    meta = CtxMeta()
    part = CtxItemPart()
    part.name = "Supervisor"
    ctx.parts = [part]
    renderer.state.pids[1] = PidData(1)
    renderer.session.get_or_create_pid = MagicMock(return_value=1)
    renderer.get_output_node = MagicMock(return_value=fake_node)
    renderer.state.stream_session_ctx[1] = id(ctx)
    renderer.streaming.stream_push = MagicMock()
    renderer.streaming.append_chunk(meta, ctx, "Delegating", begin=True, part_key=part.uuid)
    scripts = [c.args[0] for c in fake_node.page().runJavaScript.call_args_list]
    assert any('bindWorkflowStream(' in s and 'Supervisor' in s and part.uuid in s for s in scripts)
    assert not any('beginStream(' in s for s in scripts)
    renderer.streaming.stream_push.assert_called_once()


def test_legacy_tool_only_partial_keeps_worker_label(renderer, fake_window):
    from pygpt_net.item.ctx_part import CtxItemPart
    from pygpt_net.item.ctx_part_task import CtxItemPartTask

    ctx = CtxItem()
    ctx.id = 42
    ctx.mode = "agent_llama"
    part = CtxItemPart()
    part.name = "Worker"
    part.agent_id = "orchestrator"
    task = CtxItemPartTask()
    task.tool_call_id = "worker-read"
    task.task_name = "read"
    task.extra = {"tool_name": "read", "ui_ready": True, "ui_visible": True}
    part.tasks = [task]
    ctx.parts = [part]
    fake_window.core.command.is_tool_hidden.return_value = False
    from pygpt_net.core.render.web.helpers import Helpers
    renderer.helpers = Helpers(fake_window)
    timeline = renderer.timeline.build_partial_timeline(ctx, include_tool_calls=True)
    tool_segment = next(s for s in timeline if s.get("tool_calls"))
    assert tool_segment["agent_name_prefix"] == "Worker"
    assert tool_segment["part_uuid"] == part.uuid


def test_delayed_tool_status_is_anchored_to_worker_not_active_supervisor(renderer, fake_node):
    from pygpt_net.item.ctx_part import CtxItemPart

    ctx = CtxItem()
    ctx.id = 42
    ctx.mode = "agent_llama"
    ctx.meta = CtxMeta()
    worker = CtxItemPart()
    worker.name = "Worker"
    supervisor = CtxItemPart()
    supervisor.name = "Supervisor"
    supervisor.output = "Done."
    ctx.parts = [worker, supervisor]
    ctx.active_part = supervisor
    renderer.state.pids[1] = PidData(1, item=ctx)
    renderer.session.get_or_create_pid = MagicMock(return_value=1)
    renderer.get_output_node = MagicMock(return_value=fake_node)
    owner = {"part_uuid": worker.uuid, "agent_name": "Worker", "placement": "before"}
    renderer.agents.agent_status(ctx.meta, ctx, "Using tool: read_file", owner=owner)
    records = renderer.agents.workflow_status_records(ctx)
    assert records[-1]["part_uuid"] == worker.uuid
    assert records[-1]["placement"] == "before"
    assert records[-1]["agent_name"] == "Worker"
    renderer.helpers.pre_format_text = MagicMock(side_effect=lambda text, **kwargs: text)
    timeline = renderer.timeline.build_partial_timeline(ctx, include_workflow_statuses=True)
    status = next(s for s in timeline if s.get("status_text"))
    assert status["agent_name_prefix"] == "Worker"
    scripts = [c.args[0] for c in fake_node.page().runJavaScript.call_args_list]
    assert any('setAgentStatus(' in s and worker.uuid in s and 'Worker' in s for s in scripts)


def test_legacy_consecutive_status_and_prose_share_one_agent_heading(renderer):
    from pygpt_net.item.ctx_part import CtxItemPart

    ctx = CtxItem()
    ctx.id = 42
    ctx.mode = "agent_llama"
    parts = []
    for name, text in [("Supervisor", "Save the file."), ("Worker", ""),
                       ("Worker", "Saved."), ("Supervisor", "Done.")]:
        part = CtxItemPart()
        part.name, part.output = name, text
        parts.append(part)
    ctx.parts = parts
    renderer.helpers.pre_format_text = MagicMock(side_effect=lambda text, **kwargs: text)
    renderer.agents.workflow_status_records = MagicMock(return_value=[{
        "id": "save-status", "seq": 1, "kind": "agent", "text": "Using tool: save_file",
        "part_uuid": parts[1].uuid, "placement": "before", "agent_name": "Worker",
    }])
    timeline = renderer.timeline.build_partial_timeline(ctx, include_workflow_statuses=True)
    assert [s["agent_name_prefix"] for s in timeline if s.get("agent_name_prefix")] == [
        "Supervisor", "Worker", "Supervisor",
    ]
    status_index = next(i for i, s in enumerate(timeline) if s.get("status_text"))
    assert timeline[status_index]["agent_name_prefix"] == "Worker"
    assert timeline[status_index + 1]["text"] == "Saved."
    assert timeline[status_index + 1]["agent_name_prefix"] == ""


def test_computer_use_does_not_emit_chat_tool_status(renderer, fake_window, monkeypatch):
    meta = DummyCtxMeta()
    ctx = DummyCtxItem()
    renderer.agents.workflow_status_key = MagicMock(return_value=((1, '1'), 1, ctx))
    renderer.agents.workflow_status_add = MagicMock()
    renderer.tools.tool_output_snapshot = MagicMock()
    renderer.get_output_node = MagicMock()
    javascript = renderer.get_output_node.return_value.page.return_value.runJavaScript
    monkeypatch.setattr('pygpt_net.core.render.web.parts.tools.trans', lambda key: 'Using computer... Press ESC to stop.')
    renderer.tool_output_begin(meta, ['mouse_click'], ctx)
    renderer.tool_output_begin(meta, ['keyboard_type'], ctx)
    # Computer use is represented by the global badge, outside the chat renderer.
    javascript.assert_not_called()
    renderer.agents.workflow_status_add.assert_not_called()
    renderer.tools.tool_output_snapshot.assert_not_called()
