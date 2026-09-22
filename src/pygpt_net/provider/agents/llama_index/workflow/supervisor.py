# workflow/supervisor.py

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.05 14:45:00                  #
# ================================================== #

import json
import re
from typing import Optional, Literal, List, Callable, Any
from pydantic import BaseModel, ValidationError, field_validator
from llama_index.core.workflow import Workflow, Context, StartEvent, StopEvent, Event, step
from llama_index.core.agent.workflow import FunctionAgent, AgentStream
from llama_index.core.memory import Memory

# ==== Prompts ====
SUPERVISOR_PROMPT = """
You are the “Supervisor” – the main orchestrator. You may use enabled tools directly when useful, while still delegating execution to the Worker when appropriate.
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
  "done_criteria": "<short text describing the DoD criteria>"
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

    @field_validator("action", mode="before")
    @classmethod
    def normalize_action(cls, value: Any) -> str:
        return str(value or "").strip().lower()

    @field_validator(
        "instruction",
        "final_answer",
        "question",
        "reasoning",
        "done_criteria",
        mode="before",
    )
    @classmethod
    def normalize_text_fields(cls, value: Any) -> str:
        """Accept common model variants while keeping one stable string schema."""
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, (list, tuple)):
            return "\n".join(str(item) for item in value if item is not None)
        if isinstance(value, dict):
            return json.dumps(value, ensure_ascii=False)
        return str(value)


def response_to_text(value: Any) -> str:
    """Extract plain assistant text from LlamaIndex agent/workflow return types.

    Depending on the LlamaIndex version, ``FunctionAgent.run()`` may resolve to
    a string, ChatMessage/ChatResponse-like object, or AgentOutput whose actual
    message is stored under ``response``.  ``str(value)`` is not safe for
    structured output because it can produce an object repr rather than the JSON
    emitted by the model.
    """
    seen = set()

    def _extract(obj: Any) -> str:
        if obj is None:
            return ""
        if isinstance(obj, str):
            return obj.strip()

        obj_id = id(obj)
        if obj_id in seen:
            return ""
        seen.add(obj_id)

        # AgentOutput -> response; ChatResponse -> message.
        for attr in ("response", "message"):
            nested = getattr(obj, attr, None)
            if nested is not None and nested is not obj:
                text = _extract(nested)
                if text:
                    return text

        # ChatMessage and response/block variants.
        content = getattr(obj, "content", None)
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, (list, tuple)):
            parts = []
            for block in content:
                block_text = getattr(block, "text", None)
                if isinstance(block_text, str):
                    parts.append(block_text)
                    continue
                extracted = _extract(block)
                if extracted:
                    parts.append(extracted)
            if parts:
                return "".join(parts).strip()

        text = getattr(obj, "text", None)
        if isinstance(text, str):
            return text.strip()

        return ""

    extracted = _extract(value)
    if extracted:
        return extracted
    return str(value or "").strip()

def _validate_supervisor_payload(payload: Any) -> SupervisorDirective:
    """Validate one decoded Supervisor payload, unwrapping common envelopes."""
    if isinstance(payload, SupervisorDirective):
        return payload

    if hasattr(payload, "model_dump") and not isinstance(payload, (str, bytes, dict)):
        try:
            payload = payload.model_dump()
        except Exception:
            pass

    if isinstance(payload, str):
        payload = json.loads(payload)
        # Some providers/models return a JSON string whose contents are another
        # JSON object. Decode that one extra layer as well.
        if isinstance(payload, str):
            payload = json.loads(payload)

    if isinstance(payload, dict) and "action" not in payload:
        for key in ("directive", "response", "output", "result"):
            nested = payload.get(key)
            if isinstance(nested, dict) and "action" in nested:
                payload = nested
                break

    return SupervisorDirective.model_validate(payload)


def parse_supervisor_json(text: Any) -> SupervisorDirective:
    """Parse the Supervisor response robustly without accepting arbitrary code.

    Handles a plain JSON object, Markdown fences, provider envelopes, and JSON
    followed by explanatory text. Pydantic then validates/normalizes the fields.
    """
    if not isinstance(text, str):
        try:
            return _validate_supervisor_payload(text)
        except Exception:
            text = response_to_text(text)

    raw = str(text or "").strip()
    if not raw:
        raise ValueError("Supervisor returned an empty response.")

    errors = []

    def _try(candidate: Any):
        try:
            return _validate_supervisor_payload(candidate)
        except Exception as exc:
            errors.append(str(exc))
            return None

    # Fast path: the whole response is valid JSON.
    parsed = _try(raw)
    if parsed is not None:
        return parsed

    # Markdown fenced JSON (also accept a generic code fence).
    for fence in re.finditer(r"```(?:json)?\s*([\s\S]*?)\s*```", raw, re.IGNORECASE):
        parsed = _try(fence.group(1).strip())
        if parsed is not None:
            return parsed

    # Decode a JSON object beginning at any opening brace. json.JSONDecoder
    # stops exactly at the end of the object, so trailing prose is harmless and
    # nested objects/escaped braces do not confuse a greedy regular expression.
    decoder = json.JSONDecoder()
    for idx, char in enumerate(raw):
        if char != "{":
            continue
        try:
            candidate, _ = decoder.raw_decode(raw[idx:])
        except json.JSONDecodeError:
            continue
        parsed = _try(candidate)
        if parsed is not None:
            return parsed

    detail = errors[-1] if errors else "No JSON object could be decoded."
    excerpt = raw[:800].replace("\x00", "")
    raise ValueError(
        "Failed to parse a valid JSON from the Supervisor's response. "
        f"Validation: {detail} Response excerpt: {excerpt!r}"
    )


def parse_supervisor_response(value: Any) -> SupervisorDirective:
    """Prefer LlamaIndex structured output, then fall back to assistant text."""
    structured = getattr(value, "structured_response", None)
    if structured:
        try:
            return _validate_supervisor_payload(structured)
        except Exception:
            pass
    return parse_supervisor_json(response_to_text(value))

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

        # Announce the Supervisor step BEFORE waiting for the muted agent call.
        # The runner treats StepEvent as a transition boundary: it finalizes the
        # previous agent block (if any), creates the next partial context and
        # switches the UI back to BUSY.  Emitting this only after ``await`` left
        # the UI with no loader for the whole Supervisor inference.
        await self._emit_step(
            ctx,
            agent_name=self._supervisor.name,
            index=ev.round_idx + 1,
            total=ev.max_rounds,
        )

        # Run Supervisor with stream muted to avoid leaking its internal JSON.
        sup_resp = await self._run_muted(ctx, self._supervisor.run(user_msg=sup_input, memory=self._supervisor_memory))
        sup_text = response_to_text(sup_resp)
        directive = parse_supervisor_response(sup_resp)

        # Final/ask_user/max_rounds -> emit text into the already announced
        # Supervisor block and stop.
        if directive.action == "final":
            await self._emit_text(ctx, f"\n\n{directive.final_answer or sup_text}", agent_name=self._supervisor.name)
            return OutputEvent(status="final", final_answer=directive.final_answer or sup_text, rounds_used=ev.round_idx)

        if directive.action == "ask_user" and ev.stop_on_ask_user:
            q = directive.question or "I need more information, please clarify."
            await self._emit_text(ctx, f"\n\n{q}", agent_name=self._supervisor.name)
            return OutputEvent(status="ask_user", final_answer=q, rounds_used=ev.round_idx)

        if ev.round_idx >= ev.max_rounds:
            await self._emit_text(ctx, "\n\nMax rounds exceeded.", agent_name=self._supervisor.name)
            return OutputEvent(status="max_rounds", final_answer="Exceeded maximum number of iterations.", rounds_used=ev.round_idx)

        # Emit exactly one Supervisor block with the instruction (no JSON leakage, no duplicates).
        instruction = (directive.instruction or "").strip() or "Perform a step that gets closest to fulfilling the DoD."
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
        # Announce the Worker step BEFORE starting the muted call.  This is the
        # important transition for the loading indicator: after the Supervisor
        # instruction is rendered, the UI must immediately enter BUSY and stay
        # there until the first Worker payload is emitted.
        await self._emit_step(
            ctx,
            agent_name=self._worker.name,
            index=ev.round_idx + 1,
            total=ev.max_rounds,
        )

        # Run Worker with stream muted; we will emit a single block with the final text.
        worker_input = f"Instruction from Supervisor:\n{ev.instruction}\n"
        worker_resp = await self._run_muted(ctx, self._worker.run(user_msg=worker_input, memory=self._worker_memory))
        worker_text = response_to_text(worker_resp)

        # Emit the response into the Worker block announced above.
        await self._emit_text(ctx, f"\n\n{worker_text}", agent_name=self._worker.name)

        return InputEvent(
            user_msg="",
            last_worker_output=worker_text,
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
    supervisor_tools=None,
    worker_tools=None,
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
    :param supervisor_tools: Optional local tools exposed to the Supervisor.
    :param worker_tools: Optional local tools exposed to the Worker.
    :param verbose: Verbose output flag.
    :param prompt_supervisor: Prompt for the Supervisor agent.
    :param prompt_worker: Prompt for the Worker agent.
    :param max_steps: Maximum number of steps for the workflow.
    :param worker_memory_session_id: Session ID for the Worker agent's memory.
    :return: SupervisorWorkflow instance
    """
    # Keep backwards compatibility for direct callers: historically the Worker
    # received ``tools`` and the Supervisor received none. New callers can pass
    # per-role tool lists explicitly.
    if supervisor_tools is None:
        supervisor_tools = []
    if worker_tools is None:
        worker_tools = tools or []

    supervisor = FunctionAgent(
        name="Supervisor",
        llm=llm_supervisor,
        system_prompt=prompt_supervisor,
        tools=supervisor_tools,
    )
    worker = FunctionAgent(
        name="Worker",
        llm=llm_worker,
        system_prompt=prompt_worker,
        tools=worker_tools,
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