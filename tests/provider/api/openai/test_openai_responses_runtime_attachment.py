#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.core.types import MODE_CHAT, MULTIMODAL_IMAGE
from pygpt_net.item.attachment import AttachmentItem
from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.model import ModelItem
from pygpt_net.provider.api.openai.responses import Responses


def _window(history):
    config = {
        "func_call.native": True,
        "max_total_tokens": 128000,
        "use_context": True,
    }
    window = SimpleNamespace()
    window.core = SimpleNamespace()
    window.core.config = SimpleNamespace(get=lambda key, default=None: config.get(key, default))
    window.core.tokens = SimpleNamespace(from_user=MagicMock(return_value=1))
    window.core.ctx = SimpleNamespace(get_history=MagicMock(return_value=history))
    window.core.context_manager = SimpleNamespace(
        should_break_server_chain=MagicMock(return_value=False),
    )
    window.core.attachments = SimpleNamespace(
        native=SimpleNamespace(get_refs=MagicMock(return_value=[])),
    )
    window.core.api = SimpleNamespace()
    window.core.api.openai = SimpleNamespace()
    window.core.api.openai.vision = SimpleNamespace(
        is_image=MagicMock(return_value=True),
        build_content=MagicMock(return_value=[
            {"type": "input_text", "text": "Attached for native analysis"},
            {"type": "input_image", "image_url": "data:image/png;base64,abc"},
        ]),
    )
    window.core.api.openai.audio = SimpleNamespace(build_content=MagicMock())
    return window


def _model():
    model = ModelItem()
    model.id = "gpt-5.6-luna"
    model.ctx = 128000
    model.mode = [MODE_CHAT]
    model.input = ["text", MULTIMODAL_IMAGE]
    return model


def test_runtime_image_is_embedded_in_function_call_output(tmp_path):
    image = tmp_path / "painter.png"
    image.write_bytes(b"png")

    previous = CtxItem()
    previous.input = "make an animation"
    previous.output = "tool call pending"
    previous.msg_id = "resp_previous"
    previous.cmds = [{"cmd": "attach_runtime_file"}]
    previous.extra = {
        "tool_calls": [{
            "id": "fc_attach",
            "call_id": "call_attach",
            "type": "function",
            "function": {
                "name": "attach_runtime_file",
                "arguments": {"path": [str(image)]},
            },
        }],
        "tool_output": [{
            "cmd": "attach_runtime_file",
            "result": "Attached for native analysis in the next model request: painter.png",
        }],
    }

    attachment = AttachmentItem()
    attachment.path = str(image)
    attachment.extra = {
        "runtime_tool_attachment": True,
        "append_to_ctx": False,
    }
    attachments = {"runtime": attachment}

    window = _window([previous])
    responses = Responses(window=window)
    messages = responses.build(
        prompt="tool continuation",
        system_prompt="",
        model=_model(),
        history=[previous],
        attachments=attachments,
        current_ctx=CtxItem(),
    )

    assert responses.prev_response_id == "resp_previous"
    assert len(messages) == 1
    assert messages[0]["type"] == "function_call_output"
    assert messages[0]["call_id"] == "call_attach"
    assert messages[0]["output"] == [
        {"type": "input_text", "text": "Attached for native analysis"},
        {"type": "input_image", "image_url": "data:image/png;base64,abc"},
    ]
    assert not any(message.get("role") == "user" for message in messages)
    window.core.api.openai.vision.build_content.assert_called_once()
