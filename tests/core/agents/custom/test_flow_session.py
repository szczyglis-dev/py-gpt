import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import pygpt_net.core.agents.custom.flow as flow_module
import pygpt_net.core.agents.custom.flow_preparation as preparation_module
import pygpt_net.core.agents.custom.flow_execution as execution_module
from pygpt_net.core.agents.custom.runner import FlowOrchestrator


@pytest.mark.parametrize("partial", [False, True])
def test_flow_passes_displayed_router_answer_to_next_node_memory_and_finishes_context(monkeypatch, partial):
    contexts = []
    requests = []
    bridge = MagicMock()
    bridge.stopped.return_value = False
    bridge.on_next_ctx.side_effect = lambda **kwargs: contexts.append(kwargs) or MagicMock()
    handler = MagicMock()
    monkeypatch.setattr(flow_module, "StreamHandler", lambda *args: handler)
    monkeypatch.setattr(preparation_module, "resolve_node_runtime", lambda **kwargs: SimpleNamespace(
        model="model", allow_local_tools=False, allow_remote_tools=False, instructions="instructions", role=""))

    class Factory:
        def __init__(self, *args):
            pass

        def build(self, node, **kwargs):
            return SimpleNamespace(instance=SimpleNamespace(name=node.name), multi_output=len(node.outputs) > 1,
                                   allowed_routes=node.outputs)

    async def run(agent, **kwargs):
        requests.append((agent.name, kwargs["input"]))
        answer = '{"route":"writer","content":"handoff"}' if agent.name == "Router" else "final answer"
        return SimpleNamespace(final_output=answer, last_response_id=agent.name)

    monkeypatch.setattr(preparation_module, "AgentFactory", Factory)
    monkeypatch.setattr(execution_module, "Runner", SimpleNamespace(run=run))
    schema = [
        {"id": "start", "type": "start", "slots": {"output": {"out": ["router"]}}},
        {"id": "router", "type": "agent", "slots": {"name": "Router", "output": {"out": ["writer", "end"]}}},
        {"id": "writer", "type": "agent", "slots": {"name": "Writer", "output": {"out": ["end"]},
                                                          "memory": {"out": ["memory"]}}},
        {"id": "memory", "type": "memory", "slots": {}},
        {"id": "end", "type": "end", "slots": {}},
    ]
    messages = [{"role": "user", "content": "old question"}, {"role": "assistant", "content": "old answer"},
                {"role": "user", "content": "current question"}]
    ctx = MagicMock()
    result = asyncio.run(FlowOrchestrator(None).run_flow(
        schema, messages, ctx, bridge, {}, None, None, False, partial,
        None, None, False, False, [], None,
    ))
    assert requests == [("Router", messages), ("Writer", [{"role": "user", "content": "handoff"}])]
    assert result.final_output == "final answer"
    assert result.last_response_id == "Writer"
    if partial:
        assert [value["output"] for value in contexts] == ["handoff", "final answer"]
        assert [value["finish"] for value in contexts] == [False, True]
        assert handler.new.call_count == 2
    else:
        assert result.ctx is ctx
        assert bridge.on_next.call_count == 2
        assert [call.args[0] for call in handler.to_buffer.call_args_list] == ["handoff", "final answer"]
    bridge.on_stop.assert_not_called()
