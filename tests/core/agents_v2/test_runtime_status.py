"""Swarm status projections, rate limiting, and reporter lifecycle."""
import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from pygpt_net.core.agents_v2.status import RuntimeStatus
from pygpt_net.core.agents_v2.state import WorkerStatus


def runtime():
    rt = MagicMock()
    rt.is_swarm_mode = True
    rt.finished = False
    rt.is_stopped.return_value = False
    rt.SWARM_STATUS_INTERVAL = 1
    rt.SWARM_STATUS_MIN_VISIBLE = 0.2
    rt.window.core.config.get.side_effect = lambda key, default=None: default
    rt.workers.states = {}
    rt.workers.expected_count = 3
    rt.workers.created_count = 3
    rt.workers.launched_count = 2
    return rt


@pytest.mark.parametrize('name,number,expected', [(' Writer ', 2, 'Agent 2 — Writer'),
    ('Agent 2 — Writer', 2, 'Agent 2 — Writer'), ('', 0, 'Agent 1 — Worker'), ('Worker #3', 3, 'Worker #3')])
def test_worker_identity_prefix_is_stable(name, number, expected):
    status = RuntimeStatus(runtime())
    assert status.worker_name(name, number) == expected
    assert status.show_tool('fs_read_file') is False
    assert len(status.worker_name('x'*100, 2)) == 80


def test_snapshot_counts_all_terminal_and_active_states(monkeypatch):
    rt = runtime()
    rt.workers.states = {str(i): SimpleNamespace(id=str(i), name=f'Worker {i}', status=state,
        generation=0, progress='reading' if state == WorkerStatus.RUNNING else '', current_task='task')
        for i, state in enumerate(WorkerStatus)}
    status = RuntimeStatus(rt)
    snapshot = status.snapshot()
    assert snapshot['running'] == 2 and snapshot['completed'] == 1
    assert snapshot['failed'] == 1 and snapshot['stopped'] == 2 and snapshot['pending'] == 1
    assert len(snapshot['activities']) == len(WorkerStatus)
    monkeypatch.setattr('pygpt_net.core.agents_v2.status.translated_status', lambda key, **kwargs: key)
    assert status._swarm_text().startswith('Swarm: 2/3 running')
    assert 'reading' not in status._swarm_text()  # details belong to nested worker rows


def test_emit_swarm_throttles_and_respects_mode():
    rt = runtime()
    status = RuntimeStatus(rt)
    with patch('pygpt_net.core.agents_v2.status.time.monotonic', return_value=10):
        status.emit_swarm()
        status.emit_swarm()
        assert rt.emitter.status.call_count == 1
        assert rt.emitter.status.call_args.kwargs['hold_for'] == 0.2
        status.emit_swarm(force=True)
        assert rt.emitter.status.call_count == 2
        rt.is_swarm_mode = False
        status.emit_swarm(force=True)
        assert rt.emitter.status.call_count == 2


def test_reporter_is_singleton_and_stops_cleanly():
    async def scenario():
        rt = runtime()
        status = RuntimeStatus(rt)
        status.start_reporter()
        task = status.reporter_task
        status.start_reporter()
        assert status.reporter_task is task
        await asyncio.sleep(0)
        await status.stop_reporter()
        assert task.cancelled() and status.reporter_task is None
        rt.finished = True
        status.start_reporter()
        assert status.reporter_task is None
    asyncio.run(scenario())


def test_reporter_emits_for_pending_workers_and_logs_errors():
    async def scenario():
        rt = runtime()
        rt.SWARM_STATUS_INTERVAL = 0
        rt.workers.created_count = 2
        status = RuntimeStatus(rt)
        def finish(*args, **kwargs):
            rt.finished = True
        rt.emitter.status.side_effect = finish
        await status._reporter_loop()
        rt.emitter.status.assert_called_once()
        rt.finished = False
        rt.emitter.status.side_effect = RuntimeError('failed')
        await status._reporter_loop()
        rt.window.core.debug.log.assert_called_once()
    asyncio.run(scenario())


def test_status_emit_uses_translated_semantic_progress_for_worker():
    rt = runtime()
    rt.is_swarm_mode = False
    rt.is_orchestrator_mode = False
    rt.SHOW_AGENT_NAME_IN_STATUS = False
    worker = SimpleNamespace(id='w', name='Writer', progress='', status=WorkerStatus.RUNNING, generation=1)
    status = RuntimeStatus(rt)
    with patch('pygpt_net.core.agents_v2.status.translated_status', return_value='Reading'):
        status.emit('key', worker=worker)
    assert worker.progress == 'Reading'
    assert rt.emitter.status.call_args.args[0] == 'Reading'
