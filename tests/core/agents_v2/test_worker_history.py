"""Durable specialist context is saved once per generation on its launching part."""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from pygpt_net.core.agents_v2.worker_history import WorkerHistory
from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.ctx_part import CtxItemPart


def make_history():
    main = CtxItem('agent_v2')
    part = CtxItemPart()
    main.parts.append(part)
    runtime = SimpleNamespace(context=SimpleNamespace(ctx=main), window=MagicMock(),
                              workers=SimpleNamespace(parent_parts={'w': part}, stored_context_runs=set()))
    state = SimpleNamespace(id='w', generation=1, name='Writer', current_task='Write', last_result='Done')
    return runtime, state, part, WorkerHistory(runtime)


def test_save_is_idempotent_per_generation_and_persists_to_parent():
    runtime, state, part, history = make_history()
    with patch('pygpt_net.core.agents_v2.worker_history.time.time', return_value=12):
        history.save(state)
        history.save(state)
    assert part.extra['worker_context'] == [dict(id='w', name='Writer', input='Write', output='Done', created_at=12000)]
    runtime.window.core.ctx.update_part.assert_called_once_with(runtime.context.ctx, part, sync_item=False)
    state.generation = 2
    history.save(state)
    assert len(part.extra['worker_context']) == 2
    assert runtime.workers.stored_context_runs == {('w', 1), ('w', 2)}


@pytest.mark.parametrize('missing', ['part', 'main', 'membership'])
def test_missing_parent_does_not_mark_run_as_saved(missing):
    runtime, state, part, history = make_history()
    if missing == 'part':
        runtime.workers.parent_parts.clear()
    elif missing == 'main':
        runtime.context.ctx = None
    else:
        runtime.context.ctx.parts.clear()
    history.save(state)
    runtime.window.core.ctx.update_part.assert_not_called()
    assert runtime.workers.stored_context_runs == set()


def test_legacy_context_migration_sorts_records_and_removes_old_key():
    runtime, state, part, history = make_history()
    part.extra = {'worker_outputs': [{'legacy': True}, {'bad': True}]}
    with patch('pygpt_net.core.agents_v2.worker_history.legacy_worker_context_record',
               side_effect=[dict(id='old', created_at=1), None]) as migrate:
        history.save(state)
    assert migrate.call_count == 2
    assert 'worker_outputs' not in part.extra
    assert part.extra['worker_context'][0] == dict(id='old', created_at=1)
    assert part.extra['worker_context'][1]['id'] == 'w'


def test_non_dictionary_extra_is_repaired():
    runtime, state, part, history = make_history()
    part.extra = None
    history.save(state)
    assert part.extra['worker_context'][0]['output'] == 'Done'
