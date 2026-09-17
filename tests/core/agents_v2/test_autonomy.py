"""Exercise continuation against real LlamaIndex agents and memory without an API key."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest


# LlamaIndex/workflows introspects Pydantic model instances with inspect.getmembers(),
# which reads compatibility attributes that Pydantic 2.x intentionally keeps but
# marks as deprecated. Keep this module's real-agent coverage while suppressing only
# those known third-party compatibility warnings.
pytestmark = [
    pytest.mark.filterwarnings(
        r"ignore:The `__fields__` attribute is deprecated, use the `model_fields` class property instead.*"
    ),
    pytest.mark.filterwarnings(
        r"ignore:The `__fields_set__` attribute is deprecated, use `model_fields_set` instead.*"
    ),
    pytest.mark.filterwarnings(
        r"ignore:Accessing the 'model_computed_fields' attribute on the instance is deprecated.*"
    ),
    pytest.mark.filterwarnings(
        r"ignore:Accessing the 'model_fields' attribute on the instance is deprecated.*"
    ),
]
from llama_index.core.agent.workflow import AgentInput, AgentOutput
from llama_index.core.llms import MockLLM, LLMMetadata, ChatMessage
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.workflow.events import StopEvent

from pygpt_net.core.agents_v2.autonomy import AutonomousFunctionAgent, AutonomousReActAgent
from pygpt_net.core.agents_v2.context import RuntimeContext


class InlineMemory(ChatMemoryBuffer):
    """Use the real memory algorithms without cross-thread sandbox wakeups."""
    async def aput(self, message):
        self.put(message)

    async def aput_messages(self, messages):
        self.put_messages(messages)

    async def aget(self, *args, **kwargs):
        return self.get(*args, **kwargs)


class Store:
    def __init__(self):
        self.values = {}

    async def get(self, key, default=None):
        return self.values.get(key, default)

    async def set(self, key, value):
        self.values[key] = value


class ToolLLM(MockLLM):
    @property
    def metadata(self):
        return LLMMetadata(is_function_calling_model=True)


@pytest.mark.parametrize("agent_cls", [AutonomousFunctionAgent, AutonomousReActAgent])
def test_checkpoint_continues_in_same_memory_and_budget(agent_cls):
    async def scenario():
        agent = agent_cls(llm=ToolLLM())
        ctx = SimpleNamespace(store=Store(), write_event_to_stream=MagicMock())
        memory = InlineMemory.from_defaults(token_limit=4096)
        await memory.aput(ChatMessage(role="user", content="Fix the defect"))
        await ctx.store.set("memory", memory)
        await ctx.store.set("max_iterations", 8)
        event = AgentOutput(response=ChatMessage(role="assistant", content="Inspected; implementing next"),
                            tool_calls=[], current_agent_name=agent.name)
        # FunctionAgent normally fills its scratchpad in take_step.
        if agent_cls is AutonomousFunctionAgent:
            await ctx.store.set(agent.scratchpad_key, [event.response])
        result = await agent.parse_agent_output(ctx, event)
        assert isinstance(result, AgentInput)
        assert await ctx.store.get("num_iterations") == 1
        assert "Runtime continuation" in result.input[-1].content
        assert result.input[0].content == "Fix the defect"
        agent._completion_requested = True
        final = await agent.parse_agent_output(ctx, event)
        assert isinstance(final, StopEvent)
        assert await ctx.store.get("num_iterations") == 2
    asyncio.run(scenario())


def test_iteration_limit_does_not_restart_or_reset_budget():
    async def scenario():
        agent = AutonomousFunctionAgent(llm=ToolLLM())
        ctx = SimpleNamespace(store=Store(), write_event_to_stream=MagicMock())
        await ctx.store.set("max_iterations", 2)
        await ctx.store.set("num_iterations", 1)
        event = AgentOutput(response=ChatMessage(role="assistant", content="More work"),
                            tool_calls=[], current_agent_name=agent.name)
        with pytest.raises(Exception, match="Max iterations"):
            await agent.parse_agent_output(ctx, event)
        assert agent._iteration_limit_reached
        assert await ctx.store.get("num_iterations") == 2
    asyncio.run(scenario())


def test_completion_tool_validates_evidence_and_records_blocker():
    async def scenario():
        runtime = SimpleNamespace(main_agent_name="Primary Agent", uses_workflow_finish=False,
                                  is_swarm_mode=False, model=None, verbose=MagicMock(), window=MagicMock())
        agent = RuntimeContext(runtime).build_agent("Primary Agent", "Main", ToolLLM(), "System", [])
        tool = next(t for t in agent.tools if t.metadata.name == "task_complete")
        await tool.acall(outcome="completed", evidence="")
        assert not agent._completion_requested
        await tool.acall(outcome="needs_input", evidence="Target repository is missing")
        assert agent._completion_requested
        assert agent._completion_outcome == "needs_input"
    asyncio.run(scenario())


def test_peer_messages_are_delivered_before_next_model_step(monkeypatch):
    async def scenario():
        agent = AutonomousFunctionAgent(llm=ToolLLM())
        agent._receive_messages = lambda: "Peer evidence: test fails on empty input"
        memory = SimpleNamespace(aput=AsyncMock())
        from llama_index.core.agent.workflow import FunctionAgent
        take = AsyncMock(return_value="response")
        monkeypatch.setattr(FunctionAgent, "take_step", take)
        result = await agent.take_step(None, [ChatMessage(role="user", content="Fix")], [], memory)
        assert result == "response"
        assert "empty input" in take.call_args.args[1][-1].content
        memory.aput.assert_awaited_once()
    asyncio.run(scenario())


def test_real_workflow_runs_checkpoint_tools_verification_and_final_answer():
    from pydantic import PrivateAttr
    from llama_index.core.tools import ToolSelection
    from llama_index.core.tools import FunctionTool
    from pygpt_net.core.agents_v2.autonomy import AgentCheckpoint

    async def scenario():
        actions = []

        class ScriptedAgent(AutonomousFunctionAgent):
            _passes: int = PrivateAttr(default=0)

            async def take_step(self, ctx, llm_input, tools, memory):
                self._passes += 1
                calls = []
                if self._passes == 1:
                    text = "Inspection complete; implementing next."
                elif self._passes == 2:
                    text = ""
                    calls = [ToolSelection(tool_id="fix", tool_name="fix_and_test", tool_kwargs={})]
                elif self._passes == 3:
                    text = ""
                    calls = [ToolSelection(tool_id="done", tool_name="task_complete", tool_kwargs={})]
                else:
                    text = "Fixed and verified."
                msg = ChatMessage(role="assistant", content=text)
                scratch = await ctx.store.get(self.scratchpad_key, default=[])
                await ctx.store.set(self.scratchpad_key, [*scratch, msg])
                return AgentOutput(response=msg, tool_calls=calls, current_agent_name=self.name)

        async def fix_and_test():
            actions.extend(["edit", "test"])
            return "Regression test passed"

        async def task_complete():
            assert actions == ["edit", "test"]
            agent._completion_requested = True
            return "Accepted"

        agent = ScriptedAgent(llm=ToolLLM(), tools=[
            FunctionTool.from_defaults(async_fn=fix_and_test),
            FunctionTool.from_defaults(async_fn=task_complete),
        ], timeout=10)
        handler = agent.run(user_msg="Fix the defect", memory=InlineMemory.from_defaults(token_limit=4096),
                            max_iterations=8)
        events = [event async for event in handler.stream_events()]
        result = await handler
        assert str(result) == "Fixed and verified."
        assert actions == ["edit", "test"]
        assert agent._passes == 4
        assert sum(isinstance(event, AgentCheckpoint) for event in events) == 1
        assert not agent._iteration_limit_reached
    asyncio.run(scenario())


def test_repeated_checkpoint_stops_even_with_unlimited_budget():
    async def scenario():
        agent = AutonomousFunctionAgent(llm=ToolLLM())
        ctx = SimpleNamespace(store=Store(), write_event_to_stream=MagicMock())
        await ctx.store.set("memory", InlineMemory.from_defaults(token_limit=4096))
        await ctx.store.set("max_iterations", 2**63 - 1)
        for index in range(3):
            event = AgentOutput(response=ChatMessage(role="assistant", content="I will work on it"),
                                tool_calls=[], current_agent_name=agent.name)
            await ctx.store.set(agent.scratchpad_key, [event.response])
            result = await agent.parse_agent_output(ctx, event)
            assert isinstance(result, StopEvent if index == 2 else AgentInput)
        assert agent._stalled
        assert not agent._completion_requested
    asyncio.run(scenario())


def test_approved_final_at_limit_does_not_generate_another_response():
    async def scenario():
        agent = AutonomousFunctionAgent(llm=ToolLLM())
        agent._completion_requested = True
        ctx = SimpleNamespace(store=Store())
        await ctx.store.set("memory", InlineMemory.from_defaults(token_limit=4096))
        await ctx.store.set("max_iterations", 2)
        await ctx.store.set("num_iterations", 1)
        event = AgentOutput(response=ChatMessage(role="assistant", content="Verified result"),
                            tool_calls=[], current_agent_name=agent.name)
        result = await agent.parse_agent_output(ctx, event)
        assert isinstance(result, StopEvent)
        assert not agent._iteration_limit_reached
        assert await ctx.store.get("max_iterations") == 2
        assert await ctx.store.get("num_iterations") == 2
    asyncio.run(scenario())
