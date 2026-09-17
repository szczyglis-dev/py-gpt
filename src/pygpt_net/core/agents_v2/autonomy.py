"""Continuation inside one workflow: prose checkpoints do not end an assignment."""
from typing import Callable, Optional, Union

from pydantic import BaseModel, PrivateAttr
from llama_index.core.agent.workflow import AgentInput, AgentOutput, FunctionAgent, ReActAgent, ToolCall
from llama_index.core.base.llms.types import ChatMessage
from llama_index.core.workflow import Context, step
from llama_index.core.workflow.events import Event, StopEvent


class AgentCheckpoint(Event):
    """The next model response belongs to a new intermediate work segment."""


class AutonomousAgentMixin(BaseModel):
    _last_checkpoint: str = PrivateAttr(default="")
    _repeated_checkpoints: int = PrivateAttr(default=0)
    _stalled: bool = PrivateAttr(default=False)
    _completion_outcome: str = PrivateAttr(default="")
    _completion_requested: bool = PrivateAttr(default=False)
    _completion_check: Optional[Callable[[], bool]] = PrivateAttr(default=None)
    _receive_messages: Optional[Callable[[], str]] = PrivateAttr(default=None)
    _completion_tool: str = PrivateAttr(default="task_complete")
    _iteration_limit_reached: bool = PrivateAttr(default=False)

    def run(self, *args, **kwargs):
        self._last_checkpoint = ""
        self._repeated_checkpoints = 0
        self._stalled = False
        self._completion_outcome = ""
        self._completion_requested = False
        self._iteration_limit_reached = False
        return super().run(*args, **kwargs)

    async def take_step(self, ctx, llm_input, tools, memory):
        if self._receive_messages is not None:
            messages = self._receive_messages()
            if messages:
                message = ChatMessage(role="user", content=messages)
                await memory.aput(message)
                llm_input = [*llm_input, message]
        return await super().take_step(ctx, llm_input, tools, memory)

    @step
    async def parse_agent_output(
        self, ctx: Context, ev: AgentOutput
    ) -> Union[StopEvent, AgentInput, ToolCall, None]:
        iterations = await ctx.store.get("num_iterations", default=0)
        limit = await ctx.store.get("max_iterations", default=20)
        self._iteration_limit_reached = iterations + 1 >= limit
        complete = self._completion_requested
        if self._completion_check is not None:
            complete = self._completion_check()
        if complete and not ev.tool_calls and not ev.retry_messages and self._iteration_limit_reached:
            # The already generated, approved final response needs no further
            # model work. Let upstream persist it instead of generating a second
            # early-stopping response. Restore the work budget immediately.
            self._iteration_limit_reached = False
            await ctx.store.set("max_iterations", iterations + 2)
            try:
                return await super().parse_agent_output(ctx, ev)
            finally:
                await ctx.store.set("max_iterations", limit)
        if ev.tool_calls:
            self._last_checkpoint = ""
            self._repeated_checkpoints = 0
        elif not ev.retry_messages and not complete:
            text = str(ev.response.content or "").strip()
            self._repeated_checkpoints = self._repeated_checkpoints + 1 if text == self._last_checkpoint else 1
            self._last_checkpoint = text
            # Also protect explicitly unlimited runs from providers that ignore
            # the completion contract and repeat an unchanged answer forever.
            self._stalled = self._repeated_checkpoints >= 3
        if (
            not ev.tool_calls and not ev.retry_messages and not complete
            and not self._iteration_limit_reached and not self._stalled
        ):
            # Flush the provider scratchpad before continuing so both ReAct and
            # function calling retain preceding tools/prose without replaying them.
            ctx.write_event_to_stream(AgentCheckpoint())
            memory = await ctx.store.get("memory")
            await self.finalize(ctx, ev, memory)
            await ctx.store.set("num_iterations", iterations + 1)
            await memory.aput(ChatMessage(role="user", content=(
                "Runtime continuation: the preceding response is a checkpoint, not completion. "
                "Continue the assigned work, inspect results, fix problems and verify the outcome. "
                f"When done call {self._completion_tool}. If genuinely blocked or needing user input, "
                "report that explicitly through the completion tool; do not invent success or repeat unchanged work."
            )))
            return AgentInput(input=await memory.aget(), current_agent_name=self.name)
        return await super().parse_agent_output(ctx, ev)


class AutonomousFunctionAgent(AutonomousAgentMixin, FunctionAgent):
    pass


class AutonomousReActAgent(AutonomousAgentMixin, ReActAgent):
    pass
