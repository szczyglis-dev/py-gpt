"""Worker starts attach to their launching partial and do not launch duplicates."""
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

from pygpt_net.core.agents_v2.workers import WorkerRuntime
from pygpt_net.core.agents_v2.state import WorkerState, WorkerStatus
from pygpt_net.item.ctx import CtxItem


def test_identity_and_start_validation_then_launch():
    async def scenario():
        rt = MagicMock()
        rt.is_stopped.return_value = False
        rt.finished = False
        rt.workflow.final_requested = False
        rt.is_swarm_mode = True
        workers = WorkerRuntime(rt)
        first, second = workers.next_id(), workers.next_id()
        assert first.startswith('w01_') and second.startswith('w02_')
        assert workers.number(second) == 2
        assert workers.number('invalid') == 1
        workers.numbers['custom'] = 8
        assert workers.number('custom') == 8
        assert 'error' in json.loads(await workers.start('missing', 'task'))
        state = WorkerState(id=first, name='Worker', instruction='work', language='en', system_prompt='',
                            agent=None, memory=None, tool_ctx=CtxItem())
        workers.states[first] = state
        assert 'error' in json.loads(await workers.start(first, ' '))
        workers.execution.run = AsyncMock(return_value='done')
        result = json.loads(await workers.start(first, ' task '))
        assert result['id'] == first
        assert state.status == WorkerStatus.RUNNING and state.current_task == 'task'
        assert state.generation == 1 and workers.launched_count == 1
        assert workers.parent_parts[first] is rt.timeline.part.return_value
        assert 'error' in json.loads(await workers.start(first, 'again'))
        await state.task
        workers.execution.run.assert_awaited_once_with(state, 'task')
        rt.finished = True
        assert 'error' in json.loads(await workers.start(first, 'again'))
    asyncio.run(scenario())
