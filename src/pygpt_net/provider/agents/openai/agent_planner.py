#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.27 14:40:00                  #
# ================================================== #

from dataclasses import dataclass
from typing import Dict, Any, Tuple, Optional, List

from agents import (
    Agent as OpenAIAgent,
    Runner,
    RunConfig,
    TResponseInputItem,
)

from pygpt_net.core.agents.bridge import ConnectionContext
from pygpt_net.core.bridge import BridgeContext
from pygpt_net.core.types import (
    AGENT_MODE_OPENAI,
    AGENT_TYPE_OPENAI,
)

from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.model import ModelItem
from pygpt_net.item.preset import PresetItem

from pygpt_net.provider.api.openai.agents.client import get_custom_model_provider, set_openai_env
from pygpt_net.provider.api.openai.agents.remote_tools import append_tools
from pygpt_net.provider.api.openai.agents.response import StreamHandler
from pygpt_net.provider.api.openai.agents.experts import get_experts
from pygpt_net.utils import trans

from ..base import BaseAgent


# ---------- Structured types to mirror the LlamaIndex Planner ----------
@dataclass
class SubTask:
    name: str
    input: str
    expected_output: str
    dependencies: List[str]


@dataclass
class Plan:
    sub_tasks: List[SubTask]


@dataclass
class PlanRefinement:
    is_done: bool
    reason: Optional[str]
    plan: Optional[Plan]


class Agent(BaseAgent):
    # System prompts used as templates, exposed in options (planner.initial_prompt, refine.prompt).
    DEFAULT_INITIAL_PLAN_PROMPT = """\
You have the following prior context/memory (may be empty):
{memory_context}

Think step-by-step. Given a task and a set of tools, create a comprehensive, end-to-end plan to accomplish the task.
Keep in mind not every task needs to be decomposed into multiple sub-tasks if it is simple enough.
The plan should end with a sub-task that can achieve the overall task.

The tools available are:
{tools_str}

Overall Task: {task}

Return a JSON object that matches this schema exactly:
{
  "sub_tasks": [
    {
      "name": "string",
      "input": "string",
      "expected_output": "string",
      "dependencies": ["string", "..."]
    }
  ]
}
"""

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

Output schema (strict JSON):
{
  "is_done": true|false,
  "reason": "string or null",
  "plan": {
    "sub_tasks": [
      {
        "name": "string",
        "input": "string",
        "expected_output": "string",
        "dependencies": ["string", "..."]
      }
    ]
  } | null
}

The tools available are:
{tools_str}

Completed Sub-Tasks + Outputs:
{completed_outputs}

Remaining Sub-Tasks:
{remaining_sub_tasks}

Overall Task: {task}
"""

    # Base executor instruction used by the main execution agent (internal default).
    # Note: keep this concise but explicit that tools must be used for any external action.
    PROMPT = (
        "You are an execution agent. Follow each sub-task strictly and use the available tools to take actions. "
        "Do not claim that you cannot access files or the web; instead, invoke the appropriate tool. "
        "For local files prefer the sequence: cwd -> find (pattern, path, recursive=true) -> read_file(path). "
        "Return only the final output unless explicitly asked for intermediate thoughts."
    )

    def __init__(self, *args, **kwargs):
        super(Agent, self).__init__(*args, **kwargs)
        self.id = "openai_agent_planner"
        self.type = AGENT_TYPE_OPENAI
        self.mode = AGENT_MODE_OPENAI
        self.name = "Planner"
        self._memory_char_limit = 8000  # consistent with the LlamaIndex workflow

    # ---------- Helpers: planning/execution parity with LlamaIndex + bridge persistence ----------

    def _truncate(self, text: str, limit: int) -> str:
        if not text or not limit or limit <= 0:
            return text or ""
        if len(text) <= limit:
            return text
        return "...[truncated]...\n" + text[-limit:]

    def _memory_to_text(self, messages: Optional[List[Dict[str, Any]]]) -> str:
        if not messages:
            return ""
        try:
            parts = []
            for m in messages:
                role = m.get("role", "user")
                content = m.get("content", "")
                parts.append(f"{role}: {content}")
            text = "\n".join(parts)
        except Exception:
            try:
                text = str(messages)
            except Exception:
                text = ""
        return self._truncate(text, self._memory_char_limit)

    def _tools_to_str(self, tools: List[Any]) -> str:
        out = []
        for t in tools or []:
            try:
                meta = getattr(t, "metadata", None)
                if meta is not None:
                    name = (getattr(meta, "name", "") or "").strip()
                    desc = (getattr(meta, "description", "") or "").strip()
                    if name or desc:
                        out.append(f"{name}: {desc}")
                        continue
                # Fallback for function-style tools
                name = (getattr(t, "name", "") or "").strip()
                desc = (getattr(t, "description", "") or "").strip()
                if name or desc:
                    out.append(f"{name}: {desc}")
                    continue
                if isinstance(t, dict):
                    name = (t.get("name") or "").strip()
                    desc = (t.get("description") or "").strip()
                    if name or desc:
                        out.append(f"{name}: {desc}")
                        continue
                out.append(str(t))
            except Exception:
                out.append(str(t))
        return "\n".join(out)

    def _format_subtasks(self, sub_tasks: List[SubTask]) -> str:
        parts = []
        for i, st in enumerate(sub_tasks or [], 1):
            parts.append(
                f"[{i}] name={st.name}\n"
                f"    input={st.input}\n"
                f"    expected_output={st.expected_output}\n"
                f"    dependencies={st.dependencies}"
            )
        return "\n".join(parts) if parts else "(none)"

    def _format_completed(self, completed: List[Tuple[str, str]]) -> str:
        if not completed:
            return "(none)"
        parts = []
        for i, (name, out) in enumerate(completed, 1):
            parts.append(f"[{i}] {name} -> {self._truncate((out or '').strip(), 2000)}")
        joined = "\n".join(parts)
        return self._truncate(joined, self._memory_char_limit or 8000)

    def _build_context_for_subtask(
            self,
            completed: List[Tuple[str, str]],
            dependencies: List[str],
            char_limit: int,
    ) -> str:
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

    def _compose_subtask_prompt(self, st: SubTask, completed: List[Tuple[str, str]]) -> str:
        """
        Compose the prompt for a single sub-task. Keep it explicit that tools should be used.
        """
        ctx_text = self._build_context_for_subtask(
            completed=completed,
            dependencies=st.dependencies or [],
            char_limit=self._memory_char_limit,
        )

        # Small, generic tool usage hint keeps the model from refusing actions.
        tool_hint = (
            "Use tools to take actions. For file operations use: "
            "'cwd' -> 'find' (pattern, path, recursive=true) -> 'read_file(path)'."
        )

        if ctx_text:
            return (
                f"{ctx_text}\n\n"
                f"{tool_hint}\n"
                f"Now execute the next sub-task: {st.name}\n"
                f"Instructions:\n{st.input}\n"
                f"Return only the final output."
            )
        return (
            f"{tool_hint}\n"
            f"{st.input}\n\n"
            f"Return only the final output."
        )

    def _agent_label(
            self,
            step: str,
            index: Optional[int] = None,
            total: Optional[int] = None,
            subtask_name: Optional[str] = None,
    ) -> str:
        if step == "subtask":
            if index and total:
                base = f"Sub-task {index}/{total}"
            elif index:
                base = f"Sub-task {index}"
            else:
                base = "Sub-task"
            return f"{base}: {subtask_name}" if subtask_name else base
        if step == "refine":
            if index and total:
                return f"Refine {index}/{total}"
            return "Refine" if not index else f"Refine {index}"
        if step in {"make_plan", "plan"}:
            return "Plan"
        if step in {"execute", "execute_plan"}:
            return "Execute"
        return step or "Step"

    def prepare_model(
            self,
            model: ModelItem,
            window: Any,
            previous_response_id: Optional[str],
            kwargs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Prepare per-run kwargs (keep parity with other agents).
        """
        if model.provider == "openai" and previous_response_id:
            kwargs["previous_response_id"] = previous_response_id
        return kwargs

    # ---------- OpenAI Agents providers ----------

    def get_agent(self, window, kwargs: Dict[str, Any]):
        """
        Return Agent provider instance

        :param window: window instance
        :param kwargs: keyword arguments
        :return: Agent provider instance
        """
        context = kwargs.get("context", BridgeContext())
        preset = context.preset
        # Keep a stable display name; fallback to 'Executor' if no preset
        agent_name = (preset.name if preset and getattr(preset, "name", None) else "Executor")
        model = kwargs.get("model", ModelItem())
        tools = kwargs.get("function_tools", [])
        handoffs = kwargs.get("handoffs", [])

        # Use internal default prompt, not options
        base_instructions = self.PROMPT

        allow_local_tools = bool(kwargs.get("allow_local_tools", False))
        allow_remote_tools = bool(kwargs.get("allow_remote_tools", False))

        cfg = {
            "name": agent_name,
            "instructions": base_instructions,
            "model": window.core.agents.provider.get_openai_model(model),
        }
        if handoffs:
            cfg["handoffs"] = handoffs

        tool_kwargs = append_tools(
            tools=tools,
            window=window,
            model=model,
            preset=preset,
            allow_local_tools=allow_local_tools,
            allow_remote_tools=allow_remote_tools,
        )
        # NOTE: do not remove this update; it attaches tools so the agent can invoke them.
        cfg.update(tool_kwargs)

        # Optional: expose tool names inside instructions to gently steer the model.
        try:
            tool_names = [getattr(t, "name", "").strip() for t in tool_kwargs.get("tools", [])]
            tool_names = [n for n in tool_names if n]
            if tool_names:
                cfg["instructions"] = (
                    f"{cfg['instructions']} "
                    f"Available tools: {', '.join(tool_names)}."
                )
        except Exception:
            pass

        return OpenAIAgent(**cfg)

    def get_planner(
            self,
            window,
            model: ModelItem,
            preset: PresetItem,
            tools: list,
            allow_local_tools: bool = False,
            allow_remote_tools: bool = False,
    ) -> OpenAIAgent:
        """
        Return Agent provider instance producing a structured Plan.
        """
        kwargs = {
            "name": "StructuredPlanner",
            # Minimal instructions; the full template is injected as user content.
            "instructions": "Return a JSON object matching the provided schema.",
            "model": window.core.agents.provider.get_openai_model(model),
            "output_type": Plan,
        }
        tool_kwargs = append_tools(
            tools=tools,
            window=window,
            model=model,
            preset=preset,
            allow_local_tools=allow_local_tools,
            allow_remote_tools=allow_remote_tools,
        )
        kwargs.update(tool_kwargs)  # update kwargs with tools
        return OpenAIAgent(**kwargs)

    def get_refiner(
            self,
            window,
            model: ModelItem,
            preset: PresetItem,
            tools: list,
            allow_local_tools: bool = False,
            allow_remote_tools: bool = False,
    ) -> OpenAIAgent:
        """
        Return Agent provider instance producing a structured PlanRefinement.
        """
        kwargs = {
            "name": "PlanRefiner",
            "instructions": "Refine remaining plan steps and return a strict JSON object as instructed.",
            "model": window.core.agents.provider.get_openai_model(model),
            "output_type": PlanRefinement,
        }
        tool_kwargs = append_tools(
            tools=tools,
            window=window,
            model=model,
            preset=preset,
            allow_local_tools=allow_local_tools,
            allow_remote_tools=allow_remote_tools,
        )
        kwargs.update(tool_kwargs)
        return OpenAIAgent(**kwargs)

    async def run(
            self,
            window: Any = None,
            agent_kwargs: Dict[str, Any] = None,
            previous_response_id: str = None,
            messages: list = None,
            ctx: CtxItem = None,
            stream: bool = False,
            bridge: ConnectionContext = None,
            use_partial_ctx: Optional[bool] = False,
    ) -> Tuple[CtxItem, str, str]:
        """
        Run agent (async)

        :param window: Window instance
        :param agent_kwargs: Additional agent parameters
        :param previous_response_id: ID of the previous response (if any)
        :param messages: Conversation messages
        :param ctx: Context item
        :param stream: Whether to stream output
        :param bridge: Connection context for handling stop and step events
        :param use_partial_ctx: Use partial ctx per cycle
        :return: Current ctx, final output, last response ID
        """
        final_output = ""
        response_id = None
        model = agent_kwargs.get("model", ModelItem())
        verbose = agent_kwargs.get("verbose", False)
        context = agent_kwargs.get("context", BridgeContext())
        max_steps = int(agent_kwargs.get("max_iterations", 10))
        tools = agent_kwargs.get("function_tools", [])
        preset = context.preset

        # add experts
        experts = get_experts(
            window=window,
            preset=preset,
            verbose=verbose,
            tools=tools,
        )
        if experts:
            agent_kwargs["handoffs"] = experts

        # Executor must have access to the same tool set as planner/refiner.
        # If not explicitly provided, inherit allow_* flags from planner options.
        exec_allow_local_tools = agent_kwargs.get("allow_local_tools")
        exec_allow_remote_tools = agent_kwargs.get("allow_remote_tools")
        if exec_allow_local_tools is None:
            exec_allow_local_tools = bool(self.get_option(preset, "planner", "allow_local_tools"))
        if exec_allow_remote_tools is None:
            exec_allow_remote_tools = bool(self.get_option(preset, "planner", "allow_remote_tools"))

        # executor agent (FunctionAgent equivalent)
        agent_exec_kwargs = dict(agent_kwargs)
        agent_exec_kwargs["allow_local_tools"] = bool(exec_allow_local_tools)
        agent_exec_kwargs["allow_remote_tools"] = bool(exec_allow_remote_tools)
        agent = self.get_agent(window, agent_exec_kwargs)

        # options
        planner_model_name = self.get_option(preset, "planner", "model")
        planner_model = window.core.models.get(planner_model_name) if planner_model_name else agent_kwargs.get("model",
                                                                                                               ModelItem())
        planner_allow_local_tools = bool(self.get_option(preset, "planner", "allow_local_tools"))
        planner_allow_remote_tools = bool(self.get_option(preset, "planner", "allow_remote_tools"))
        planner_prompt_tpl = self.get_option(preset, "planner", "initial_prompt") or self.DEFAULT_INITIAL_PLAN_PROMPT

        refine_model_name = self.get_option(preset, "refine", "model") or planner_model_name
        refine_allow_local_tools = bool(self.get_option(preset, "refine", "allow_local_tools"))
        refine_allow_remote_tools = bool(self.get_option(preset, "refine", "allow_remote_tools"))
        refine_prompt_tpl = self.get_option(preset, "refine", "prompt") or self.DEFAULT_PLAN_REFINE_PROMPT
        _after_each_val = self.get_option(preset, "refine", "after_each_subtask")
        refine_after_each = True if _after_each_val is None else bool(_after_each_val)

        # Common Runner kwargs baseline
        common_kwargs: Dict[str, Any] = {
            "max_turns": max_steps,
        }
        if model.provider != "openai":
            custom_provider = get_custom_model_provider(window, model)
            common_kwargs["run_config"] = RunConfig(model_provider=custom_provider)
        else:
            set_openai_env(window)

        # Build tool list description and memory context for prompts
        tools_str = self._tools_to_str(tools)
        query = messages[-1]["content"] if messages else ""
        memory_context = self._memory_to_text(messages)

        # Step lifecycle control for bridge
        begin = True  # first block only

        # ---------- Make plan (structured) ----------
        planner = self.get_planner(
            window=window,
            model=planner_model,
            preset=preset,
            tools=tools,
            allow_local_tools=planner_allow_local_tools,
            allow_remote_tools=planner_allow_remote_tools,
        )

        plan_prompt = planner_prompt_tpl.format(
            memory_context=memory_context,
            tools_str=tools_str,
            task=query,
        )
        plan_input_items: List[TResponseInputItem] = [{"role": "user", "content": plan_prompt}]

        try:
            planner_result = await Runner.run(planner, plan_input_items)
            plan_obj: Optional[Plan] = planner_result.final_output  # type: ignore
        except Exception:
            plan_obj = None

        if not plan_obj or not getattr(plan_obj, "sub_tasks", None):
            plan_obj = Plan(sub_tasks=[
                SubTask(
                    name="default",
                    input=f"{query}",
                    expected_output="",
                    dependencies=[],
                )
            ])

        # Present current plan as a dedicated step
        plan_lines = ["`Current plan:`"]
        for i, st in enumerate(plan_obj.sub_tasks, 1):
            plan_lines.append(
                f"\n**===== Sub Task {i}: {st.name} =====**\n"
                f"Expected output: {st.expected_output}\n"
                f"Dependencies: {st.dependencies}\n\n"
            )
        plan_text = "\n".join(plan_lines)

        ctx.set_agent_name(self._agent_label("make_plan"))
        ctx.stream = plan_text
        bridge.on_step(ctx, begin)
        begin = False

        # Persist plan step boundary without leaking inputs
        if use_partial_ctx:
            ctx = bridge.on_next_ctx(
                ctx=ctx,
                input="",
                output=plan_text,
                response_id="",
                finish=False,
                stream=stream,
            )
        else:
            bridge.on_next(ctx)

        # ---------- Execute plan with optional refinement after each sub-task ----------
        plan_sub_tasks: List[SubTask] = list(plan_obj.sub_tasks)
        last_answer = ""
        completed: List[Tuple[str, str]] = []  # (name, output)

        # Prepare static prompt parts for refinement
        memory_context = self._memory_to_text(messages)  # re-evaluate after plan message

        # shared stream handler for sub-task streaming
        handler = StreamHandler(window, bridge)

        # keep track of previous response id for provider continuity
        prev_rid: Optional[str] = previous_response_id

        i = 0
        while i < len(plan_sub_tasks):
            if bridge.stopped():
                bridge.on_stop(ctx)
                break

            st = plan_sub_tasks[i]
            total = len(plan_sub_tasks)

            # UI header for the sub-task
            subtask_label = self._agent_label("subtask", index=i + 1, total=total, subtask_name=st.name)
            header = (
                f"\n\n**===== Sub Task {i + 1}/{total}: {st.name} =====**\n"
                f"Expected output: {st.expected_output}\n"
                f"Dependencies: {st.dependencies}\n\n"
            )

            # Compose sub-task prompt and open a new persisted step
            composed_prompt = self._compose_subtask_prompt(st, completed)
            ctx.set_agent_name(subtask_label)
            ctx.stream = header
            bridge.on_step(ctx, False)  # open a new step block

            exec_kwargs = dict(common_kwargs)
            exec_items: List[TResponseInputItem] = [{"role": "user", "content": composed_prompt}]
            exec_kwargs["input"] = exec_items
            exec_kwargs = self.prepare_model(model, window, prev_rid, exec_kwargs)

            sub_answer = ""
            sub_rid = ""

            if not stream:
                try:
                    result = await Runner.run(agent, **exec_kwargs)
                    sub_rid = getattr(result, "last_response_id", "") or ""
                    sub_answer = str(getattr(result, "final_output", "") or "")
                except Exception as ex:
                    sub_answer = f"Sub-task failed: {ex}"

                if sub_answer:
                    ctx.stream = sub_answer
                    bridge.on_step(ctx, True)
            else:
                result = Runner.run_streamed(agent, **exec_kwargs)
                handler.reset()
                handler.begin = False
                async for event in result.stream_events():
                    if bridge.stopped():
                        result.cancel()
                        bridge.on_stop(ctx)
                        break
                    sub_answer, sub_rid = handler.handle(event, ctx)

            # Save completed sub-task
            sub_answer = (sub_answer or "").strip()
            completed.append((st.name, sub_answer))
            if sub_answer:
                last_answer = sub_answer
            if sub_rid:
                prev_rid = sub_rid
                response_id = sub_rid  # keep latest rid for return

            # Close persisted step (finish only if last and no refine)
            is_last_subtask = (i + 1 == len(plan_sub_tasks))
            will_refine = (refine_after_each and not is_last_subtask)
            if use_partial_ctx:
                ctx = bridge.on_next_ctx(
                    ctx=ctx,
                    input="",
                    output=sub_answer if sub_answer else header.strip(),
                    response_id=sub_rid,
                    finish=(is_last_subtask and not will_refine),
                    stream=stream,
                )
                if stream:
                    handler.new()
            else:
                bridge.on_next(ctx)

            if bridge.stopped():
                bridge.on_stop(ctx)
                break

            # Optional legacy-style refine after each sub-task (if there are remaining ones)
            i += 1
            if refine_after_each and i < len(plan_sub_tasks):
                remaining = plan_sub_tasks[i:]
                refine_label = self._agent_label("refine", index=i, total=len(plan_sub_tasks))

                # Start refine step
                refine_display = "\n`Refining remaining plan...`"
                ctx.set_agent_name(refine_label)
                ctx.stream = refine_display
                bridge.on_step(ctx, False)

                # Build refine prompt
                completed_text = self._format_completed(completed)
                remaining_text = self._format_subtasks(remaining)
                refine_prompt = refine_prompt_tpl.format(
                    memory_context=memory_context,
                    tools_str=tools_str,
                    completed_outputs=completed_text,
                    remaining_sub_tasks=remaining_text,
                    task=query,
                )
                model_refiner = window.core.models.get(refine_model_name) if refine_model_name else planner_model
                refiner = self.get_refiner(
                    window=window,
                    model=model_refiner,
                    preset=preset,
                    tools=tools,
                    allow_local_tools=refine_allow_local_tools,
                    allow_remote_tools=refine_allow_remote_tools,
                )

                refinement: Optional[PlanRefinement] = None
                refine_rid = ""
                try:
                    refinement_result = await Runner.run(refiner, [{"role": "user", "content": refine_prompt}])
                    refinement = refinement_result.final_output  # type: ignore
                    refine_rid = getattr(refinement_result, "last_response_id", "") or ""
                except Exception:
                    refinement = None

                if refinement is None:
                    refine_display += "\n`Refine step failed to parse; continuing without changes.`"
                    ctx.stream = "\n`Refine step failed to parse; continuing without changes.`"
                    bridge.on_step(ctx, True)
                    # finalize refine step
                    if use_partial_ctx:
                        ctx = bridge.on_next_ctx(
                            ctx=ctx,
                            input="",
                            output=refine_display,
                            response_id=refine_rid,
                            finish=False,
                            stream=False,
                        )
                    else:
                        bridge.on_next(ctx)
                    continue

                if getattr(refinement, "is_done", False):
                    reason = getattr(refinement, "reason", "") or "Planner judged the task as satisfied."
                    done_msg = f"\n`Planner marked the plan as complete: {reason}`"
                    refine_display += done_msg
                    ctx.stream = done_msg
                    bridge.on_step(ctx, True)

                    # finalize refine step as the last block
                    if use_partial_ctx:
                        ctx = bridge.on_next_ctx(
                            ctx=ctx,
                            input="",
                            output=refine_display,
                            response_id=refine_rid or (response_id or ""),
                            finish=True,
                            stream=False,
                        )
                    else:
                        bridge.on_next(ctx)
                    break

                if refinement.plan and getattr(refinement.plan, "sub_tasks", None):
                    completed_names = {n for (n, _) in completed}
                    new_remaining = [st for st in refinement.plan.sub_tasks if st.name not in completed_names]

                    current_remaining_repr = self._format_subtasks(remaining)
                    new_remaining_repr = self._format_subtasks(new_remaining)
                    if new_remaining_repr.strip() != current_remaining_repr.strip():
                        plan_sub_tasks = plan_sub_tasks[:i] + new_remaining
                        # Present the updated tail of the plan
                        lines = ["`Updated remaining plan:`"]
                        for k, st_upd in enumerate(new_remaining, i + 1):
                            lines.append(
                                f"\n**===== Sub Task {k}/{len(plan_sub_tasks)}: {st_upd.name} =====**\n"
                                f"Expected output: {st_upd.expected_output}\n"
                                f"Dependencies: {st_upd.dependencies}\n\n"
                            )
                        upd_text = "\n".join(lines)
                        refine_display += "\n" + upd_text
                        ctx.stream = upd_text
                        bridge.on_step(ctx, True)

                # finalize refine step (no extra noise)
                if use_partial_ctx:
                    ctx = bridge.on_next_ctx(
                        ctx=ctx,
                        input="",
                        output=refine_display,
                        response_id=refine_rid,
                        finish=False,
                        stream=False,
                    )
                else:
                    bridge.on_next(ctx)

        # Return last answer (final block already closed in the loop)
        return ctx, (last_answer or "Plan finished."), (response_id or "")

    def get_options(self) -> Dict[str, Any]:
        """
        Return Agent options

        :return: dict of options
        """
        return {
            "planner": {
                "label": trans("agent.option.section.planner"),
                "options": {
                    "model": {
                        "label": trans("agent.option.model"),
                        "type": "combo",
                        "use": "models",
                        "default": "gpt-4o",
                    },
                    "initial_prompt": {
                        "type": "textarea",
                        "label": trans("agent.option.prompt"),
                        "description": trans("agent.option.prompt.planner.desc"),
                        "default": self.DEFAULT_INITIAL_PLAN_PROMPT,
                    },
                    "allow_local_tools": {
                        "type": "bool",
                        "label": trans("agent.option.tools.local"),
                        "description": trans("agent.option.tools.local.desc"),
                        "default": True,
                    },
                    "allow_remote_tools": {
                        "type": "bool",
                        "label": trans("agent.option.tools.remote"),
                        "description": trans("agent.option.tools.remote.desc"),
                        "default": True,
                    },
                }
            },
            "refine": {
                "label": trans("agent.option.section.refine"),
                "options": {
                    "model": {
                        "label": trans("agent.option.model"),
                        "type": "combo",
                        "use": "models",
                        "default": "gpt-4o",
                    },
                    "prompt": {
                        "type": "textarea",
                        "label": trans("agent.option.prompt"),
                        "description": trans("agent.option.prompt.refine.desc"),
                        "default": self.DEFAULT_PLAN_REFINE_PROMPT,
                    },
                    "after_each_subtask": {
                        "type": "bool",
                        "label": trans("agent.option.refine.after_each"),
                        "description": trans("agent.option.refine.after_each.desc"),
                        "default": True,
                    },
                    "allow_local_tools": {
                        "type": "bool",
                        "label": trans("agent.option.tools.local"),
                        "description": trans("agent.option.tools.local.desc"),
                        "default": True,
                    },
                    "allow_remote_tools": {
                        "type": "bool",
                        "label": trans("agent.option.tools.remote"),
                        "description": trans("agent.option.tools.remote.desc"),
                        "default": True,
                    },
                }
            },
        }