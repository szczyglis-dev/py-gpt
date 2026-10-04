"""Swarm sizing and status are explicit workflow contracts, not worker side effects."""
import asyncio
import json
from unittest.mock import MagicMock

from pygpt_net.core.agents_v2.workflow import WorkflowControl


def test_swarm_declaration_validation_and_aggregate_status():
    runtime = MagicMock()
    runtime.is_swarm_mode = False
    runtime.workers.expected_count = None
    runtime.workers.created_count = 0
    runtime.workers.launched_count = 0
    workflow = WorkflowControl(runtime)
    assert 'error' in json.loads(asyncio.run(workflow.declare_swarm(3)))
    assert 'error' in json.loads(asyncio.run(workflow.status()))
    runtime.is_swarm_mode = True
    for count in ('invalid', 0, -1):
        assert 'error' in json.loads(asyncio.run(workflow.declare_swarm(count)))
    result = json.loads(asyncio.run(workflow.declare_swarm(3)))
    assert result['declared'] == 3 and runtime.workers.expected_count == 3
    runtime.status.start_reporter.assert_called_once()
    assert 'error' in json.loads(asyncio.run(workflow.declare_swarm(4)))
    runtime.workers.created_count = 1
    assert 'error' in json.loads(asyncio.run(workflow.declare_swarm(3)))
    runtime.status.snapshot.return_value = {'running': 1}
    assert json.loads(asyncio.run(workflow.status())) == {'running': 1}
