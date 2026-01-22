#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.03 17:00:00                  #
# ================================================== #
from types import SimpleNamespace

import pytest
from unittest.mock import MagicMock
from pygpt_net.controller.chat.stream import StreamWorker, Stream, MODE_ASSISTANT
from pygpt_net.core.types.chunk import ChunkType


# A generator raising an exception after one chunk.
def fake_stream():
    yield "first chunk"
    raise Exception("Fake error")

def test_stream_worker_run_raw_chunk(monkeypatch):
    # Set up dummy context.
    ctx = MagicMock()
    ctx.meta = {}
    ctx.stream = ["hello"]
    ctx.msg_id = "123"
    ctx.chunk_type = None
    ctx.extra = {}
    ctx.output = ""
    ctx.input_tokens = 5
    ctx.set_tokens = MagicMock()

    # Create dummy window with needed attributes.
    window = MagicMock()
    window.core.image.gen_unique_path.return_value = "dummy_image.png"
    window.core.ctx.update_item = MagicMock()
    window.core.debug.info = MagicMock()
    window.core.debug.error = MagicMock()
    window.core.debug.log = MagicMock()
    window.core.api.openai.computer.handle_stream_chunk.return_value = ([], False)
    window.core.api.openai.container.download_files = MagicMock()
    window.core.command.unpack_tool_calls_chunks = MagicMock()
    window.controller.kernel.stopped.return_value = False
    window.controller.ui.update_tokens = MagicMock()
    window.controller.chat.output.handle_after = MagicMock()
    window.controller.assistant.threads.handle_output_message_after_stream = MagicMock()
    window.controller.chat.response.post_handle = MagicMock()
    window.controller.chat.response.failed = MagicMock()
    window.dispatch = MagicMock()

    end_emitted = []
    event_emitted = []
    error_emitted = []

    worker = StreamWorker(ctx, window)
    worker.stream = ctx.stream
    worker.signals.end.connect(lambda x: end_emitted.append(x))
    worker.signals.eventReady.connect(lambda x: event_emitted.append(x))
    worker.signals.errorOccurred.connect(lambda x: error_emitted.append(x))

    # Patch helper.
    monkeypatch.setattr("pygpt_net.core.text.utils.has_unclosed_code_tag", lambda text: False)
    worker.run()

    assert ctx.output == "hello"
    ctx.set_tokens.assert_called_once_with(ctx.input_tokens, 1)
    window.core.ctx.update_item.assert_called_with(ctx)
    assert len(end_emitted) == 1
    assert len(error_emitted) == 0

def test_stream_worker_run_stopped(monkeypatch):
    ctx = MagicMock()
    ctx.meta = {}
    ctx.stream = ["hello", "world"]
    ctx.msg_id = "123"
    ctx.chunk_type = None
    ctx.extra = {}
    ctx.output = ""
    ctx.input_tokens = 10
    ctx.set_tokens = MagicMock()

    window = MagicMock()
    window.core.image.gen_unique_path.return_value = "dummy_image.png"
    window.core.ctx.update_item = MagicMock()
    window.core.debug.info = MagicMock()
    window.core.debug.error = MagicMock()
    window.core.debug.log = MagicMock()
    window.core.api.openai.computer.handle_stream_chunk.return_value = ([], False)
    window.core.api.openai.container.download_files = MagicMock()
    window.core.command.unpack_tool_calls_chunks = MagicMock()
    window.controller.kernel.stopped.return_value = True
    window.controller.ui.update_tokens = MagicMock()
    window.controller.chat.output.handle_after = MagicMock()
    window.controller.assistant.threads.handle_output_message_after_stream = MagicMock()
    window.controller.chat.response.post_handle = MagicMock()
    window.controller.chat.response.failed = MagicMock()
    window.dispatch = MagicMock()

    end_emitted = []
    event_emitted = []
    error_emitted = []

    worker = StreamWorker(ctx, window)
    worker.signals.end.connect(lambda x: end_emitted.append(x))
    worker.signals.eventReady.connect(lambda x: event_emitted.append(x))
    worker.signals.errorOccurred.connect(lambda x: error_emitted.append(x))
    worker.stream = ctx.stream

    monkeypatch.setattr("pygpt_net.core.text.utils.has_unclosed_code_tag", lambda text: False)
    worker.run()

    assert ctx.output == ""
    assert ctx.msg_id is None
    ctx.set_tokens.assert_called_once_with(ctx.input_tokens, 0)
    window.core.ctx.update_item.assert_called_with(ctx)
    assert len(end_emitted) == 1
    assert len(error_emitted) == 0

def test_stream_worker_run_exception(monkeypatch):
    ctx = MagicMock()
    ctx.meta = {}
    ctx.stream = fake_stream()
    ctx.msg_id = "id123"
    ctx.chunk_type = ChunkType.API_CHAT
    ctx.extra = {}
    ctx.output = ""
    ctx.input_tokens = 1
    ctx.set_tokens = MagicMock()
    ctx.chunk_type = None

    window = MagicMock()
    window.core.image.gen_unique_path.return_value = "dummy_image.png"
    window.core.ctx.update_item = MagicMock()
    window.core.debug.info = MagicMock()
    window.core.debug.error = MagicMock()
    window.core.debug.log = MagicMock()
    window.core.api.openai.computer.handle_stream_chunk.return_value = ([], False)
    window.core.api.openai.container.download_files = MagicMock()
    window.core.command.unpack_tool_calls_chunks = MagicMock()
    window.controller.kernel.stopped.return_value = False
    window.controller.ui.update_tokens = MagicMock()
    window.controller.chat.output.handle_after = MagicMock()
    window.controller.assistant.threads.handle_output_message_after_stream = MagicMock()
    window.controller.chat.response.post_handle = MagicMock()
    window.controller.chat.response.failed = MagicMock()
    window.dispatch = MagicMock()

    end_emitted = []
    error_emitted = []

    worker = StreamWorker(ctx, window)
    worker.signals.end.connect(lambda x: end_emitted.append(x))
    worker.signals.errorOccurred.connect(lambda x: error_emitted.append(x))
    worker.stream = ctx.stream

    monkeypatch.setattr("pygpt_net.core.text.utils.has_unclosed_code_tag", lambda text: False)
    worker.run()

    assert "first chunk" in ctx.output
    ctx.set_tokens.assert_called_once_with(ctx.input_tokens, 1)
    window.core.ctx.update_item.assert_called_with(ctx)
    assert len(end_emitted) == 1
    assert len(error_emitted) == 1

def test_stream_append(monkeypatch):
    ctx = MagicMock()
    ctx.meta = MagicMock()
    ctx.input_tokens = 0
    ctx.set_tokens = MagicMock()

    window = MagicMock()
    # Simulate threadpool.start calling worker.run immediately.
    def start_worker(worker):
        worker.run()
    window.threadpool.start.side_effect = start_worker
    window.core.image.gen_unique_path.return_value = "dummy_image.png"
    window.core.ctx.update_item = MagicMock()
    window.core.debug.info = MagicMock()
    window.dispatch = MagicMock()
    window.controller.kernel.stopped.return_value = False
    window.controller.ui.update_tokens = MagicMock()
    window.controller.chat.output.handle_after = MagicMock()
    window.controller.assistant.threads.handle_output_message_after_stream = MagicMock()
    window.controller.chat.response.post_handle = MagicMock()
    window.controller.chat.response.failed = MagicMock()

    stream_obj = Stream(window)
    monkeypatch.setattr("pygpt_net.core.text.utils.has_unclosed_code_tag", lambda text: False)
    stream_obj.append(ctx, mode="test", is_response=False, reply=False, internal=False, context=None, extra={'key': 'value'})
    assert stream_obj.pids is not None

def test_handleEnd_assistant():
    meta = SimpleNamespace(id=1)
    ctx = SimpleNamespace(meta=meta)
    window = MagicMock()
    window.dispatch = MagicMock()
    window.controller.ui.update_tokens = MagicMock()
    window.controller.chat.output.handle_after = MagicMock()
    window.controller.assistant.threads.handle_output_message_after_stream = MagicMock()
    window.core.ctx.output.get_pid = MagicMock(return_value=1)

    stream_obj = Stream(window)
    stream_obj.pids = {
        1: {
            "ctx": MagicMock(),
            "mode": MODE_ASSISTANT,
            "is_response": False,
            "reply": False,
            "internal": False,
        }
    }

    stream_obj.handleEnd(ctx)
    window.controller.ui.update_tokens.assert_called_once()
    window.dispatch.assert_called_once()
    window.controller.chat.output.handle_after.assert_called_once_with(ctx=ctx, mode=MODE_ASSISTANT, stream=True)
    window.controller.assistant.threads.handle_output_message_after_stream.assert_called_once_with(ctx)

def test_handleEvent():
    window = MagicMock()
    window.dispatch = MagicMock()
    stream_obj = Stream(window)
    dummy_event = MagicMock()
    stream_obj.handleEvent(dummy_event)
    window.dispatch.assert_called_once_with(dummy_event)

def test_handleError():
    window = MagicMock()
    window.core.debug.log = MagicMock()
    window.controller.chat.response.failed = MagicMock()
    window.controller.chat.response.post_handle = MagicMock()
    window.core.ctx.output.get_pid = MagicMock(return_value=1)

    meta = SimpleNamespace(id=1)
    dummy_ctx = SimpleNamespace(meta=meta)
    stream_obj = Stream(window)
    stream_obj.pids = {
        1: {
            "ctx": dummy_ctx,
            "mode": None,
            "is_response": True,
            "reply": False,
            "internal": False,
            "context": "dummy_context",
            "extra": {}
        }
    }
    error = Exception("test error")
    stream_obj.handleError(dummy_ctx, error)
    window.core.debug.log.assert_called_once_with(error)
    window.controller.chat.response.failed.assert_called_once_with("dummy_context", {"error": error})
    window.controller.chat.response.post_handle.assert_called_once_with(ctx=dummy_ctx, mode=None, stream=True, reply=False, internal=False)

def test_log():
    window = MagicMock()
    window.core.debug.info = MagicMock()
    stream_obj = Stream(window)
    data = "log data"
    stream_obj.log(data)
    window.core.debug.info.assert_called_once_with(data)