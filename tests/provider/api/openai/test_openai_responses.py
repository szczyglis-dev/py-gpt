#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.05 18:00:00                  #
# ================================================== #

import base64
import time
from types import SimpleNamespace

import pytest
from unittest.mock import MagicMock, mock_open

from pygpt_net.core.types import MODE_CHAT, MODE_VISION, MODE_AUDIO, MODE_RESEARCH, MODE_AGENT, MODE_AGENT_OPENAI, MODE_AGENT_LLAMA, MODE_EXPERT, MODE_COMPUTER, OPENAI_DISABLE_TOOLS, MULTIMODAL_IMAGE, MULTIMODAL_AUDIO
from pygpt_net.item.ctx import CtxItem
import pygpt_net.item.attachment as attachment_mod
from pygpt_net.item.preset import PresetItem
from pygpt_net.item.model import ModelItem
from pygpt_net.item.ctx import CtxItem

from pygpt_net.provider.api.openai.responses import Responses


@pytest.fixture
def dummy_window():
    config_dict = {
        'func_call.native': False,
        'max_total_tokens': 50,
        'use_context': False,
        'api_use_responses': True,
        'agent.api_use_responses': True,
        'experts.api_use_responses': True,
        'experts.internal.api_use_responses': True
    }
    window = SimpleNamespace()
    window.core = SimpleNamespace()
    window.core.config = SimpleNamespace()
    window.core.config.get = lambda key, default=None: config_dict.get(key, default)
    window.core.api = SimpleNamespace()
    window.core.api.openai = SimpleNamespace()
    window.core.api.openai.get_client = MagicMock()
    window.core.api.openai.tools = SimpleNamespace()
    window.core.api.openai.tools.prepare_responses_api = MagicMock(return_value=[])
    window.core.api.openai.remote_tools = SimpleNamespace()
    window.core.api.openai.remote_tools.append_to_tools = MagicMock(side_effect=lambda mode, model, stream, is_expert_call, tools, preset: tools)
    window.core.api.openai.vision = SimpleNamespace()
    window.core.api.openai.vision.build_content = MagicMock(side_effect=lambda content, attachments, responses_api: "vision_" + content)
    window.core.api.openai.vision.get_attachment = MagicMock(return_value="base64img")
    window.core.api.openai.audio = SimpleNamespace()
    window.core.api.openai.audio.build_content = MagicMock(side_effect=lambda content, multimodal_ctx: "audio_" + content)
    window.core.api.openai.computer = SimpleNamespace()
    window.core.api.openai.computer.handle_action = MagicMock(return_value=(["dummy_tool_call"], True))
    window.core.api.openai.container = SimpleNamespace()
    window.core.api.openai.container.download_files = MagicMock()
    window.core.tokens = SimpleNamespace()
    window.core.tokens.from_messages = MagicMock(return_value=5)
    window.core.tokens.from_user = MagicMock(return_value=10)
    window.core.ctx = SimpleNamespace()
    window.core.ctx.get_history = MagicMock(return_value=[])
    window.core.ctx.save = MagicMock()
    window.core.command = SimpleNamespace()
    window.core.command.unpack_tool_calls_responses = MagicMock(return_value=["tool_response"])
    window.core.command.unpack_tool_calls_chunks = MagicMock()
    window.core.image = SimpleNamespace()
    window.core.image.gen_unique_path = MagicMock(return_value="dummy_image.png")
    window.core.debug = SimpleNamespace()
    window.core.debug.info = MagicMock()
    window.core.debug.error = MagicMock()
    window.controller = SimpleNamespace()
    window.controller.agent = SimpleNamespace()
    window.controller.agent.legacy = SimpleNamespace(enabled=MagicMock(return_value=True))
    window.controller.agent.experts = SimpleNamespace(enabled=MagicMock(return_value=True))
    return window


@pytest.fixture
def dummy_model():
    model = ModelItem()
    model.id = "gpt-3"
    model.ctx = 100
    model.mode = [MODE_CHAT]
    model.extra = {}
    model.input = ["text"]
    return model


@pytest.fixture
def dummy_context(dummy_model):
    ctx = CtxItem()
    ctx.input_name = "User"
    ctx.output_name = "AI"
    context = SimpleNamespace()
    context.prompt = "test prompt"
    context.stream = False
    context.max_tokens = 50
    context.system_prompt = "system prompt"
    context.mode = MODE_CHAT
    context.model = dummy_model
    context.external_functions = []
    context.attachments = {}
    context.multimodal_ctx = None
    context.is_expert_call = False
    context.preset = None
    context.history = []
    context.ctx = ctx
    return context


@pytest.fixture
def responses_instance(dummy_window):
    return Responses(window=dummy_window)


def test_reset_tokens(responses_instance):
    responses_instance.input_tokens = 123
    responses_instance.reset_tokens()
    assert responses_instance.input_tokens == 0


def test_get_used_tokens(responses_instance):
    responses_instance.input_tokens = 456
    assert responses_instance.get_used_tokens() == 456


def test_build_plain(responses_instance, dummy_window, dummy_model):
    dummy_window.core.config.get = lambda key, default=None: False if key == 'use_context' else (50 if key == 'max_total_tokens' else default)
    dummy_model.input = ["text"]
    res = responses_instance.build("plain", "sys", dummy_model, history=[], attachments={}, ai_name="AI", user_name="User", multimodal_ctx=None, is_expert_call=False)
    assert res[-1]["role"] == "user"
    assert res[-1]["content"] == "plain"
    assert responses_instance.get_used_tokens() == 5


def test_build_image(responses_instance, dummy_window, dummy_model):
    dummy_model.input = ["text", MULTIMODAL_IMAGE]
    res = responses_instance.build("img", "sys", dummy_model, history=[], attachments={"att": attachment_mod.AttachmentItem()}, ai_name="AI", user_name="User", multimodal_ctx=None, is_expert_call=False)
    assert res[-1]["role"] == "user"
    assert res[-1]["content"] == "vision_img"


def test_build_audio(responses_instance, dummy_window, dummy_model):
    dummy_model.input = ["text", MULTIMODAL_AUDIO]
    res = responses_instance.build("aud", "sys", dummy_model, history=[], attachments={}, ai_name="AI", user_name="User", multimodal_ctx="multi", is_expert_call=False)
    assert res[-1]["role"] == "user"
    assert res[-1]["content"] == "audio_aud"


def test_send(responses_instance, dummy_window, dummy_context):
    client = SimpleNamespace()
    client.responses = SimpleNamespace()
    client.responses.create = MagicMock(return_value=SimpleNamespace(id="resp123"))
    dummy_window.core.api.openai.get_client.return_value = client
    dummy_window.core.tokens.from_messages.return_value = 10
    dummy_context.model.ctx = 100
    resp = responses_instance.send(dummy_context)
    assert resp.id == "resp123"
    assert dummy_context.ctx.msg_id == "resp123"


class DummyOutput:
    def __init__(self, type, **kwargs):
        self.type = type
        for k, v in kwargs.items():
            setattr(self, k, v)


class DummyAnnotation:
    def __init__(self, type, **kwargs):
        self.type = type
        for k, v in kwargs.items():
            setattr(self, k, v)


def test_unpack_response(responses_instance, dummy_window):
    usage = SimpleNamespace(input_tokens=3, output_tokens=5)
    out_img = DummyOutput("image_generation_call", result=base64.b64encode(b"imagebytes").decode("utf-8"))
    out_code = DummyOutput("code_interpreter_call", code="print('hello')")
    ann_url = DummyAnnotation("url_citation", url="http://example.com")
    ann_file = DummyAnnotation("container_file_citation", container_id="cid", file_id="fid")
    content_item = SimpleNamespace(annotations=[ann_url, ann_file])
    out_msg = DummyOutput("message", content=[content_item])
    pending = [SimpleNamespace(id="p1", code="C1", message="msg1")]
    out_comp = DummyOutput("computer_call", id="comp1", call_id="call1", action="act", pending_safety_checks=pending)
    summary_item = SimpleNamespace(type="summary_text", text="summary text")
    out_reason = DummyOutput("reasoning", summary=[summary_item])
    out_mcp_list = DummyOutput("mcp_list_tools", tools=["tool1", "tool2"])
    out_mcp_call = DummyOutput("mcp_call", id="mcp1", approval_request_id="app1", arguments={"a": 1}, error=None, name="mcp", output="out", server_label="lab")
    out_mcp_approval = DummyOutput("mcp_approval_request", id="mcp2", arguments={"b": 2}, name="mcp_app", server_label="lab2")
    response = SimpleNamespace(id="resp001", output_text="Response text", usage=usage, output=[out_img, out_code, out_msg, out_comp, out_reason, out_mcp_list, out_mcp_call, out_mcp_approval])
    ctx = CtxItem()
    ctx.extra = {}
    ctx.meta = SimpleNamespace(id="meta1", extra={})
    ctx.images = []
    ctx.urls = []
    orig_open = open
    m = mock_open()
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr("builtins.open", m)
        responses_instance.unpack_response(MODE_CHAT, response, ctx)
    expected_code = "\n\n**Code interpreter**\n```python\nprint('hello')\n\n```\n-----------\nResponse text"
    assert ctx.output == expected_code
    assert ctx.msg_id == "resp001"
    assert hasattr(ctx, "set_tokens")
    dummy_window.core.command.unpack_tool_calls_chunks.assert_called()
    dummy_window.core.api.openai.container.download_files.assert_called()


def test_unpack_agent_response(responses_instance, dummy_window):
    raw_img = SimpleNamespace(type="image_generation_call", result=base64.b64encode(b"imgdata").decode("utf-8"))
    item_img = SimpleNamespace(type="tool_call_item", raw_item=raw_img)
    raw_code = SimpleNamespace(type="code_interpreter_call", code="print('agent')")
    item_code = SimpleNamespace(type="tool_call_item", raw_item=raw_code)
    ann = DummyAnnotation("url_citation", url="http://agent.com")
    content = SimpleNamespace(annotations=[ann])
    raw_msg = SimpleNamespace(type="message", content=[content])
    item_msg = SimpleNamespace(type="message_output_item", raw_item=raw_msg)
    result = SimpleNamespace(final_output="final output", last_response_id="agent_resp", new_items=[item_img, item_code, item_msg])
    ctx = CtxItem()
    ctx.extra = {}
    ctx.urls = []
    orig_open = open
    m = mock_open()
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr("builtins.open", m)
        final, resp_id = responses_instance.unpack_agent_response(result, ctx)
    expected_code = "\n\n**Code interpreter**\n```python\nprint('agent')\n\n```\n-----------\nfinal output"
    assert final == expected_code
    assert resp_id == "agent_resp"


def test_is_enabled(responses_instance, dummy_window, dummy_model):
    res = responses_instance.is_enabled(dummy_model, MODE_COMPUTER)
    assert res is True
    dummy_model.id = "gpt-3"
    dummy_window.core.config.get = lambda key, default=None: {"api_use_responses": True, "agent.api_use_responses": True, "experts.api_use_responses": True, "experts.internal.api_use_responses": True}.get(key, default)
    res = responses_instance.is_enabled(dummy_model, MODE_CHAT, MODE_CHAT, is_expert_call=False)
    assert res is True
    dummy_window.controller.agent.legacy.enabled = MagicMock(return_value=True)
    dummy_window.core.config.get = lambda key, default=None: False if key == "agent.api_use_responses" else True
    res = responses_instance.is_enabled(dummy_model, MODE_CHAT, MODE_CHAT, is_expert_call=False)
    assert res is False
    dummy_window.controller.agent.experts.enabled = MagicMock(return_value=True)
    dummy_window.core.config.get = lambda key, default=None: False if key == "experts.api_use_responses" else True
    res = responses_instance.is_enabled(dummy_model, MODE_CHAT, MODE_CHAT, is_expert_call=False)
    assert res is False
    dummy_window.core.config.get = lambda key, default=None: False if key == "experts.internal.api_use_responses" else True
    res = responses_instance.is_enabled(dummy_model, MODE_CHAT, MODE_CHAT, is_expert_call=True)
    assert res is False
    preset = PresetItem()
    preset.remote_tools = ["tool"]
    res = responses_instance.is_enabled(dummy_model, MODE_CHAT, MODE_CHAT, is_expert_call=True, preset=preset)
    assert res is True