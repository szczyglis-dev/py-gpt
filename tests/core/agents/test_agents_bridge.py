from unittest.mock import MagicMock

from pygpt_net.core.agents.bridge import ConnectionContext


def test_connection_context_keeps_all_callbacks():
    callbacks = [MagicMock() for _ in range(6)]
    ctx = ConnectionContext(
        stopped=callbacks[0],
        on_step=callbacks[1],
        on_stop=callbacks[2],
        on_error=callbacks[3],
        on_next=callbacks[4],
        on_next_ctx=callbacks[5],
    )
    assert [ctx.stopped, ctx.on_step, ctx.on_stop, ctx.on_error, ctx.on_next, ctx.on_next_ctx] == callbacks


def test_connection_context_allows_empty_callbacks():
    ctx = ConnectionContext()
    assert ctx.stopped is None
    assert ctx.on_step is None
    assert ctx.on_stop is None
    assert ctx.on_error is None
    assert ctx.on_next is None
    assert ctx.on_next_ctx is None
