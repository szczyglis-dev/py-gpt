from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.core.agent_workflow.workflow import AgentWorkflow


def test_event_burst_does_not_copy_snapshots_and_retains_latest_result():
    controller = MagicMock()
    workflow = AgentWorkflow(SimpleNamespace(controller=SimpleNamespace(agent_workflow=controller)))
    workflow.snapshot = MagicMock(side_effect=AssertionError('eager snapshot'))
    workflow.ingest('RUNTIME INIT', {}, run_id='run')
    for i in range(100):
        workflow.ingest('TOOL CALL', {'name': 'search', 'id': str(i), 'arguments': {'q': i}})
        workflow.ingest('TOOL RESULT', {'name': 'search', 'id': str(i), 'output': str(i)})
    workflow.snapshot.assert_not_called()
    snapshot = AgentWorkflow.snapshot(workflow)
    assert snapshot['agents']['orchestrator']['events'][-1]['tool_output'] == '99'
    assert all(not call.args for call in controller.publish.call_args_list)


def test_monitor_bounds_large_previews_without_modifying_result():
    workflow = AgentWorkflow()
    value = {'text': 'x' * 1_000_000}
    workflow.ingest('TOOL CALL', {'name': 'search', 'id': 'call'})
    workflow.ingest('TOOL RESULT', {'name': 'search', 'id': 'call', 'output': value})
    output = workflow.snapshot()['agents']['orchestrator']['events'][-1]['tool_output']
    assert len(output) < workflow.MAX_TEXT_CHARS + 100
    assert output.endswith('[… preview truncated …]')
    assert len(value['text']) == 1_000_000


def test_global_timeline_limit_also_expires_call_indexes():
    workflow = AgentWorkflow()
    workflow.MAX_EVENTS_PER_AGENT = 4
    workflow.MAX_EVENTS_TOTAL = 6
    for actor in ('a', 'b', 'c'):
        for i in range(10):
            workflow._tool_call(actor, {'name': f'tool{i}', 'id': str(i)})
    events = [e for a in workflow.snapshot()['agents'].values() for e in a['events']]
    assert len(events) == 6
    retained = {e['id'] for e in events}
    assert set(workflow._tool_events.values()) <= retained
    assert set(workflow._tool_events_by_name.values()) <= retained
    workflow.clear()
    assert not workflow._tool_events
    assert not workflow.snapshot()['agents']
