#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.14 01:00:00                  #
# ================================================== #

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple
import inspect
from pydantic import ValidationError

# LlamaIndex workflow / agent
from llama_index.core.workflow import (
    Workflow,
    Context,
    StartEvent,
    StopEvent,
    Event,
    step,
)
from llama_index.core.llms.llm import LLM
from llama_index.core.tools.types import BaseTool

# v12/v13 agent workflow events + agent
from llama_index.core.agent.workflow import (
    FunctionAgent,
    ToolCall,
    ToolCallResult,
    AgentStream,
    AgentOutput,
)

# v12/v13 compatibility imports
try:
    # v13+
    from llama_index.core.memory import ChatMemoryBuffer
except Exception:  # pragma: no cover
    try:
        # v12
        from llama_index.memory import ChatMemoryBuffer
    except Exception:
        ChatMemoryBuffer = None  # type: ignore

try:
    from llama_index.core.objects.base import ObjectRetriever
except Exception:  # pragma: no cover
    ObjectRetriever = None  # type: ignore

try:
    from llama_index.core.settings import Settings
except Exception:  # pragma: no cover
    Settings = None  # type: ignore

# optional: OpenAI type for hints only
try:
    from llama_index.llms.openai import OpenAI  # noqa: F401
except Exception:
    pass

try:
    from .events import StepEvent  # local helper, same as in your Planner
except Exception:  # pragma: no cover
    StepEvent = None  # type: ignore


DEFAULT_MAX_FUNCTION_CALLS = 5
DEFAULT_SYSTEM_PROMPT = (
    "You are an OpenAI function-calling agent. "
    "Use tools when helpful, reason step-by-step, and produce concise, correct answers."
)


class QueryEvent(StartEvent):
    query: str


class FinalEvent(StopEvent):
    pass


def _safe_tool_name(t: BaseTool) -> str:
    """
    Get a safe tool name from the BaseTool instance.

    :param t: BaseTool instance
    :return: str: Tool name or class name if name is not available
    """
    try:
        # v13 BaseTool.metadata.name
        n = (getattr(t, "metadata", None) or {}).get("name") if isinstance(getattr(t, "metadata", None), dict) else None
        if not n and hasattr(t, "metadata") and hasattr(t.metadata, "name"):
            n = t.metadata.name  # pydantic model
        if not n:
            n = getattr(t, "name", None)
        if not n:
            n = t.__class__.__name__
        return str(n)
    except Exception:
        return t.__class__.__name__


def _list_tool_names(tools: Sequence[BaseTool]) -> List[str]:
    """
    Get a list of safe tool names from a sequence of BaseTool instances.

    :param tools: Sequence of BaseTool instances
    :return: List[str]: List of tool names
    """
    return [_safe_tool_name(t) for t in tools]


class OpenAIWorkflowAgent(Workflow):
    """
    Workflow-based replacement for the legacy OpenAIAgent (v12) using FunctionAgent (v12/v13).

    - memory: tries to set FunctionAgent.memory; falls back to injecting memory text into system prompt.
    - tools: accepts static list or dynamic tool_retriever (query-aware).
    - default_tool_choice: 'auto' | 'none' | '<tool_name>' -> filters visible tools for this run.
    - max_function_calls: mapped to FunctionAgent.max_steps.
    - streaming: forwards AgentStream/ToolCall/ToolCallResult/AgentOutput; emits StepEvent when available.
    """
    def __init__(
        self,
        tools: List[BaseTool],
        llm: LLM,
        memory: Optional[Any] = None,
        system_prompt: Optional[str] = None,
        prefix_messages: Optional[Sequence[Any]] = None,
        verbose: bool = False,
        max_function_calls: int = DEFAULT_MAX_FUNCTION_CALLS,
        default_tool_choice: str = "auto",
        tool_retriever: Optional[Any] = None,
        memory_char_limit: int = 8000,
        on_stop: Optional[Callable[[], bool]] = None,
    ):
        """
        Initialize the OpenAIWorkflowAgent.

        :param tools: List of BaseTool instances to use in the agent.
        :param llm: LLM instance to use for the agent.
        :param memory: Optional memory object to use for the agent. If provided, it will be set on FunctionAgent.memory.
        :param system_prompt: System prompt to use for the agent. If not provided, a default will be used.
        :param prefix_messages: List of messages to prepend to the system prompt for context.
        :param verbose: Verbosity flag for the agent.
        :param max_function_calls: Maximum number of function calls allowed in the agent run. This maps to FunctionAgent.max_steps.
        :param default_tool_choice: Default tool choice for the agent run. Can be 'auto', 'none', or a specific tool name.
        :param tool_retriever: Optional tool retriever to dynamically select tools based on the query.
        :param memory_char_limit: Optional character limit for the memory text representation. If set, will truncate memory text to this limit.
        :param on_stop: Optional callback function that returns a boolean indicating whether the agent should stop running.
        """
        super().__init__(timeout=None, verbose=verbose)
        self._llm = llm
        self._base_system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        self._prefix_messages = list(prefix_messages or [])
        self._tools = tools or []
        self._tool_retriever = tool_retriever
        self._memory = memory
        self._memory_char_limit = memory_char_limit
        self._default_tool_choice = (default_tool_choice or "auto").strip().lower()
        self._max_steps = int(max_function_calls or DEFAULT_MAX_FUNCTION_CALLS)
        self._on_stop = on_stop
        self.verbose = verbose

        # construct FunctionAgent once, will override tools/system_prompt/memory per run
        self._agent = FunctionAgent(
            name="OpenAIWorkflowAgent",
            description="Workflow-based OpenAI function-calling agent.",
            tools=self._tools,
            llm=self._llm,
            system_prompt=self._base_system_prompt,
            max_steps=self._max_steps,
        )

        # try attach memory now (can be overridden in run())
        if self._memory is not None:
            self._set_agent_memory(self._memory)

    def run(
        self,
        query: str,
        ctx: Optional[Context] = None,
        memory: Optional[Any] = None,
        verbose: Optional[bool] = None,
        **kwargs: Any,
    ):
        """
        Start the workflow answering a single user query.

        :param query: user message
        :param ctx: workflow context
        :param memory: optional memory object to use for this run
        :param verbose: override verbosity
        :return: Workflow run handler (stream_events() supported)
        """
        if verbose is not None:
            self.verbose = bool(verbose)
        if memory is not None:
            self._memory = memory
        # system handles rest via steps
        return super().run(ctx=ctx, query=query)

    # ---------- steps ----------

    @step
    async def answer(self, ctx: Context, ev: QueryEvent) -> FinalEvent:
        """
        Single-step: select tools -> prepare prompt/memory -> run FunctionAgent with streaming.

        :param ctx: Context for the workflow
        :param ev: QueryEvent containing the user query
        :return: FinalEvent with the last answer from the agent
        """
        self._emit_step_event(ctx, name="run", meta={"query": ev.query})

        # prepare memory + prompt
        self._set_agent_memory(self._memory)
        effective_system_prompt = self._compose_system_prompt(self._base_system_prompt, self._prefix_messages, self._memory)

        # select tools for this query
        tools_for_run, selection_reason = await self._select_tools_for_query(ev.query)

        # apply default_tool_choice filter
        tools_for_run = self._apply_default_tool_choice_filter(tools_for_run)

        # update agent config for this run
        try:
            self._agent.system_prompt = effective_system_prompt  # type: ignore[attr-defined]
        except Exception:
            pass
        try:
            self._agent.tools = tools_for_run  # type: ignore[attr-defined]
        except Exception:
            pass

        # log tool selection
        self._emit_step_event(
            ctx,
            name="tools_selected",
            meta={
                "available": _list_tool_names(self._tools),
                "selected": _list_tool_names(tools_for_run),
                "reason": selection_reason,
                "default_tool_choice": self._default_tool_choice,
                "max_steps": self._max_steps,
            },
        )

        # run agent and stream
        last_answer = await self._run_agent_once(ctx, ev.query)
        return FinalEvent(result=last_answer or "")

    # ---------- internals ----------

    def _stopped(self) -> bool:
        """
        Check if the agent should stop running based on the provided callback.

        :return: bool: True if the agent should stop, False otherwise.
        """
        if self._on_stop:
            try:
                return bool(self._on_stop())
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
        Emit a step event to the context stream.

        :param ctx: Context for the workflow
        :param name: Name of the step event
        :param index: Index of the step (optional)
        :param total: Total number of steps (optional)
        :param meta: Optional metadata dictionary for the step event
        """
        try:
            if StepEvent is not None:
                ctx.write_event_to_stream(StepEvent(name=name, index=index, total=total, meta=meta or {}))
                return
        except Exception:
            pass

        # Fallback: embed in AgentStream.raw for older AgentStream validators
        try:
            ctx.write_event_to_stream(
                AgentStream(
                    delta="",
                    response="",
                    current_agent_name="OpenAIWorkflowAgent",
                    tool_calls=[],
                    raw={"StepEvent": {"name": name, "index": index, "total": total, "meta": meta or {}}},
                )
            )
        except Exception:
            pass

    def _set_agent_memory(self, memory: Optional[Any]) -> None:
        """
        Set the memory for the FunctionAgent instance.

        :param memory: Optional memory object to set on the agent.
        """
        if memory is None:
            return
        try:
            # Prefer native memory on the FunctionAgent if present
            if hasattr(self._agent, "memory"):
                self._agent.memory = memory  # type: ignore[attr-defined]
        except Exception:
            pass

    def _memory_to_text(self, memory: Any) -> str:
        """
        Convert memory to a text representation, handling various types and structures.

        :param memory: Memory object or content to convert
        :return: str: Text representation of the memory
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

    def _prefix_to_text(self, prefix_messages: Sequence[Any]) -> str:
        """
        Convert a sequence of prefix messages to a formatted text representation.

        :param prefix_messages: Sequence of messages to convert, can be strings or objects with 'role' and 'content' attributes.
        :return: str: Formatted text representation of the prefix messages.
        """
        if not prefix_messages:
            return ""
        parts: List[str] = []
        for m in prefix_messages:
            if isinstance(m, str):
                parts.append(m.strip())
                continue

            # chat-like
            role = getattr(m, "role", None) or getattr(m, "sender", "system")
            content = getattr(m, "content", None) or getattr(m, "text", "")
            if not content and isinstance(m, dict):
                content = m.get("content", m.get("text", ""))
            if content:
                parts.append(f"{role}: {content}")
        return "\n".join([p for p in parts if p])

    def _compose_system_prompt(
        self,
        base: str,
        prefix_messages: Sequence[Any],
        memory: Optional[Any],
    ) -> str:
        """
        Compose the system prompt for the FunctionAgent, including base prompt,

        :param base: Base system prompt text.
        :param prefix_messages: Sequence of messages to prepend to the system prompt.
        :param memory: Optional memory object to include in the system prompt.
        :return: str: Composed system prompt text.
        """
        out = [base.strip()]
        prefix_text = self._prefix_to_text(prefix_messages)
        if prefix_text:
            out += ["", "Additional preface:", prefix_text]
        mem_text = self._memory_to_text(memory)
        if mem_text:
            out += ["", "Relevant past memory/context:", mem_text]
        return "\n".join(out).strip()

    async def _select_tools_for_query(self, query: str) -> Tuple[List[BaseTool], str]:
        """
        Select tools for the given query, either from static tools or dynamically retrieved tools.

        :param query: User query to select tools for
        :return: Tuple containing the list of selected tools and the reason for selection.
        """
        # default: use provided static tools
        selected = list(self._tools)
        reason = "static tools"

        if not self._tool_retriever:
            return selected, reason

        retriever = self._tool_retriever
        candidates: Optional[Iterable[Any]] = None

        # try a range of method names for compatibility
        for name in ("aretrieve", "aget_retrieved_objects", "retrieve", "get_retrieved_objects"):
            fn = getattr(retriever, name, None)
            if not fn:
                continue
            try:
                if inspect.iscoroutinefunction(fn):
                    candidates = await fn(query)  # type: ignore[misc]
                else:
                    candidates = fn(query)  # type: ignore[misc]
                break
            except Exception:
                candidates = None

        if candidates is None:
            return selected, "retriever failed; using static tools"

        tools: List[BaseTool] = []
        for item in candidates:
            if isinstance(item, BaseTool):
                tools.append(item)
                continue
            # common wrappers
            for attr in ("obj", "object", "tool"):
                cand = getattr(item, attr, None)
                if isinstance(cand, BaseTool):
                    tools.append(cand)
                    break

        if tools:
            selected = tools
            reason = "retrieved tools"
        else:
            reason = "retriever returned no tools; using static tools"

        return selected, reason

    def _apply_default_tool_choice_filter(self, tools: List[BaseTool]) -> List[BaseTool]:
        """
        Apply the default tool choice filter to the list of tools.

        :param tools: List of BaseTool instances to filter.
        :return: List[BaseTool]: Filtered list of tools based on the default tool choice.
        """
        choice = (self._default_tool_choice or "auto").strip().lower()
        if choice in ("auto", "", "default"):
            return tools
        if choice in ("none", "no", "off"):
            return []

        # filter by name
        wanted = choice
        filtered: List[BaseTool] = []
        for t in tools:
            name = _safe_tool_name(t).strip().lower()
            if name == wanted:
                filtered = [t]
                break
        return filtered or tools  # if not found, keep original

    async def _emit_text(
            self,
            ctx: Context,
            text: str,
            agent_name: str = "OpenAIWorkflowAgent"
    ):
        """
        Emit text to the context stream, handling validation errors gracefully.

        :param ctx: Context for the workflow
        :param text: Text to emit to the stream
        :param agent_name: Name of the agent to set in the event (default: "OpenAIWorkflowAgent")
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

    async def _run_agent_once(self, ctx: Context, prompt: str) -> str:
        """
        Run FunctionAgent for a single user message, streaming events.

        :param ctx: Context for the workflow
        :param prompt: User message to process
        :return: Last answer from the agent (text response)
        """
        sig = inspect.signature(self._agent.run)
        kwargs: Dict[str, Any] = {}
        if "user_msg" in sig.parameters:
            kwargs["user_msg"] = prompt
        elif "query" in sig.parameters:
            kwargs["query"] = prompt
        if "max_steps" in sig.parameters:
            kwargs["max_steps"] = self._max_steps

        handler = self._agent.run(**kwargs)
        last_answer = ""
        has_stream = False

        async def _stream():
            nonlocal last_answer, has_stream

            async for e in handler.stream_events():
                if isinstance(e, StopEvent):
                    continue

                # external stop callback
                if self._stopped():
                    try:
                        ctx.write_event_to_stream(StopEvent())
                    except Exception:
                        pass
                    try:
                        await handler.cancel_run()
                    except Exception:
                        pass
                    return last_answer

                if isinstance(e, AgentStream):
                    if getattr(e, "delta", None):
                        has_stream = True
                    if not getattr(e, "current_agent_name", None):
                        try:
                            e.current_agent_name = "OpenAIWorkflowAgent"
                        except Exception:
                            pass
                    ctx.write_event_to_stream(e)
                    continue

                if isinstance(e, AgentOutput):
                    resp = getattr(e, "response", None)
                    content = self._to_text(resp).strip()
                    last_answer = content
                    if not has_stream and content:
                        ctx.write_event_to_stream(
                            AgentStream(
                                delta=content,
                                response=content,
                                current_agent_name="OpenAIWorkflowAgent",
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

            return last_answer

        try:
            return await _stream()
        except Exception as ex:
            await self._emit_text(ctx, f"\n`Agent run failed: {ex}`")
            return last_answer

    def _to_text(self, resp: Any) -> str:
        """
        Convert response to text, handling various types and structures.

        :param resp: Response object or content to convert
        :return: str: Text representation of the response
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