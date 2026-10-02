"""Specialist execution completion, cancellation and durable cleanup contracts."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from pygpt_net.core.agents_v2.execution.worker import WorkerExecution
from pygpt_net.core.agents_v2.state import WorkerState, WorkerStatus


class Handler:
    def __init__(self, events=(), output='done', error=None):
        self.events, self.output, self.error = events, output, error
        self.cancel_run = AsyncMock()

    async def stream_events(self):
        for event in self.events:
            yield event

    def __await__(self):
        async def result():
            if self.error:
                raise self.error
            return self.output
        return result().__await__()


def setup_execution(handler):
    rt = MagicMock()
    rt.is_stopped.return_value = False
    rt.shared_context_text = 'attachments'
    rt.main_agent_name = 'Primary'
    rt.worker_max_iterations = 12
    rt.inputs.message.side_effect = lambda text: text
    state = WorkerState(id='w', name='Writer', instruction='write', language='en', system_prompt='',
                        agent=SimpleNamespace(run=MagicMock(return_value=handler), llm='llm'), memory=object(), tool_ctx=object())
    state.status = WorkerStatus.RUNNING
    store = MagicMock()
    return rt, state, store, WorkerExecution(rt, store)


@pytest.mark.parametrize('flag,outcome,error_text', [('normal', '', ''), ('iteration_limit_reached', '', 'iteration limit'),
    ('stalled', '', 'unchanged checkpoint'), ('normal', 'blocked', 'requires assistance'), ('normal', 'needs_input', 'requires assistance')])
def test_complete_projects_failure_flags_and_always_persists(flag, outcome, error_text):
    handler = Handler([SimpleNamespace(), SimpleNamespace()], 'answer')
    rt, state, store, execution = setup_execution(handler)
    setattr(state.agent, flag, True)
    state.agent.completion_outcome = outcome
    assert asyncio.run(execution.run(state, 'task')) == 'answer'
    assert state.last_result == 'answer'
    assert state.status == (WorkerStatus.FAILED if error_text else WorkerStatus.COMPLETED)
    assert error_text in state.error
    store.assert_called_once_with(state)
    kwargs = state.agent.run.call_args.kwargs
    assert kwargs['memory'] is state.memory and kwargs['max_iterations'] == 12
    assert 'shared user attachments' in kwargs['user_msg']
    assert rt.timeline.consume.call_count == 2
    assert rt.window.core.api.logger.log_output.call_args.kwargs['chunks'] == 2


@pytest.mark.parametrize('failure', ['stopped', 'requested', 'exception', 'cancelled'])
def test_interruption_and_errors_finalize_without_raising(failure):
    handler = Handler([SimpleNamespace()], error=RuntimeError('bad') if failure == 'exception' else None)
    rt, state, store, execution = setup_execution(handler)
    if failure == 'stopped':
        rt.is_stopped.return_value = True
    elif failure == 'requested':
        state.stop_requested = True
    elif failure == 'cancelled':
        state.agent.run.side_effect = asyncio.CancelledError()
    assert asyncio.run(execution.run(state, 'task')) == ''
    assert state.status == (WorkerStatus.FAILED if failure == 'exception' else WorkerStatus.STOPPED)
    store.assert_called_once_with(state)
    if failure in ('stopped', 'requested'):
        assert handler.cancel_run.await_count >= 1
    if failure == 'exception':
        assert state.error == 'bad'
        rt.window.core.debug.log.assert_called_once()
