import io
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from pygpt_net.controller.chat.stream_worker import StreamWorker, WorkerState
from pygpt_net.core.types.chunk import ChunkType


def _worker():
    worker = StreamWorker.__new__(StreamWorker)
    worker.window = MagicMock()
    worker.ctx = MagicMock()
    worker.stream = None
    worker.signals = MagicMock()
    return worker


@pytest.mark.parametrize(
    ('chunk', 'expected'),
    [
        (SimpleNamespace(choices=[SimpleNamespace(delta='x')]), ChunkType.API_CHAT),
        (SimpleNamespace(choices=[SimpleNamespace(text='x')]), ChunkType.API_COMPLETION),
        ((object(), SimpleNamespace(content='x')), ChunkType.XAI_SDK),
        (SimpleNamespace(type='message_delta'), ChunkType.ANTHROPIC),
        (SimpleNamespace(candidates=[]), ChunkType.GOOGLE),
        (SimpleNamespace(content='hello'), ChunkType.LANGCHAIN_CHAT),
        (SimpleNamespace(delta='hello'), ChunkType.LLAMA_CHAT),
        (object(), ChunkType.RAW),
    ],
)
def test_stream_worker_detects_provider_chunk_shapes_without_network(chunk, expected):
    assert _worker()._detect_chunk_type(chunk) == expected


def test_stream_worker_should_stop_closes_generator_and_marks_context():
    worker = _worker()
    ctrl = MagicMock()
    ctrl.kernel.stopped.return_value = True
    gen = MagicMock()
    state = WorkerState(generator=gen)
    ctx = SimpleNamespace(msg_id='m1', extra={})

    assert worker._should_stop(ctrl, state, ctx) is True
    gen.close.assert_called_once_with()
    assert ctx.msg_id is None
    assert state.stopped is True


def test_stream_worker_should_stop_is_false_when_kernel_is_running():
    worker = _worker()
    ctrl = MagicMock()
    ctrl.kernel.stopped.return_value = False
    state = WorkerState(generator=MagicMock())
    ctx = SimpleNamespace(msg_id='m1', extra={})
    assert worker._should_stop(ctrl, state, ctx) is False
    state.generator.close.assert_not_called()


def test_stream_worker_append_response_buffers_counts_and_emits():
    worker = _worker()
    state = WorkerState()
    emit = MagicMock()
    ctx = object()

    worker._append_response(ctx, state, 'abc', emit)
    worker._append_response(ctx, state, 'def', emit)

    assert state.out.getvalue() == 'abcdef'
    assert state.output_tokens == 2
    assert emit.call_args_list[0].args == (ctx, 'abc', True)
    assert emit.call_args_list[1].args == (ctx, 'def', False)


def test_stream_worker_after_loop_normalizes_tool_arguments_and_images():
    worker = _worker()
    ctx = SimpleNamespace(force_call=False, images=[], urls=None)
    core = MagicMock()
    state = WorkerState(
        tool_calls=[{'function': {'name': 'x', 'arguments': {'a': 1}}}],
        force_func_call=True,
        image_paths=['a.png', 'a.png', 'b.png'],
    )

    worker._handle_after_loop(ctx, core, state)

    assert ctx.force_call is True
    assert state.tool_calls[0]['function']['arguments'] == '{"a": 1}'
    core.command.unpack_tool_calls_chunks.assert_called_once_with(ctx, state.tool_calls)
    assert ctx.images == ['a.png', 'a.png', 'b.png']


def test_worker_state_defaults_are_per_instance():
    a, b = WorkerState(), WorkerState()
    a.tool_calls.append({'id': 1})
    a.image_paths.append('a')
    assert b.tool_calls == []
    assert b.image_paths == []


def test_stream_worker_cleanup_releases_signal_object():
    worker = _worker()
    sig = MagicMock()
    worker.signals = sig
    worker.cleanup()
    assert worker.signals is None
    sig.deleteLater.assert_called_once_with()


def test_stream_worker_run_with_no_generator_emits_begin_and_end_without_network():
    worker = _worker()
    ctx = MagicMock()
    ctx.meta = {'id': 1}
    ctx.model = None
    worker.ctx = ctx
    worker.stream = None
    core = worker.window.core
    core.image.gen_unique_path.return_value = '/tmp/image.png'
    core.models.get.return_value = None
    worker._finalize = MagicMock()

    worker.run()

    worker.signals.eventReady.emit.assert_called_once()
    worker._finalize.assert_called_once()
