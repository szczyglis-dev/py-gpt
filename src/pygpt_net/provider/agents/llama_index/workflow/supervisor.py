# workflow/supervisor.py

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.26 22:25:00                  #
# ================================================== #

import re
from typing import Optional, Literal, List, Callable, Any
from pydantic import BaseModel, ValidationError
from llama_index.core.workflow import Workflow, Context, StartEvent, StopEvent, Event, step
from llama_index.core.agent.workflow import FunctionAgent, AgentStream
from llama_index.core.memory import Memory

# ==== Prompts ====
SUPERVISOR_PROMPT = """
You are the “Supervisor” – the main orchestrator. Do not use tools directly.
Your tasks:
- Break down the user's task into steps and create precise instructions for the “Worker” agent.
- Do not pass your history/memory to the Worker. Only pass minimal, self-sufficient instructions.
- After each Worker response, assess progress towards the Definition of Done (DoD). If not met – generate a better instruction.
- Ask the user only when absolutely necessary. Then stop and return the question.
- When the task is complete – return the final answer to the user.
Always return only ONE JSON object:
{
  "action": "task" | "final" | "ask_user",
  "instruction": "<Worker's instruction or ''>",
  "final_answer": "<final answer or ''>",
  "question": "<user question or ''>",
  "reasoning": "<brief reasoning and quality control>",
  "done_criteria": "<list/text of DoD criteria>"
}
Ensure proper JSON (no comments, no trailing commas). Respond in the user's language.
"""

WORKER_PROMPT = """
You are the “Worker” – executor of the Supervisor's instructions. You have your own memory and tools.
- Execute the Supervisor's instructions precisely and concisely.
- Use the available tools and return a brief result + relevant data/reasoning.
- Maintain the working context in your memory (only Worker).
- Return plain text (not JSON) unless instructed otherwise by the Supervisor.
- Respond in the user's language.
"""


# ==== Supervisor's JSON Structures ====
class SupervisorDirective(BaseModel):
    action: Literal["task", "final", "ask_user"]
    instruction: str = ""
    final_answer: str = ""
    question: str = ""
    reasoning: str = ""
    done_criteria: str = ""

JSON_RE = re.compile(r"\{[\s\S]*\}$", re.MULTILINE)

def parse_supervisor_json(text: str) -> SupervisorDirective:
    """
    Parse the Supervisor's JSON response from text.

    :param text: The text response from the Supervisor.
    :return: SupervisorDirective: Parsed directive from the Supervisor.
    """
    try:
        return SupervisorDirective.model_validate_json(text)
    except Exception:
        pass
    fence = re.search(r"```json\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if fence:
        try:
            return SupervisorDirective.model_validate_json(fence.group(1).strip())
        except Exception:
            pass
    tail = JSON_RE.findall(text)
    for candidate in tail[::-1]:
        try:
            return SupervisorDirective.model_validate_json(candidate.strip())
        except Exception:
            continue
    first = text.find("{")
    if first != -1:
        try:
            return SupervisorDirective.model_validate_json(text[first:])
        except Exception:
            pass
    raise ValueError("Failed to parse a valid JSON from the Supervisor's response.")

# ==== Workflow Events ====
class InputEvent(StartEvent):
    user_msg: str
    external_context: Optional[str] = ""
    round_idx: int = 0
    max_rounds: int = 8
    stop_on_ask_user: bool = True
    last_worker_output: Optional[str] = None

class ExecuteEvent(Event):
    instruction: str
    round_idx: int
    max_rounds: int
    external_context: str = ""
    stop_on_ask_user: bool = True

class OutputEvent(StopEvent):
    status: Literal["final", "ask_user", "max_rounds"]
    final_answer: str
    rounds_used: int

# ==== Main Workflow ====
class SupervisorWorkflow(Workflow):
    _supervisor: FunctionAgent
    _worker: FunctionAgent
    _supervisor_memory: Memory
    _worker_memory: Memory
    _max_steps: int = 12

    def __init__(self, **kwargs):
        super().__init__(timeout=kwargs.get("timeout", 120), verbose=kwargs.get("verbose", True))
        self._supervisor = kwargs["supervisor"]
        self._worker = kwargs["worker"]
        self._worker_memory = kwargs.get("worker_memory")
        self._max_steps = kwargs.get("max_steps", 12)

    def run(
        self,
        query: str,
        ctx: Optional[Context] = None,
        memory: Optional[Memory] = None,  # <- only for Supervisor
        verbose: bool = False,
        **kwargs
    ):
        """
        Run the SupervisorWorkflow with the given query and context.

        :param query: The user's query to start the workflow.
        :param ctx: Context for the workflow, used to write events.
        :param memory: Optional memory for the Supervisor agent. If not provided, it uses the default memory.
        :param verbose: If True, enables verbose output for the workflow.
        :param kwargs: Additional keyword arguments for the workflow, such as `external_context`, `stop_on_ask_user`, etc.
        :return: OutputEvent or ExecuteEvent based on the workflow's progress.
        """
        if verbose:
            self._verbose = True

        if memory is not None:
            self._supervisor_memory = memory  # use external memory for Supervisor

        start_event = InputEvent(
            user_msg=query,
            external_context=kwargs.get("external_context", ""),
            round_idx=0,
            max_rounds=self._max_steps,
            stop_on_ask_user=kwargs.get("stop_on_ask_user", True),
            last_worker_output=None,
        )
        return super().run(ctx=ctx, start_event=start_event)

    async def _emit_text(
            self,
            ctx: Context,
            text: str,
            agent_name: str = "SupervisorWorkflow"
    ):
        """
        Emit a text message to the context stream.

        :param ctx: The context to write the event to
        :param text: The text message to emit.
        :param agent_name: The name of the agent emitting the text (default: "PlannerWorkflow").
        """
        try:
            ctx.write_event_to_stream(
                AgentStream(
                    delta=text,
                    response=text,
                    current_agent_name=agent_name,
                    tool_calls=[],
                    raw={},
                )
            )
        except ValidationError:
            ctx.write_event_to_stream(AgentStream(delta=text))

    async def _emit_step(self, ctx: Context, agent_name: str, index: int, total: int, meta: Optional[dict] = None):
        """
        Emit a StepEvent that your runner uses to split UI into blocks.
        Mirrors the behavior used by the schema-driven workflow.
        """
        from pygpt_net.provider.agents.llama_index.workflow.events import StepEvent
        try:
            ctx.write_event_to_stream(
                StepEvent(
                    name="next",
                    index=index,
                    total=total,
                    meta={"agent_name": agent_name, **(meta or {})},
                )
            )
        except Exception:
            pass

    async def _run_muted(self, ctx: Context, awaitable) -> Any:
        """
        Execute an agent call while muting all events sent to ctx.
        Matches schema-style emission: we control all UI events ourselves.
        """
        orig_write = ctx.write_event_to_stream

        def _noop(ev: Any) -> None:
            return None

        ctx.write_event_to_stream = _noop
        try:
            return await awaitable
        finally:
            ctx.write_event_to_stream = orig_write

    @step
    async def supervisor_step(self, ctx: Context, ev: InputEvent) -> ExecuteEvent | OutputEvent:
        """
        Supervisor step: run Supervisor silently, then emit exactly one UI block like schema.

        :param ctx: Context for the workflow
        :param ev: InputEvent containing the user's message and context.
        :return: ExecuteEvent for the Worker or OutputEvent if final answer is reached.
        """
        parts: List[str] = []
        if ev.external_context:
            parts.append(f"<external_context>\n{ev.external_context}\n</external_context>")
        if ev.user_msg and ev.round_idx == 0:
            parts.append(f"<task_from_user>\n{ev.user_msg}\n</task_from_user>")
        if ev.last_worker_output:
            parts.append(f"<last_worker_output>\n{ev.last_worker_output}\n</last_worker_output>")
        parts.append(
            f"<control>\nround={ev.round_idx} max_rounds={ev.max_rounds}\n"
            "Return ONE JSON following the schema.\n</control>"
        )
        sup_input = "\n".join(parts)

        # Run Supervisor with stream muted to avoid extra blocks/finishes.
        sup_resp = await self._run_muted(ctx, self._supervisor.run(user_msg=sup_input, memory=self._supervisor_memory))
        directive = parse_supervisor_json(str(sup_resp))

        # Final/ask_user/max_rounds -> emit single Supervisor block and stop (schema-like).
        if directive.action == "final":
            await self._emit_step(ctx, agent_name=self._supervisor.name, index=ev.round_idx + 1, total=ev.max_rounds)
            await self._emit_text(ctx, f"\n\n{directive.final_answer or str(sup_resp)}", agent_name=self._supervisor.name)
            return OutputEvent(status="final", final_answer=directive.final_answer or str(sup_resp), rounds_used=ev.round_idx)

        if directive.action == "ask_user" and ev.stop_on_ask_user:
            await self._emit_step(ctx, agent_name=self._supervisor.name, index=ev.round_idx + 1, total=ev.max_rounds)
            q = directive.question or "I need more information, please clarify."
            await self._emit_text(ctx, f"\n\n{q}", agent_name=self._supervisor.name)
            return OutputEvent(status="ask_user", final_answer=q, rounds_used=ev.round_idx)

        if ev.round_idx >= ev.max_rounds:
            await self._emit_step(ctx, agent_name=self._supervisor.name, index=ev.round_idx + 1, total=ev.max_rounds)
            await self._emit_text(ctx, "\n\nMax rounds exceeded.", agent_name=self._supervisor.name)
            return OutputEvent(status="max_rounds", final_answer="Exceeded maximum number of iterations.", rounds_used=ev.round_idx)

        # Emit exactly one Supervisor block with the instruction (no JSON leakage, no duplicates).
        instruction = (directive.instruction or "").strip() or "Perform a step that gets closest to fulfilling the DoD."
        await self._emit_step(ctx, agent_name=self._supervisor.name, index=ev.round_idx + 1, total=ev.max_rounds)
        await self._emit_text(ctx, f"\n\n{instruction}", agent_name=self._supervisor.name)

        return ExecuteEvent(
            instruction=instruction,
            round_idx=ev.round_idx,
            max_rounds=ev.max_rounds,
            external_context=ev.external_context or "",
            stop_on_ask_user=ev.stop_on_ask_user,
        )

    @step
    async def worker_step(self, ctx: Context, ev: ExecuteEvent) -> InputEvent:
        """
        Worker step: run Worker silently and emit exactly one UI block like schema.

        :param ctx: Context for the workflow
        :param ev: ExecuteEvent containing the instruction and context.
        :return: InputEvent for the next round or final output.
        """
        # Run Worker with stream muted; we will emit a single block with the final text.
        worker_input = f"Instruction from Supervisor:\n{ev.instruction}\n"
        worker_resp = await self._run_muted(ctx, self._worker.run(user_msg=worker_input, memory=self._worker_memory))

        # Emit exactly one Worker block (schema-style: one AgentStream per node).
        await self._emit_step(ctx, agent_name=self._worker.name, index=ev.round_idx + 1, total=ev.max_rounds)
        await self._emit_text(ctx, f"\n\n{str(worker_resp)}", agent_name=self._worker.name)

        return InputEvent(
            user_msg="",
            last_worker_output=str(worker_resp),
            round_idx=ev.round_idx + 1,
            max_rounds=ev.max_rounds,
            external_context=ev.external_context,
            stop_on_ask_user=ev.stop_on_ask_user,
        )

# ==== Factory ====
def get_workflow(
    tools,
    llm_supervisor,
    llm_worker,
    verbose: bool = False,
    prompt_supervisor: str = SUPERVISOR_PROMPT,
    prompt_worker: str = WORKER_PROMPT,
    max_steps: int = 12,
    worker_memory_session_id: str = "llama_worker_session"  # session ID for worker memory
):
    """
    Create a SupervisorWorkflow instance.

    :param tools: List of tools for the Worker agent.
    :param llm_supervisor: LLM instance for the Supervisor agent.
    :param llm_worker: LLM instance for the Worker agent.
    :param verbose: Verbose output flag.
    :param prompt_supervisor: Prompt for the Supervisor agent.
    :param prompt_worker: Prompt for the Worker agent.
    :param max_steps: Maximum number of steps for the workflow.
    :param worker_memory_session_id: Session ID for the Worker agent's memory.
    :return: SupervisorWorkflow instance
    """
    supervisor = FunctionAgent(
        name="Supervisor",
        llm=llm_supervisor,
        system_prompt=prompt_supervisor,
        tools=[],
    )
    worker = FunctionAgent(
        name="Worker",
        llm=llm_worker,
        system_prompt=prompt_worker,
        tools=tools,
    )

    # separate memory for the worker
    worker_memory = Memory.from_defaults(session_id=worker_memory_session_id, token_limit=40000)

    return SupervisorWorkflow(
        supervisor=supervisor,
        worker=worker,
        worker_memory=worker_memory,
        verbose=verbose,
        timeout=120,
        max_steps=max_steps,
    )