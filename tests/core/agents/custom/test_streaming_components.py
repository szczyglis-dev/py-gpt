"""Chunk boundaries and routing metadata must not leak into displayed prose."""
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from openai.types.responses import ResponseTextDeltaEvent, ResponseCreatedEvent, ResponseCompletedEvent

from pygpt_net.core.agents.custom.router_streamer import DelayedRouterStreamer, RealtimeRouterStreamer
from pygpt_net.core.agents.custom.llama_index.router_streamer import DelayedRouterStreamerLI, RealtimeRouterStreamerLI
from pygpt_net.core.agents.custom.llama_index.stream import LIStreamHandler
from pygpt_net.core.agents.custom.logging import NullLogger, StdLogger
from pygpt_net.item.ctx import CtxItem


@pytest.mark.parametrize('text', ['Hello', 'Zażółć 😀\nnext', 'quote " and slash \\'])
@pytest.mark.parametrize('chunk_size', [1, 3, 100])
def test_li_realtime_decodes_content_across_chunk_boundaries(text, chunk_size):
    raw = json.dumps({'route': 'hidden', 'content': text})
    streamer = RealtimeRouterStreamerLI()
    pieces = [streamer.handle_delta(raw[i:i+chunk_size]) for i in range(0, len(raw), chunk_size)]
    assert ''.join(pieces) == text
    assert streamer.buffer == raw
    assert streamer.handle_delta('') == ''
    streamer.reset()
    assert streamer.buffer == ''
    assert streamer.handle_delta('{"content":"second"}') == 'second'


def test_delayed_li_and_stream_handler_reset_and_flush_contracts():
    delayed = DelayedRouterStreamerLI()
    delayed.handle_delta('a')
    delayed.handle_delta(None)
    assert delayed.buffer == 'a'
    delayed.reset()
    assert delayed.buffer == ''
    bridge, ctx = MagicMock(), CtxItem()
    stream = LIStreamHandler(bridge)
    assert stream.handle_token('', ctx) == ('', None)
    assert stream.handle_token('first', ctx) == ('first', None)
    bridge.on_step.assert_called_once_with(ctx, True)
    bridge.on_step.reset_mock()
    assert stream.handle_token('second', ctx, flush=False, buffer=False) == ('first', None)
    bridge.on_step.assert_not_called()
    stream.handle_token('third', ctx)
    bridge.on_step.assert_called_once_with(ctx, False)
    stream.reset()
    assert stream.buffer == '' and stream.begin is False
    stream.new()
    assert stream.begin is True


def test_openai_delayed_retains_last_nonempty_response_id():
    with patch('pygpt_net.core.agents.custom.router_streamer.StreamHandler') as handler:
        stream = DelayedRouterStreamer(MagicMock(), MagicMock())
    handler.return_value.buffer = 'raw'
    handler.return_value.handle.side_effect = [('raw', 'response'), ('raw', None)]
    assert stream.handle_event('event', 'ctx') == ('raw', 'response')
    assert stream.handle_event('event', 'ctx') == ('raw', 'response')
    assert stream.buffer == 'raw' and stream.last_response_id == 'response'
    stream.reset()
    assert stream.buffer == '' and stream.last_response_id is None


def test_openai_realtime_only_publishes_decoded_content():
    bridge, handler, ctx = MagicMock(), MagicMock(), CtxItem()
    stream = RealtimeRouterStreamer(MagicMock(), bridge, handler)
    stream.handle_event(SimpleNamespace(type='other'), ctx)
    for piece in ['{"route":"secret","con', 'tent":"A\\', 'nB\\"C"', ',"other":"ignored"}']:
        event = ResponseTextDeltaEvent.model_construct(delta=piece)
        stream.handle_event(SimpleNamespace(type='raw_response_event', data=event), ctx)
    assert stream.buffer == '{"route":"secret","content":"A\\nB\\"C","other":"ignored"}'
    assert ''.join(c.args[0] for c in handler.to_buffer.call_args_list) == 'A\nB"C'
    stream.handle_event(SimpleNamespace(type='raw_response_event', data=ResponseCreatedEvent.model_construct(response=SimpleNamespace(id='r'))), ctx)
    stream.handle_event(SimpleNamespace(type='raw_response_event', data=ResponseCompletedEvent.model_construct()), ctx)
    assert stream.last_response_id == 'r'
    stream.reset()
    assert stream.buffer == '' and stream.last_response_id is None


@pytest.mark.parametrize('logger_cls', [NullLogger, StdLogger])
@pytest.mark.parametrize('level', ['debug', 'info', 'warning', 'error'])
def test_logger_levels(logger_cls, level, capsys):
    logger = logger_cls()
    getattr(logger, level)('message', unused=True)
    assert capsys.readouterr().out == (f'[flow] {level.upper()}: message\n' if logger_cls is StdLogger else '')


def test_li_stream_manual_buffer_does_not_emit():
    bridge = MagicMock()
    stream = LIStreamHandler(bridge)
    stream.to_buffer('manual')
    stream.to_buffer('')
    assert stream.buffer == 'manual'
    bridge.on_step.assert_not_called()


def test_openai_realtime_defers_split_unicode_surrogate_pairs():
    bridge, handler, ctx = MagicMock(), MagicMock(), CtxItem()
    stream = RealtimeRouterStreamer(MagicMock(), bridge, handler)
    raw = json.dumps({'content': '😀 next'})
    for character in raw:
        event = ResponseTextDeltaEvent.model_construct(delta=character)
        stream.handle_event(SimpleNamespace(type='raw_response_event', data=event), ctx)
    assert ''.join(call.args[0] for call in handler.to_buffer.call_args_list) == '😀 next'
