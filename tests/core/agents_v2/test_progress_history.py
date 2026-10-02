"""Durable progress belongs to actor launch partials, independent of UI memory."""
from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.core.agents_v2.status import RuntimeStatus
from pygpt_net.core.render.web.parts.agents import Agents


def test_progress_history_groups_tasks_by_actor_after_renderer_reset():
    from pygpt_net.item.ctx_part_task import CtxItemPartTask
    tasks = [CtxItemPartTask(uuid='t1', extra={'tool_name': 'read_file'},
                             agent_id='orchestrator', tool_call_id='c1'),
             CtxItemPartTask(uuid='t2', extra={'tool_name': 'search', 'agent_name': 'Worker'},
                             agent_id='w1', tool_call_id='c2')]
    part = SimpleNamespace(uuid='p1', extra={}, tasks=tasks)
    main = SimpleNamespace(parts=[part])
    main.get_part_tool_calls = lambda **kwargs: [{'call_id':'c1', 'name':'read_file'}, {'call_id':'c2', 'name':'search'}]
    runtime = SimpleNamespace(emitter=MagicMock(), timeline=SimpleNamespace(part=lambda *args, **kwargs: part),
                              context=SimpleNamespace(ctx=main), window=MagicMock(), is_swarm_mode=False,
                              workers=SimpleNamespace(states={}))
    status = RuntimeStatus(runtime)
    status.owner('Reading files', 'orchestrator')
    status.owner('Searching', 'w1')
    runtime.window.core.ctx.update_part.assert_called_with(main, part, sync_item=False)
    renderer = SimpleNamespace(state=SimpleNamespace(), window=MagicMock(),
                               helpers=SimpleNamespace(extract_extra_tool_calls=lambda calls: calls))
    renderer.window.core.command.is_tool_hidden.return_value = False
    records = Agents(renderer).progress_records(main)
    assert records[0]['id'] == 'progress-p1'
    assert records[0]['text'] == '[w1] Searching'
    assert [call['call_id'] for call in records[0]['hierarchy']['calls']] == ['c1', 'c2']
    assert records[0]['hierarchy']['workers'] == []
    status.owner('Completed.', 'w1')
    completed = Agents(renderer).progress_records(main)[0]
    assert completed['id'] == records[0]['id']
    assert completed['text'] == '[w1] Completed.'
    assert completed['hierarchy'] == records[0]['hierarchy']
    # Swarm alone keeps worker status rows and independently expandable tools.
    part.extra['agents_v2_progress']['swarm'] = True
    part.extra['agents_v2_progress']['workers'] = {'w1': {'id': 'w1', 'text': 'Searching'}}
    replay = Agents(renderer).progress_records(main)[0]['hierarchy']
    assert [call['call_id'] for call in replay['calls']] == ['c1']
    assert replay['workers'][0]['text'] == 'Searching'
    assert [call['call_id'] for call in replay['workers'][0]['calls']] == ['c2']


def test_held_status_delivers_owner_without_undefined_variables():
    import time
    from pygpt_net.core.agents_v2.emitter import RuntimeEmitter
    signals = SimpleNamespace(response=MagicMock())
    emitter = RuntimeEmitter(context=None, extra={}, signals=signals)
    emitter.status_owner_provider = lambda text, actor: {"part_uuid": "p1", "progress": {"text": text}}
    emitter.status("Working", hold_for=60)
    emitter.status("Checking")
    emitter._status_hold_until = time.monotonic() - 1
    emitter._flush_held_status()
    assert emitter.status_text == "Checking"
    assert emitter._status_owner["part_uuid"] == "p1"


def test_live_status_sends_hierarchy_with_real_worker_task():
    from pygpt_net.item.ctx import CtxItem
    from pygpt_net.item.ctx_part import CtxItemPart
    from pygpt_net.item.ctx_part_task import CtxItemPartTask
    ctx = CtxItem()
    ctx.id = 42
    ctx.mode = 'agent_v2'
    part = CtxItemPart()
    part.uuid = 'p1'
    part.extra = {'agents_v2_progress': {'text': 'Thinking...'}}
    part.tasks = [CtxItemPartTask(agent_id='w1', tool_call_id='c1',
                                extra={'tool_name': 'read_file', 'agent_name': 'Worker'}, tool_input={'path': 'a.txt'})]
    ctx.parts = [part]
    renderer = SimpleNamespace(state=SimpleNamespace(), window=MagicMock(), get_output_node=MagicMock(),
                               helpers=SimpleNamespace(extract_extra_tool_calls=lambda calls: calls))
    renderer.window.core.command.is_tool_hidden.return_value = False
    agents = Agents(renderer)
    agents.workflow_status_key = lambda *args: (None, None, ctx)
    agents.update_agent_working = MagicMock()
    agents.workflow_status_add = MagicMock(return_value='transient-status')
    agents.agent_status(None, ctx, 'Working', owner={'part_uuid': 'p1', 'progress': {'text': 'Odczytuję plik wierszyk.txt'}})
    script = renderer.get_output_node.return_value.page.return_value.runJavaScript.call_args.args[0]
    assert 'progress-p1' in script
    assert 'Odczytuję plik wierszyk.txt' in script
    assert 'Thinking...' not in script
    assert 'hierarchy' in script
    assert 'read_file' in script
    assert '"workers": []' in script


def test_embedded_javascript_matches_current_bundle():
    from pathlib import Path
    from PySide6.QtCore import QFile, QIODevice
    import pygpt_net.js_rc  # Registers the same resource the application loads.
    resource = QFile(':/js/app.min.js')
    assert resource.open(QIODevice.ReadOnly)
    bundle = Path(__file__).resolve().parents[3] / 'src/pygpt_net/data/js/app.min.js'
    assert bytes(resource.readAll()) == bundle.read_bytes()


def test_worker_tool_refresh_preserves_named_prefix_without_duplication():
    from pygpt_net.core.agents_v2.emitter import RuntimeEmitter
    part = SimpleNamespace(uuid='p1', extra={}, tasks=[])
    worker = SimpleNamespace(name='Translator', progress='Reading file', current_task='Translate',
                             status=SimpleNamespace(value='running'))
    emitter = RuntimeEmitter(context=None, extra={}, signals=None)
    runtime = SimpleNamespace(emitter=emitter, timeline=SimpleNamespace(part=lambda *args, **kwargs: part),
                              context=SimpleNamespace(ctx=SimpleNamespace(parts=[part])), window=MagicMock(),
                              is_swarm_mode=False, workers=SimpleNamespace(states={'w1': worker}))
    status = RuntimeStatus(runtime)
    emitter.status('[Translator] Reading file', source='w1')
    assert part.extra['agents_v2_progress']['text'] == '[Translator] Reading file'
    # Tool snapshots use raw worker.progress, unlike explicit worker status events.
    status.refresh_tools('w1')
    assert part.extra['agents_v2_progress']['text'] == '[Translator] Reading file'
    worker.progress = 'Completed.'
    status.refresh_tools('w1')
    assert part.extra['agents_v2_progress']['text'] == '[Translator] Completed.'
    emitter.status('Checking results', source='orchestrator')
    assert part.extra['agents_v2_progress']['text'] == 'Checking results'


def test_primary_tool_refresh_keeps_status_across_partial_and_spinner(monkeypatch):
    from pygpt_net.core.agents_v2.emitter import RuntimeEmitter
    from pygpt_net.item.ctx_part_task import CtxItemPartTask
    monkeypatch.setattr('pygpt_net.core.agents_v2.status.translated_status',
                        lambda key, **kwargs: 'Using tool: ' + kwargs['tool'] if 'tool' in kwargs else 'Thinking...')
    part = SimpleNamespace(uuid='p1', extra={}, tasks=[CtxItemPartTask(extra={'tool_name': 'read_file'})])
    emitter = RuntimeEmitter(context=None, extra={}, signals=None)
    runtime = SimpleNamespace(emitter=emitter, timeline=SimpleNamespace(part=lambda *args, **kwargs: part),
                              context=SimpleNamespace(ctx=SimpleNamespace(parts=[part])), window=MagicMock(),
                              is_swarm_mode=False, workers=SimpleNamespace(states={}))
    status = RuntimeStatus(runtime)
    status.refresh_tools('orchestrator')
    assert part.extra['agents_v2_progress']['text'] == 'Thinking...'
    emitter.status('Checking the translation', source='orchestrator')
    emitter.clear_status()
    part.extra = {}  # The next primary partial has no progress yet.
    status.refresh_tools('orchestrator')
    assert part.extra['agents_v2_progress']['text'] == 'Checking the translation'


def test_direct_plugin_progress_is_saved_in_expandable_primary_status():
    from pygpt_net.item.ctx import CtxItem
    from pygpt_net.item.ctx_part import CtxItemPart
    ctx = CtxItem()
    ctx.id = 42
    ctx.mode = 'agent_v2'
    part = CtxItemPart()
    part.uuid = 'p1'
    part.extra = {'agents_v2_progress': {'text': 'Tools'}}
    ctx.parts = [part]
    renderer = SimpleNamespace(state=SimpleNamespace(), window=MagicMock(), get_output_node=MagicMock(),
                               helpers=SimpleNamespace(extract_extra_tool_calls=lambda calls: calls))
    agents = Agents(renderer)
    agents.workflow_status_key = lambda *args: (None, None, ctx)
    agents.update_agent_working = MagicMock()
    agents.workflow_status_add = MagicMock(return_value='transient')
    agents.agent_status(None, ctx, 'Odczytuję plik wierszyk.txt')
    assert part.extra['agents_v2_progress']['text'] == 'Odczytuję plik wierszyk.txt'
    script = renderer.get_output_node.return_value.page.return_value.runJavaScript.call_args.args[0]
    assert 'progress-p1' in script
    assert 'Odczytuję plik wierszyk.txt' in script
    assert 'hierarchy' in script
    assert agents.progress_records(ctx)[0]['text'] == 'Odczytuję plik wierszyk.txt'


def test_semantic_primary_status_wins_over_stale_partial_label():
    import asyncio
    from pygpt_net.core.agents_v2.emitter import RuntimeEmitter
    part = SimpleNamespace(uuid='p1', extra={}, tasks=[])
    emitter = RuntimeEmitter(context=None, extra={}, signals=None)
    runtime = SimpleNamespace(emitter=emitter, timeline=SimpleNamespace(part=lambda *args, **kwargs: part),
                              context=SimpleNamespace(ctx=SimpleNamespace(parts=[part])), window=MagicMock(),
                              verbose=MagicMock(), is_swarm_mode=False, workers=SimpleNamespace(states={}))
    status = RuntimeStatus(runtime)
    asyncio.run(status.update('Odczytuję plik wierszyk.txt'))
    emitter.clear_status()
    part.extra = {'agents_v2_progress': {'text': 'Thinking...'}}
    status.refresh_tools('orchestrator')
    assert part.extra['agents_v2_progress']['text'] == 'Odczytuję plik wierszyk.txt'


def test_disabled_tool_history_keeps_status_without_extracting_or_emitting_calls(monkeypatch):
    from pygpt_net.core.types import agent as agent_policy
    from pygpt_net.core.render.web.parts.tools import Tools
    from pygpt_net.item.ctx import CtxItem
    monkeypatch.setattr(agent_policy, 'AGENTS_V2_TOOL_CALLS_ENABLED', False)
    part = SimpleNamespace(uuid='p1', extra={'agents_v2_progress': {'text': 'Odczytuję plik'}}, tasks=[object()])
    ctx = CtxItem()
    ctx.mode = 'agent_v2'
    ctx.parts = [part]
    extract = MagicMock(side_effect=AssertionError('must not extract stored tool calls'))
    monkeypatch.setattr(CtxItem, 'get_part_tool_calls', extract)
    renderer = SimpleNamespace(state=SimpleNamespace(), window=MagicMock())
    assert Agents(renderer).progress_records(ctx)[0]['hierarchy'] is None
    assert Agents(renderer).progress_records(ctx)[0]['text'] == 'Odczytuję plik'
    assert Tools(renderer).show_tool_chain_for_ctx(ctx) is False
    runtime = SimpleNamespace(emitter=MagicMock(), window=renderer.window)
    RuntimeStatus(runtime).refresh_tools('orchestrator')
    runtime.emitter.status.assert_not_called()
    extract.assert_not_called()
def test_show_tools_preference_defaults_off_and_respects_master_switch(monkeypatch):
    from pygpt_net.core.types import agent as agent_policy
    monkeypatch.setattr(agent_policy, 'AGENTS_V2_TOOL_CALLS_ENABLED', True)
    assert not agent_policy.tool_calls_enabled({})
    assert not agent_policy.tool_calls_enabled({'agent.v2.show_tools': False})
    assert agent_policy.tool_calls_enabled({'agent.v2.show_tools': True})
    monkeypatch.setattr(agent_policy, 'AGENTS_V2_TOOL_CALLS_ENABLED', False)
    assert not agent_policy.tool_calls_enabled({'agent.v2.show_tools': True})
