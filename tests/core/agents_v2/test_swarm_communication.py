import asyncio
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.core.agents_v2.workers import WorkerRuntime


def make_bus():
    runtime = SimpleNamespace(is_swarm_mode=True, is_stopped=lambda: False, finished=False,
                              workers={"w1": SimpleNamespace(), "w2": SimpleNamespace()}, verbose=MagicMock())
    return WorkerRuntime(runtime)


def test_peer_delivery_broadcast_identity_and_consume_once():
    async def scenario():
        bus = make_bus()
        sender_tool = bus.communication_tools("w1")[0]
        response = await sender_tool.acall(recipient="all", message="Regression reproduced")
        assert json.loads(response.content)["delivered_to"] == ["orchestrator", "w2"]
        assert not bus.receive_messages("w1")
        for target in ("w2", "orchestrator"):
            value = bus.receive_messages(target)
            assert '"sender": "w1"' in value
            assert "Regression reproduced" in value
            assert "untrusted" in value
            assert not bus.receive_messages(target)
    asyncio.run(scenario())


def test_waiting_peer_wakes_on_message():
    async def scenario():
        bus = make_bus()
        receive = bus.communication_tools("w2")[1]
        pending = asyncio.create_task(receive.acall(wait_seconds=1))
        await asyncio.sleep(0)
        await bus.send_message("w1", "w2", "Ready for review")
        result = await asyncio.wait_for(pending, 2)
        assert "Ready for review" in result.content
    asyncio.run(scenario())


def test_mailbox_limits_and_stop_reject_without_partial_broadcast():
    async def scenario():
        bus = make_bus()
        for _ in range(64):
            await bus.send_message("w1", "w2", "Evidence")
        assert "error" in json.loads(await bus.send_message("w1", "all", "Overflow"))
        assert not bus.receive_messages("orchestrator")
        assert "error" in json.loads(await bus.send_message("w1", "missing", "Evidence"))
        assert "error" in json.loads(await bus.send_message("w1", "w1", "Evidence"))
        assert "error" in json.loads(await bus.send_message("spoof", "w1", "Evidence"))
        bus.runtime.is_stopped = lambda: True
        assert "error" in json.loads(await bus.send_message("w1", "orchestrator", "Evidence"))
    asyncio.run(scenario())
