#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.27 10:00:00                  #
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
    # noqa
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

# Translation utility
from pygpt_net.utils import trans


class SubTask(BaseModel):
    name: str = Field(..., description="The name of the sub-task.")
    input: str = Field(..., description="The input prompt for the sub-task.")
    expected_output: str = Field(..., description="The expected output of the sub-task.")
    dependencies: List[str] = Field(
        ..., description="Names of sub-tasks that must be completed before this sub-task."
    )


class Plan(BaseModel):
    sub_tasks: List[SubTask] = Field(..., description="The sub-tasks in the plan.")


# Structured refinement output to emulate the legacy Planner's refine behavior.
class PlanRefinement(BaseModel):
    is_done: bool = Field(..., description="Whether the overall task is already satisfied.")
    reason: Optional[str] = Field(None, description="Short justification why the plan is complete or needs update.")
    plan: Optional[Plan] = Field(
        default=None,
        description="An updated plan that replaces the remaining sub-tasks. Omit if is_done=True or no update is needed.",
    )


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

# Refinement prompt tuned to prevent premature completion and enforce "final deliverable present" rule.
DEFAULT_PLAN_REFINE_PROMPT = """\
You have the following prior context/memory (may be empty):
{memory_context}

Think step-by-step. Given an overall task, a set of tools, and completed sub-tasks, decide whether the overall task is already satisfied.
If not, update the remaining sub-tasks so that the overall task can still be completed.

Completion criteria (ALL must be true to set is_done=true):
- A final, user-facing answer that directly satisfies "Overall Task" already exists within "Completed Sub-Tasks + Outputs".
- The final answer matches any explicit format and language requested in "Overall Task".
- No critical transformation/summarization/finalization step remains among "Remaining Sub-Tasks" (e.g., steps like: provide/present/report/answer/summarize/finalize/deliver the result).
- The final answer does not rely on placeholders such as "will be provided later" or "see plan above".

If ANY of the above is false, set is_done=false.

Update policy:
- If the remaining sub-tasks are already reasonable and correctly ordered, do not propose changes: set is_done=false and omit "plan".
- Only propose a new "plan" if you need to REPLACE the "Remaining Sub-Tasks" (e.g., wrong order, missing critical steps, or new info from completed outputs).
- Do NOT repeat any completed sub-task. New sub-tasks must replace only the "Remaining Sub-Tasks".

Output schema:
- Return a JSON object matching the schema with fields: is_done (bool), reason (string), and optional plan (Plan).

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
        refine_after_each_subtask: bool = True,
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

        # Human-friendly display names propagated to UI via workflow events.
        self._display_planner_name: str = trans("agent.planner.display.planner")  # UI label
        self._display_executor_name: str = trans("agent.planner.display.executor_agent")  # UI label

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

        # Controls whether the legacy-style refine happens after every sub-task execution.
        self._refine_after_each_subtask = refine_after_each_subtask

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

    # Build human-friendly, step-scoped labels to display in the UI instead of agent names.
    def _agent_label(
        self,
        step: str,
        index: Optional[int] = None,
        total: Optional[int] = None,
        subtask_name: Optional[str] = None,
    ) -> str:
        if step == "subtask":
            if index and total:
                base = trans("agent.planner.label.subtask.index_total").format(index=index, total=total)
            elif index:
                base = trans("agent.planner.label.subtask.index").format(index=index)
            else:
                base = trans("agent.planner.label.subtask")
            return trans("agent.planner.label.with_name").format(base=base, name=subtask_name) if subtask_name else base
        if step == "refine":
            if index and total:
                return trans("agent.planner.label.refine.index_total").format(index=index, total=total)
            return trans("agent.planner.label.refine.index").format(index=index) if index else trans("agent.planner.label.refine")
        if step in {"make_plan", "plan"}:
            return trans("agent.planner.label.plan")
        if step in {"execute", "execute_plan"}:
            return trans("agent.planner.label.execute")
        return trans("agent.planner.label.step")

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
        # Always pass a friendly per-step label as "agent_name".
        m = dict(meta or {})
        label = self._agent_label(
            step=name,
            index=index,
            total=total,
            subtask_name=m.get("name"),
        )
        m["agent_name"] = label

        try:
            ctx.write_event_to_stream(
                StepEvent(name=name, index=index, total=total, meta=m)
            )
        except Exception:
            # fallback for older versions of AgentStream
            try:
                ctx.write_event_to_stream(
                    AgentStream(
                        delta="",
                        response="",
                        current_agent_name=label,
                        tool_calls=[],
                        raw={"StepEvent": {"name": name, "index": index, "total": total, "meta": m}}
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
            agent_name: Optional[str] = None
    ):
        """
        Emit a text message to the context stream.

        :param ctx: The context to write the event to.
        :param text: The text message to emit.
        :param agent_name: The name/label to display in UI (we pass per-step labels here).
        """
        label = agent_name or self._display_planner_name
        # Always try to include agent name; fall back to minimal event for older validators.
        try:
            ctx.write_event_to_stream(
                AgentStream(
                    delta=text,
                    response=text,
                    current_agent_name=label,
                    tool_calls=[],
                    raw={},
                )
            )
        except ValidationError:
            ctx.write_event_to_stream(AgentStream(delta=text))

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

    async def _run_subtask(self, ctx: Context, prompt: str, agent_label: Optional[str] = None) -> str:
        """
        Run a sub-task using the executor agent.

        :param ctx: The context in which the sub-task is executed.
        :param prompt: The prompt for the sub-task.
        :param agent_label: Per-step UI label (e.g., 'Sub-task 1/7: ...') used instead of agent name.
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
                    # Force the per-step label for executor events.
                    try:
                        e.current_agent_name = agent_label or self._display_executor_name
                    except Exception:
                        try:
                            e = AgentStream(
                                delta=getattr(e, "delta", ""),
                                response=getattr(e, "response", ""),
                                current_agent_name=agent_label or self._display_executor_name,
                                tool_calls=getattr(e, "tool_calls", []),
                                raw=getattr(e, "raw", {}),
                            )
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
                                current_agent_name=agent_label or self._display_executor_name,
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
            await self._emit_text(
                ctx,
                f"\n`{trans('agent.planner.ui.subtask_failed').format(error=ex)}`",
                agent_name=agent_label or self._display_executor_name,
            )
            return last_answer or ("".join(stream_buf).strip() if stream_buf else "")

    # Helper to render sub-tasks into a readable string for prompts and UI.
    def _format_subtasks(self, sub_tasks: List[SubTask]) -> str:
        parts = []
        for i, st in enumerate(sub_tasks, 1):
            parts.append(
                f"[{i}] name={st.name}\n"
                f"    input={st.input}\n"
                f"    expected_output={st.expected_output}\n"
                f"    dependencies={st.dependencies}"
            )
        return "\n".join(parts) if parts else "(none)"

    # Helper to render completed outputs for refinement prompt.
    def _format_completed(self, completed: list[tuple[str, str]]) -> str:
        if not completed:
            return "(none)"
        parts = []
        for i, (name, out) in enumerate(completed, 1):
            parts.append(f"[{i}] {name} -> {self._truncate((out or '').strip(), 2000)}")
        joined = "\n".join(parts)
        return self._truncate(joined, self._memory_char_limit or 8000)

    async def _refine_plan(
        self,
        ctx: Context,
        task: str,
        tools_str: str,
        completed: list[tuple[str, str]],
        remaining: List[SubTask],
        memory_context: str,
        agent_label: Optional[str] = None,
    ) -> Optional[PlanRefinement]:
        """
        Ask the planner LLM to refine the plan. Returns a PlanRefinement or None on failure.
        """
        completed_text = self._format_completed(completed)
        remaining_text = self._format_subtasks(remaining)

        # Emit a lightweight status line to the UI.
        await self._emit_text(
            ctx,
            f"\n`{trans('agent.planner.ui.refining_remaining_plan')}`",
            agent_name=agent_label or trans("agent.planner.label.refine"),
        )

        try:
            refinement = await self._planner_llm.astructured_predict(
                PlanRefinement,
                self._plan_refine_prompt,
                tools_str=tools_str,
                task=task,
                completed_outputs=completed_text,
                remaining_sub_tasks=remaining_text,
                memory_context=memory_context,
            )
            return refinement
        except (ValueError, ValidationError):
            # Graceful fallback if the model fails to conform to schema.
            return None

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

        lines = [f"`{trans('agent.planner.ui.current_plan')}`"]
        for i, st in enumerate(plan.sub_tasks, 1):
            header = trans("agent.planner.ui.subtask_header.one").format(index=i, name=st.name)
            lines.append(
                f"\n{header}\n"
                f"{trans('agent.planner.ui.expected_output')} {st.expected_output}\n"
                f"{trans('agent.planner.ui.dependencies')} {st.dependencies}\n\n"
            )
        # Use a per-step label for plan creation
        await self._emit_text(ctx, "\n".join(lines), agent_name=self._agent_label("make_plan"))
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

        # Start executing with a per-step label
        execute_label = self._agent_label("execute")
        await self._emit_text(ctx, f"\n\n`{trans('agent.planner.ui.executing_plan')}`", agent_name=execute_label)

        # Prepare static prompt parts for refinement.
        tools_str = ""
        for t in self._tools:
            tools_str += f"{(t.metadata.name or '').strip()}: {(t.metadata.description or '').strip()}\n"
        memory_context = self._memory_to_text(self._memory)

        i = 0  # manual index to allow in-place plan updates during refinement
        while i < len(plan_sub_tasks):
            st = plan_sub_tasks[i]
            total = len(plan_sub_tasks)

            # Compute label for this sub-task
            subtask_label = self._agent_label("subtask", index=i + 1, total=total, subtask_name=st.name)

            self._emit_step_event(
                ctx,
                name="subtask",
                index=i + 1,
                total=total,
                meta={
                    "name": st.name,
                    "expected_output": st.expected_output,
                    "dependencies": st.dependencies,
                    "input": st.input,
                    # UI label for this sub-task step
                    "agent_name": subtask_label,
                },
            )

            header = trans("agent.planner.ui.subtask_header.progress").format(
                index=i + 1, total=total, name=st.name
            )
            header_block = (
                f"\n\n{header}\n"
                f"{trans('agent.planner.ui.expected_output')} {st.expected_output}\n"
                f"{trans('agent.planner.ui.dependencies')} {st.dependencies}\n\n"
            )

            # stop callback
            if self._stopped():
                await self._emit_text(ctx, f"\n`{trans('agent.planner.ui.execution_stopped')}`", agent_name=execute_label)
                return FinalEvent(result=last_answer or trans("agent.planner.ui.execution_stopped"))

            await self._emit_text(ctx, header_block, agent_name=subtask_label)

            # build context for sub-task
            ctx_text = self._build_context_for_subtask(
                completed=completed,
                dependencies=st.dependencies or [],
                char_limit=self._memory_char_limit,
            )

            # make composed prompt for sub-task (internal; do not translate)
            if ctx_text:
                composed_prompt = (
                    f"{ctx_text}\n\n"
                    f"Now execute the next sub-task: {st.name}\n"
                    f"Instructions:\n{st.input}\n"
                    f"Return only the final output."
                )
            else:
                composed_prompt = st.input

            # run the sub-task with the per-step label
            sub_answer = await self._run_subtask(ctx, composed_prompt, agent_label=subtask_label)
            sub_answer = (sub_answer or "").strip()

            await self._emit_text(
                ctx,
                f"\n\n`{trans('agent.planner.ui.subtask_finished').format(index=i + 1, total=total, name=st.name)}`",
                agent_name=subtask_label,
            )

            # save completed sub-task
            completed.append((st.name, sub_answer))
            if sub_answer:
                last_answer = sub_answer

            # Early stop check (external cancel)
            if self._stopped():
                await self._emit_text(ctx, f"\n`{trans('agent.planner.ui.execution_stopped')}`", agent_name=execute_label)
                return FinalEvent(result=last_answer or trans("agent.planner.ui.execution_stopped"))

            # Optional legacy-style refine after each sub-task
            i += 1  # move pointer to the next item before potential replacement of tail
            if self._refine_after_each_subtask and i < len(plan_sub_tasks):
                remaining = plan_sub_tasks[i:]
                # Label for refine step
                refine_label = self._agent_label("refine", index=i, total=len(plan_sub_tasks))

                # Emit a step event for refine to keep UI parity with the legacy Planner.
                self._emit_step_event(
                    ctx,
                    name="refine",
                    index=i,
                    total=len(plan_sub_tasks),
                    meta={"agent_name": refine_label},
                )

                refinement = await self._refine_plan(
                    ctx=ctx,
                    task=ev.query,
                    tools_str=tools_str,
                    completed=completed,
                    remaining=remaining,
                    memory_context=memory_context,
                    agent_label=refine_label,
                )

                # If refinement failed to parse, skip gracefully.
                if refinement is None:
                    continue

                # If the planner states the task is complete, stop early.
                if getattr(refinement, "is_done", False):
                    reason = getattr(refinement, "reason", "") or "Planner judged the task as satisfied."
                    await self._emit_text(
                        ctx,
                        f"\n`{trans('agent.planner.ui.plan_marked_complete').format(reason=reason)}`",
                        agent_name=refine_label,
                    )
                    await self._emit_text(
                        ctx,
                        f"\n\n`{trans('agent.planner.ui.plan_execution_finished')}`",
                        agent_name=execute_label,
                    )
                    return FinalEvent(result=last_answer or trans("agent.planner.ui.plan_finished"))

                # If an updated plan was provided, replace the remaining sub-tasks.
                if refinement.plan and refinement.plan.sub_tasks is not None:
                    # Filter out any sub-tasks that repeat completed names to avoid loops.
                    completed_names = {n for (n, _) in completed}
                    new_remaining = [st for st in refinement.plan.sub_tasks if st.name not in completed_names]

                    # If nothing changes, continue.
                    current_remaining_repr = self._format_subtasks(remaining)
                    new_remaining_repr = self._format_subtasks(new_remaining)
                    if new_remaining_repr.strip() != current_remaining_repr.strip():
                        plan_sub_tasks = plan_sub_tasks[:i] + new_remaining
                        # Present the updated tail of the plan to the UI.
                        lines = [f"`{trans('agent.planner.ui.updated_remaining_plan')}`"]
                        for k, st_upd in enumerate(new_remaining, i + 1):
                            upd_header = trans("agent.planner.ui.subtask_header.progress").format(
                                index=k, total=len(plan_sub_tasks), name=st_upd.name
                            )
                            lines.append(
                                f"\n{upd_header}\n"
                                f"{trans('agent.planner.ui.expected_output')} {st_upd.expected_output}\n"
                                f"{trans('agent.planner.ui.dependencies')} {st_upd.dependencies}\n\n"
                            )
                        await self._emit_text(ctx, "\n".join(lines), agent_name=refine_label)

        await self._emit_text(ctx, f"\n\n`{trans('agent.planner.ui.plan_execution_finished')}`", agent_name=execute_label)
        return FinalEvent(result=last_answer or trans("agent.planner.ui.plan_finished"))