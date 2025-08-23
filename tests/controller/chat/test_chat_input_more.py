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
import os
from unittest.mock import MagicMock, call, ANY
import pytest
from pygpt_net.core.events import Event, AppEvent, KernelEvent, RenderEvent
from pygpt_net.core.bridge import BridgeContext
from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_AGENT_LLAMA,
    MODE_AGENT_OPENAI,
    MODE_LLAMA_INDEX,
    MODE_ASSISTANT,
    MODE_IMAGE,
    MODE_CHAT,
)
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans
from pygpt_net.controller.chat.input import Input

def create_dummy_window():
    win = MagicMock()
    win.ui = MagicMock()
    win.ui.nodes = {'input': MagicMock()}
    win.ui.nodes['input'].toPlainText = MagicMock(return_value="dummy text")
    win.ui.dialogs = MagicMock()
    win.ui.dialogs.alert = MagicMock()
    win.controller = MagicMock()
    win.controller.agent = MagicMock()
    win.controller.agent.experts = MagicMock()
    win.controller.agent.experts.unlock = MagicMock()
    win.controller.agent.llama = MagicMock()
    win.controller.agent.llama.reset_eval_step = MagicMock()
    win.controller.agent.llama.on_user_send = MagicMock()
    win.controller.agent.legacy = MagicMock()
    win.controller.agent.legacy.on_user_send = MagicMock()
    win.controller.agent.legacy.on_input_before = MagicMock(side_effect=lambda x: x)
    win.controller.agent.common = MagicMock()
    win.controller.agent.common.is_infinity_loop = MagicMock(return_value=False)
    win.controller.agent.common.display_infinity_loop_confirm = MagicMock()
    win.controller.presets = MagicMock()
    preset = MagicMock()
    preset.name = "preset"
    win.controller.presets.get_current = MagicMock(return_value=preset)
    win.controller.ctx = MagicMock()
    win.controller.ctx.extra = MagicMock()
    win.controller.ctx.extra.is_editing = MagicMock(return_value=False)
    win.controller.ctx.extra.edit_submit = MagicMock()
    win.controller.ctx.update = MagicMock()
    win.controller.ctx.handle_allowed = MagicMock()
    win.controller.ctx.update_mode_in_current = MagicMock()
    win.controller.ui = MagicMock()
    win.controller.ui.tabs = MagicMock()
    win.controller.ui.tabs.switch_to_first_chat = MagicMock()
    win.controller.ui.vision = MagicMock()
    win.controller.ui.vision.has_vision = MagicMock(return_value=False)
    win.controller.camera = MagicMock()
    win.controller.camera.handle_auto_capture = MagicMock()
    win.controller.assistant = MagicMock()
    win.controller.assistant.threads = MagicMock()
    win.controller.assistant.threads.stop = False
    win.controller.kernel = MagicMock()
    win.controller.kernel.stop = MagicMock()
    win.controller.kernel.resume = MagicMock()
    win.controller.chat = MagicMock()
    win.controller.chat.log = MagicMock()
    win.controller.chat.image = MagicMock()
    win.controller.chat.image.send = MagicMock()
    win.controller.chat.text = MagicMock()
    win.controller.chat.text.send = MagicMock()
    win.controller.chat.attachment = MagicMock()
    win.controller.chat.attachment.has = MagicMock(return_value=False)
    win.controller.chat.attachment.handle = MagicMock()
    win.controller.chat.common = MagicMock()
    win.controller.chat.common.check_api_key = MagicMock(return_value=True)
    win.core = MagicMock()
    win.core.config = MagicMock()
    win.core.config.get = MagicMock(side_effect=lambda key: {
        'mode': MODE_CHAT,
        'model': None,
        'assistant': "assistant_value",
        'send_clear': False,
    }.get(key, None))
    win.core.models = MagicMock()
    win.core.models.get = MagicMock(return_value=None)
    win.core.models.ollama = MagicMock()
    win.core.models.ollama.check_model = MagicMock(return_value={'is_installed': True, 'is_model': True})
    win.core.ctx = MagicMock()
    win.core.ctx.count_meta = MagicMock(return_value=1)
    win.core.ctx.get_current = MagicMock(return_value="ctx")
    win.dispatch = MagicMock()
    return win

def test_send_input_edit_mode():
    win = create_dummy_window()
    win.controller.ctx.extra.is_editing.return_value = True
    win.ui.nodes['input'].toPlainText.return_value = "edit text"
    inp = Input(win)
    inp.send_input(force=False)

def test_send_input_infinity_loop():
    win = create_dummy_window()
    win.controller.ctx.extra.is_editing.return_value = False
    win.controller.agent.common.is_infinity_loop.return_value = True
    win.ui.nodes['input'].toPlainText.return_value = "infinity loop text"
    inp = Input(win)
    inp.send_input(force=False)

def test_send_input_agent_not_selected():
    win = create_dummy_window()
    win.controller.ctx.extra.is_editing.return_value = False
    win.controller.agent.common.is_infinity_loop.return_value = False
    win.core.config.get = MagicMock(side_effect=lambda key: {
        'mode': MODE_AGENT_OPENAI,
        'model': None,
        'assistant': "assistant_value",
        'send_clear': False,
    }.get(key, None))
    preset = MagicMock()
    preset.name = "*"
    win.controller.presets.get_current.return_value = preset
    win.ui.nodes['input'].toPlainText.return_value = "agent not selected"
    inp = Input(win)
    inp.send_input(force=False)

def test_send_input_model_not_installed():
    win = create_dummy_window()
    win.controller.ctx.extra.is_editing.return_value = False
    win.controller.agent.common.is_infinity_loop.return_value = False
    win.core.config.get = MagicMock(side_effect=lambda key: {
        'mode': MODE_LLAMA_INDEX,
        'model': "model123",
        'assistant': "assistant_value",
        'send_clear': False,
    }.get(key, None))
    model_data = MagicMock()
    model_data.is_ollama.return_value = True
    model_data.get_ollama_model.return_value = "ollama_model"
    model_data.llama_index = {'env': [{'name': 'TEST', 'value': '123'}]}
    win.core.models.get.return_value = model_data
    win.core.models.ollama.check_model.return_value = {'is_installed': False, 'is_model': True}
    win.ui.nodes['input'].toPlainText.return_value = "model test"
    inp = Input(win)
    inp.send_input(force=False)

def test_send_input_model_not_found():
    win = create_dummy_window()
    win.controller.ctx.extra.is_editing.return_value = False
    win.controller.agent.common.is_infinity_loop.return_value = False
    win.core.config.get = MagicMock(side_effect=lambda key: {
        'mode': MODE_LLAMA_INDEX,
        'model': "model123",
        'assistant': "assistant_value",
        'send_clear': False,
    }.get(key, None))
    model_data = MagicMock()
    model_data.is_ollama.return_value = True
    model_data.get_ollama_model.return_value = "ollama_model"
    model_data.llama_index = {'env': [{'name': 'TEST', 'value': '123'}]}
    win.core.models.get.return_value = model_data
    win.core.models.ollama.check_model.return_value = {'is_installed': True, 'is_model': False}
    win.ui.nodes['input'].toPlainText.return_value = "model test"
    inp = Input(win)
    inp.send_input(force=False)

def test_send_input_agent_mode():
    win = create_dummy_window()
    win.controller.ctx.extra.is_editing.return_value = False
    win.controller.agent.common.is_infinity_loop.return_value = False
    win.ui.nodes['input'].toPlainText.return_value = "hello"
    win.core.config.get = MagicMock(return_value=MODE_AGENT)
    win.controller.chat.attachment.has.return_value = False
    inp = Input(win)
    inp.generating = False
    inp.send_input(force=False)
    calls = [c for c in win.dispatch.call_args_list if c[0][0].__class__.__name__ == "Event" and c[0][0].data.get("value") == "hello"]
    assert calls

def test_send_input_agent_llama_mode():
    win = create_dummy_window()
    win.controller.ctx.extra.is_editing.return_value = False
    win.controller.agent.common.is_infinity_loop.return_value = False
    win.ui.nodes['input'].toPlainText.return_value = "hello"
    win.core.config.get = MagicMock(return_value=MODE_AGENT_LLAMA)
    win.controller.chat.attachment.has.return_value = False
    inp = Input(win)
    inp.send_input(force=False)

def test_send_input_attachments_success():
    win = create_dummy_window()
    win.ui.nodes['input'].toPlainText.return_value = "attachment text"
    win.core.config.get = MagicMock(return_value=MODE_CHAT)
    win.controller.chat.attachment.has.return_value = True
    inp = Input(win)
    inp.send_input(force=False)
    calls = win.dispatch.call_args_list
    found_busy = any(isinstance(arg[0], KernelEvent) and arg[0].data.get("msg") == "Reading attachments..." for arg, _ in calls)
    assert found_busy
    win.controller.chat.attachment.handle.assert_called_once_with(MODE_CHAT, "attachment text")

def test_send_input_attachments_error():
    win = create_dummy_window()
    win.ui.nodes['input'].toPlainText.return_value = "attachment error"
    win.core.config.get = MagicMock(return_value=MODE_CHAT)
    win.controller.chat.attachment.has.return_value = True
    win.controller.chat.attachment.handle.side_effect = Exception("error")
    inp = Input(win)
    inp.send_input(force=False)
    calls = win.dispatch.call_args_list
    found_error = any(isinstance(arg[0], KernelEvent) and arg[0].data.get("msg", "").startswith("Error reading attachments:") for arg, _ in calls)
    assert found_error

def test_send_calls_execute():
    win = create_dummy_window()
    inp = Input(win)
    context = MagicMock(spec=BridgeContext)
    context.prompt = "dummy prompt"
    context.ctx = "prev_ctx"
    context.multimodal_ctx = "mm_ctx"
    inp.execute = MagicMock()
    extra = {"force": True, "reply": True, "internal": True, "parent_id": 42}
    inp.send(context, extra)
    inp.execute.assert_called_once_with(
        text="dummy prompt",
        force=True,
        reply=True,
        internal=True,
        prev_ctx="prev_ctx",
        multimodal_ctx="mm_ctx",
    )

def test_execute_assistant_no_assistant():
    win = create_dummy_window()
    inp = Input(win)
    inp.locked = False
    win.core.config.get = MagicMock(side_effect=lambda key: {
        'mode': MODE_ASSISTANT,
        'assistant': "",
        'send_clear': False,
        'model': None,
    }.get(key, None))
    inp.execute(text="test", force=False, reply=False, internal=False, prev_ctx=None, multimodal_ctx=None)

def test_execute_handle_allowed():
    win = create_dummy_window()
    inp = Input(win)
    inp.locked = False
    win.core.config.get = MagicMock(side_effect=lambda key: {
        'mode': MODE_CHAT,
        'assistant': "assistant_value",
        'send_clear': False,
        'model': None,
    }.get(key, None))
    win.controller.ui.vision.has_vision.return_value = False
    win.core.ctx.count_meta.return_value = 1
    win.core.ctx.get_current.return_value = "ctx"
    mm_ctx = MagicMock()
    mm_ctx.is_audio_input = False
    inp.execute(text="non empty", force=True, reply=False, internal=False, prev_ctx="prev", multimodal_ctx=mm_ctx)
    win.controller.chat.text.send.assert_called_once_with(text="non empty", reply=False, internal=False, prev_ctx="prev", multimodal_ctx=ANY)

def test_execute_empty_text():
    win = create_dummy_window()
    inp = Input(win)
    inp.locked = False
    win.core.config.get = MagicMock(return_value=MODE_CHAT)
    win.controller.ui.vision.has_vision.return_value = False
    mm_ctx = MagicMock()
    mm_ctx.is_audio_input = False
    inp.execute(text="   ", force=False, reply=False, internal=False, prev_ctx=None, multimodal_ctx=mm_ctx)

def test_execute_mode_image():
    win = create_dummy_window()
    inp = Input(win)
    inp.locked = False
    win.core.config.get = MagicMock(side_effect=lambda key: {
        'mode': MODE_IMAGE,
        'assistant': "assistant_value",
        'send_clear': False,
        'model': None,
    }.get(key, None))
    win.controller.ui.vision.has_vision.return_value = False
    mm_ctx = MagicMock()
    mm_ctx.is_audio_input = False
    inp.execute(text="image text", force=True, reply=False, internal=False, prev_ctx="ctx_prev", multimodal_ctx=mm_ctx)
    win.controller.chat.image.send.assert_called_once_with(text="image text", prev_ctx="ctx_prev")
    win.controller.chat.text.send.assert_not_called()

def test_execute_agent_mode():
    win = create_dummy_window()
    inp = Input(win)
    inp.locked = False
    win.core.config.get = MagicMock(side_effect=lambda key: {
        'mode': MODE_AGENT,
        'assistant': "assistant_value",
        'send_clear': False,
        'model': None,
    }.get(key, None))
    win.controller.ui.vision.has_vision.return_value = False
    win.controller.agent.legacy.on_input_before.side_effect = lambda x: "modified " + x
    mm_ctx = MagicMock()
    mm_ctx.is_audio_input = False
    inp.execute(text="agent test", force=True, reply=True, internal=False, prev_ctx="prev", multimodal_ctx=mm_ctx)

def test_execute_internal_override_locked():
    win = create_dummy_window()
    inp = Input(win)
    inp.locked = True
    win.core.config.get = MagicMock(side_effect=lambda key: {
        'mode': MODE_CHAT,
        'assistant': "assistant_value",
        'send_clear': False,
        'model': None,
    }.get(key, None))
    win.controller.ui.vision.has_vision.return_value = False
    mm_ctx = MagicMock()
    mm_ctx.is_audio_input = False
    inp.execute(text="internal", force=False, reply=False, internal=True, prev_ctx=None, multimodal_ctx=mm_ctx)
    win.controller.kernel.resume.assert_called_once()
    win.controller.chat.text.send.assert_called_once()