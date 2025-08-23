#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.24 02:00:00                  #
# ================================================== #

from typing import List, Optional, Callable
import inspect
from pydantic import BaseModel, Field, ValidationError

from llama_index.core.workflow import (
    Workflow,
    Context,
    StartEvent,
    StopEvent,
    Event,
    step,
)
from llama_index.core.llms.llm import LLM
from llama_index.core.prompts import PromptTemplate
from llama_index.core.tools.types import BaseTool

from llama_index.core.agent.workflow import (
    FunctionAgent,
    ToolCall,
    ToolCallResult,
    AgentStream,
    AgentOutput,
)

from .events import StepEvent

try:
    from llama_index.core.memory import ChatMemoryBuffer
except Exception:
    try:
        from llama_index.memory import ChatMemoryBuffer  # old import
    except Exception:
        ChatMemoryBuffer = None

class SubTask(BaseModel):
    name: str = Field(..., description="The name of the sub-task.")
    input: str = Field(..., description="The input prompt for the sub-task.")
    expected_output: str = Field(..., description="The expected output of the sub-task.")
    dependencies: List[str] = Field(
        ..., description="Names of sub-tasks that must be completed before this sub-task."
    )


class Plan(BaseModel):
    sub_tasks: List[SubTask] = Field(..., description="The sub-tasks in the plan.")


DEFAULT_INITIAL_PLAN_PROMPT = """\
You have the following prior context/memory (may be empty):
{memory_context}

Think step-by-step. Given a task and a set of tools, create a comprehensive, end-to-end plan to accomplish the task.
Keep in mind not every task needs to be decomposed into multiple sub-tasks if it is simple enough.
The plan should end with a sub-task that can achieve the overall task.

The tools available are:
{tools_str}

Overall Task: {task}
"""

DEFAULT_PLAN_REFINE_PROMPT = """\
You have the following prior context/memory (may be empty):
{memory_context}

Think step-by-step. Given an overall task, a set of tools, and completed sub-tasks, update (if needed) the remaining sub-tasks so that the overall task can still be completed.
The plan should end with a sub-task that can achieve and satisfy the overall task.
If you do update the plan, only create new sub-tasks that will replace the remaining sub-tasks, do NOT repeat tasks that are already completed.
If the remaining sub-tasks are enough to achieve the overall task, it is ok to skip this step, and instead explain why the plan is complete.

The tools available are:
{tools_str}

Completed Sub-Tasks + Outputs:
{completed_outputs}

Remaining Sub-Tasks:
{remaining_sub_tasks}

Overall Task: {task}
"""

DEFAULT_EXECUTE_PROMPT = """\
You execute the given sub-task using the tools. Return concise outputs.
"""

class QueryEvent(StartEvent):
    query: str


class PlanReady(Event):
    plan: Plan
    query: str


class FinalEvent(StopEvent):
    pass


class PlannerWorkflow(Workflow):
    def __init__(
        self,
        tools: List[BaseTool],
        llm: LLM,
        system_prompt: Optional[str] = None,
        initial_plan_prompt: str = DEFAULT_INITIAL_PLAN_PROMPT,
        plan_refine_prompt: str = DEFAULT_PLAN_REFINE_PROMPT,
        verbose: bool = False,
        max_steps: int = 12,
        memory_char_limit: int = 8000,
        clear_executor_memory_between_subtasks: bool = False,
        executor_memory_factory: Optional[Callable[[], object]] = None,
        on_stop: Optional[Callable] = None,
    ):
        super().__init__(timeout=None, verbose=verbose)
        self._planner_llm = llm
        self._initial_plan_prompt = PromptTemplate(initial_plan_prompt)
        self._plan_refine_prompt = PromptTemplate(plan_refine_prompt)
        self._tools = tools
        self._max_steps = max_steps
        self._memory = None
        self.verbose = verbose
        self._memory_char_limit = memory_char_limit
        self._on_stop = on_stop

        self._executor = FunctionAgent(
            name="PlannerExecutor",
            description="Executes planner sub-tasks using available tools.",
            tools=tools,
            llm=llm,
            system_prompt=system_prompt or DEFAULT_EXECUTE_PROMPT,
            max_steps=max_steps,
        )

        if executor_memory_factory is not None:
            self._executor_mem_factory = executor_memory_factory
        else:
            def _default_factory():
                if ChatMemoryBuffer is not None:
                    return ChatMemoryBuffer.from_defaults()
                return None
            self._executor_mem_factory = _default_factory

        self._clear_exec_mem_between_subtasks = clear_executor_memory_between_subtasks

    def _stopped(self) -> bool:
        """
        Check if the workflow has been stopped.

        :return: True if the workflow is stopped, False otherwise.
        """
        if self._on_stop:
            try:
                return self._on_stop()
            except Exception:
                return False
        return False

    def _emit_step_event(
            self,
            ctx: Context,
            name: str,
            index: Optional[int] = None,
            total: Optional[int] = None,
            meta: Optional[dict] = None,
    ) -> None:
        """
        Emits a step event to the context stream.

        :param ctx: The context to write the event to.
        :param name: The name of the step (e.g., "make_plan", "execute_plan", "subtask").
        :param index: The index of the step (optional).
        :param total: The total number of steps (optional).
        :param meta: Additional metadata for the step (optional).
        """
        try:
            ctx.write_event_to_stream(
                StepEvent(name=name, index=index, total=total, meta=meta or {})
            )
        except Exception:
            # fallback for older versions of AgentStream
            try:
                ctx.write_event_to_stream(
                    AgentStream(
                        delta="",
                        response="",
                        current_agent_name="PlannerWorkflow",
                        tool_calls=[],
                        raw={"StepEvent": {"name": name, "index": index, "total": total, "meta": meta or {}}}
                    )
                )
            except Exception:
                pass

    def _reset_executor_memory(self):
        """Reset the memory of the executor agent to a new instance or clear it."""
        try:
            new_mem = self._executor_mem_factory()
            if hasattr(self._executor, "memory"):
                self._executor.memory = new_mem
        except Exception:
            mem = getattr(self._executor, "memory", None)
            for attr in ("reset", "clear", "flush"):
                fn = getattr(mem, attr, None)
                if callable(fn):
                    try:
                        fn()
                        break
                    except Exception:
                        pass

    def run(
        self,
        query: str,
        ctx: Optional[Context] = None,
        memory=None,
        verbose: bool = False,
        **kwargs
    ):
        """
        Run the planner workflow with the given query and context.

        :param query: The input query string to process.
        :param ctx: The context in which the workflow is executed (optional).
        :param memory: custom memory buffer to use for the agent (optional).
        :param verbose: Whether to enable verbose output (default: False).
        :param kwargs: Additional keyword arguments (not used).
        :return: The result of the workflow execution.
        """
        if verbose:
            self.verbose = True

        self._memory = memory
        self._reset_executor_memory()

        return super().run(ctx=ctx, query=query)

    def _memory_to_text(self, memory) -> str:
        """
        Convert the memory object to a text representation.

        :param memory: The memory object to convert, which can be a string, list, or other types.
        :return: A string representation of the memory content, truncated if it exceeds the character limit.
        """
        if not memory:
            return ""
        try:
            if isinstance(memory, str):
                text = memory
            elif isinstance(memory, list):
                parts = []
                for m in memory:
                    if isinstance(m, str):
                        parts.append(m)
                    elif isinstance(m, dict) and ("content" in m or "text" in m):
                        role = m.get("role", "user")
                        content = m.get("content", m.get("text", ""))
                        parts.append(f"{role}: {content}")
                    else:
                        # ChatMessage-like object
                        role = getattr(m, "role", None) or getattr(m, "sender", "user")
                        content = getattr(m, "content", None) or getattr(m, "text", "")
                        parts.append(f"{role}: {content}")
                text = "\n".join(parts)
            else:
                for attr in ("to_string", "to_str"):
                    fn = getattr(memory, attr, None)
                    if callable(fn):
                        text = fn()
                        break
                else:
                    for attr in ("get", "messages", "get_all", "dump"):
                        fn = getattr(memory, attr, None)
                        if callable(fn):
                            data = fn()
                            text = self._memory_to_text(data)
                            break
                    else:
                        text = str(memory)
        except Exception:
            text = str(memory)

        if self._memory_char_limit and len(text) > self._memory_char_limit:
            text = "...[truncated]...\n" + text[-self._memory_char_limit:]
        return text

    async def _emit_text(
            self,
            ctx: Context,
            text: str,
            agent_name: str = "PlannerWorkflow"
    ):
        """
        Emit a text message to the context stream.

        :param ctx: The context to write the event to
        :param text: The text message to emit.
        :param agent_name: The name of the agent emitting the text (default: "PlannerWorkflow").
        """
        try:
            ctx.write_event_to_stream(AgentStream(delta=text))
        except ValidationError:
            ctx.write_event_to_stream(
                AgentStream(
                    delta=text,
                    response=text,
                    current_agent_name=agent_name,
                    tool_calls=[],
                    raw={},
                )
            )

    def _to_text(self, resp) -> str:
        """
        Convert the response object to a text representation.

        :param resp: The response object to convert, which can be a string, list, or other types.
        :return: A string representation of the response content.
        """
        try:
            if resp is None or str(resp) == "assistant: None":
                return ""
            msg = getattr(resp, "message", None)
            if msg is not None:
                return getattr(msg, "content", "") or ""
            c = getattr(resp, "content", None)
            if c is not None:
                if isinstance(c, list):
                    parts = []
                    for s in c:
                        parts.append(getattr(s, "text", s if isinstance(s, str) else str(s)))
                    return "".join(parts)
                return c if isinstance(c, str) else str(c)
            return str(resp)
        except Exception:
            return str(resp)

    def _truncate(self, text: str, limit: int) -> str:
        """
        Truncate the text to a specified character limit, adding a prefix if truncated.

        :param text: The text to truncate.
        :param limit: The maximum number of characters to keep in the text.
        :return: Truncated text
        """
        if not text or not limit or limit <= 0:
            return text or ""
        if len(text) <= limit:
            return text
        return "...[truncated]...\n" + text[-limit:]

    def _build_context_for_subtask(
            self,
            completed: list[tuple[str, str]],
            dependencies: list[str],
            char_limit: int,
    ) -> str:
        """
        Build context for a sub-task based on completed tasks and dependencies.

        :param completed: List of completed sub-tasks with their outputs.
        :param dependencies: List of sub-task names that this sub-task depends on.
        :param char_limit: Character limit for the context text.
        :return: A formatted string containing the context for the sub-task.
        """
        if not completed:
            return ""

        if dependencies:
            selected = [(n, out) for (n, out) in completed if n in set(dependencies)]
            if not selected:
                return ""
        else:
            selected = completed

        parts = []
        for idx, (name, output) in enumerate(selected, 1):
            clean = (output or "").strip()
            if not clean:
                continue
            parts.append(f"[{idx}] {name} -> {clean}")

        if not parts:
            return ""

        ctx_text = "Completed sub-tasks context:\n" + "\n".join(parts)
        return self._truncate(ctx_text, char_limit or 8000)

    async def _run_subtask(self, ctx: Context, prompt: str) -> str:
        """
        Run a sub-task using the executor agent.

        :param ctx: The context in which the sub-task is executed.
        :param prompt: The prompt for the sub-task.
        """
        if self._clear_exec_mem_between_subtasks:
            self._reset_executor_memory()

        sig = inspect.signature(self._executor.run)
        kwargs = {}
        if "user_msg" in sig.parameters:
            kwargs["user_msg"] = prompt
        elif "input" in sig.parameters:
            kwargs["input"] = prompt
        elif "query" in sig.parameters:
            kwargs["query"] = prompt
        elif "task" in sig.parameters:
            kwargs["task"] = prompt
        if "max_steps" in sig.parameters:
            kwargs["max_steps"] = self._max_steps

        handler = self._executor.run(**kwargs)
        last_answer = ""
        has_stream = False
        stream_buf = []

        async def _stream():
            nonlocal last_answer, has_stream

            async for e in handler.stream_events():
                if isinstance(e, StopEvent):
                    continue

                # stop callback
                if self._stopped():
                    ctx.write_event_to_stream(StopEvent())
                    await handler.cancel_run()
                    return last_answer or ("".join(stream_buf).strip() if stream_buf else "")

                if isinstance(e, AgentStream):
                    delta = getattr(e, "delta", None)
                    if delta:
                        has_stream = True
                        stream_buf.append(str(delta))
                    if not getattr(e, "current_agent_name", None):
                        try:
                            e.current_agent_name = self._executor.name
                        except Exception:
                            pass
                    ctx.write_event_to_stream(e)
                    continue

                if isinstance(e, AgentOutput):
                    resp = getattr(e, "response", None)
                    content = self._to_text(resp).strip()
                    last_answer = content or ("".join(stream_buf).strip() if stream_buf else "")
                    if not has_stream and last_answer:
                        ctx.write_event_to_stream(
                            AgentStream(
                                delta=last_answer,
                                response=last_answer,
                                current_agent_name=f"{self._executor.name} (subtask)",
                                tool_calls=e.tool_calls,
                                raw=e.raw,
                            )
                        )
                    continue

                if isinstance(e, (ToolCall, ToolCallResult)):
                    ctx.write_event_to_stream(e)
                    continue

                if isinstance(e, Event):
                    ctx.write_event_to_stream(e)

            try:
                await handler
            except Exception:
                pass

            return last_answer or ("".join(stream_buf).strip() if stream_buf else "")

        try:
            return await _stream()
        except Exception as ex:
            await self._emit_text(ctx, f"\n`Sub-task failed: {ex}`")
            return last_answer or ("".join(stream_buf).strip() if stream_buf else "")

    @step
    async def make_plan(self, ctx: Context, ev: QueryEvent) -> PlanReady:
        """
        Create a plan based on the provided query and available tools.

        :param ctx: Context in which the plan is created.
        :param ev: QueryEvent containing the query to process.
        :return: PlanReady event containing the generated plan and query.
        """
        tools_str = ""
        for t in self._tools:
            tools_str += f"{(t.metadata.name or '').strip()}: {(t.metadata.description or '').strip()}\n"

        memory_context = self._memory_to_text(self._memory)

        try:
            plan = await self._planner_llm.astructured_predict(
                Plan,
                self._initial_plan_prompt,
                tools_str=tools_str,
                task=ev.query,
                memory_context=memory_context,
            )
        except (ValueError, ValidationError):
            plan = Plan(sub_tasks=[SubTask(name="default", input=ev.query, expected_output="", dependencies=[])])

        lines = ["`Current plan:`"]
        for i, st in enumerate(plan.sub_tasks, 1):
            lines.append(
                f"\n**===== Sub Task {i}: {st.name} =====**\n"
                f"Expected output: {st.expected_output}\n"
                f"Dependencies: {st.dependencies}\n\n"
            )
        await self._emit_text(ctx, "\n".join(lines))
        return PlanReady(plan=plan, query=ev.query)

    @step
    async def execute_plan(self, ctx: Context, ev: PlanReady) -> FinalEvent:
        """
        Execute the plan created in the previous step.

        :param ctx: Context in which the plan is executed.
        :param ev: PlanReady event containing the plan and query.
        """
        plan_sub_tasks = list(ev.plan.sub_tasks)
        total = len(plan_sub_tasks)

        last_answer = ""
        completed: list[tuple[str, str]] = []  # (name, output)

        await self._emit_text(ctx, "\n\n`Executing plan...`")

        for i, st in enumerate(plan_sub_tasks, 1):
            self._emit_step_event(
                ctx,
                name="subtask",
                index=i,
                total=total,
                meta={
                    "name": st.name,
                    "expected_output": st.expected_output,
                    "dependencies": st.dependencies,
                    "input": st.input,
                },
            )

            header = (
                f"\n\n**===== Sub Task {i}/{total}: {st.name} =====**\n"
                f"Expected output: {st.expected_output}\n"
                f"Dependencies: {st.dependencies}\n\n"
            )

            # stop callback
            if self._stopped():
                await self._emit_text(ctx, "\n`Plan execution stopped.`")
                return FinalEvent(result=last_answer or "Plan execution stopped.")

            await self._emit_text(ctx, header)

            # build context for sub-task
            ctx_text = self._build_context_for_subtask(
                completed=completed,
                dependencies=st.dependencies or [],
                char_limit=self._memory_char_limit,
            )

            # make composed prompt for sub-task
            if ctx_text:
                composed_prompt = (
                    f"{ctx_text}\n\n"
                    f"Now execute the next sub-task: {st.name}\n"
                    f"Instructions:\n{st.input}\n"
                    f"Return only the final output."
                )
            else:
                composed_prompt = st.input

            # run the sub-task
            sub_answer = await self._run_subtask(ctx, composed_prompt)
            sub_answer = (sub_answer or "").strip()

            await self._emit_text(ctx, f"\n\n`Finished Sub Task {i}/{total}: {st.name}`")

            # save completed sub-task
            completed.append((st.name, sub_answer))
            if sub_answer:
                last_answer = sub_answer

            # TODO: refine plan if needed

        await self._emit_text(ctx, "\n\n`Plan execution finished.`")
        return FinalEvent(result=last_answer or "Plan finished.")