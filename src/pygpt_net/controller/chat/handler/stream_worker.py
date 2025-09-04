#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.04 00:00:00                  #
# ================================================== #

import base64
import io
import json
from dataclasses import dataclass, field
from typing import Optional, Literal, Any
from enum import Enum

from PySide6.QtCore import QObject, Signal, Slot, QRunnable

from pygpt_net.core.events import RenderEvent
from pygpt_net.core.text.utils import has_unclosed_code_tag
from pygpt_net.item.ctx import CtxItem

# OpenAI Responses Events
EventType = Literal[
    "response.completed",
    "response.output_text.delta",
    "response.output_item.added",
    "response.function_call_arguments.delta",
    "response.function_call_arguments.done",
    "response.output_text.annotation.added",
    "response.reasoning_summary_text.delta",
    "response.output_item.done",
    "response.code_interpreter_call_code.delta",
    "response.code_interpreter_call_code.done",
    "response.image_generation_call.partial_image",
    "response.created",
    "response.done",
    "response.failed",
    "error",
]


class ChunkType(str, Enum):
    """
    Enum for chunk type classification.
    """
    API_CHAT = "api_chat"  # OpenAI Chat Completions / or compatible
    API_CHAT_RESPONSES = "api_chat_responses"  # OpenAI Responses
    API_COMPLETION = "api_completion"  # OpenAI Completions
    LANGCHAIN_CHAT = "langchain_chat"  # LangChain chat (deprecated)
    LLAMA_CHAT = "llama_chat"  # LlamaIndex chat
    GOOGLE = "google"  # Google SDK
    ANTHROPIC = "anthropic"  # Anthropic SDK
    XAI_SDK = "xai_sdk"  # xAI SDK
    RAW = "raw"  # Raw string fallback


class WorkerSignals(QObject):
    """
    Defines the signals available from a running worker thread.
    - `finished`: No data
    - `errorOccurred`: Exception
    - `eventReady`: RenderEvent
    """
    end = Signal(object)
    errorOccurred = Signal(Exception)
    eventReady = Signal(object)


@dataclass(slots=True)
class WorkerState:
    """Holds mutable state for the streaming loop."""
    out: Optional[io.StringIO] = None
    output_tokens: int = 0
    begin: bool = True
    error: Optional[Exception] = None
    fn_args_buffers: dict[str, io.StringIO] = field(default_factory=dict)
    citations: Optional[list] = field(default_factory=list)
    image_paths: list[str] = field(default_factory=list)
    files: list[dict] = field(default_factory=list)
    img_path: Optional[str] = None
    is_image: bool = False
    has_google_inline_image: bool = False
    is_code: bool = False
    force_func_call: bool = False
    stopped: bool = False
    chunk_type: ChunkType = ChunkType.RAW
    generator: Any = None
    usage_vendor: Optional[str] = None
    usage_payload: dict = field(default_factory=dict)
    google_stream_ref: Any = None
    tool_calls: list[dict] = field(default_factory=list)

    # --- XAI SDK ---
    xai_last_response: Any = None  # holds final response from xai_sdk.chat.stream()


class StreamWorker(QRunnable):
    __slots__ = ("signals", "ctx", "window", "stream")

    def __init__(self, ctx: CtxItem, window, parent=None):
        super().__init__()
        self.signals = WorkerSignals()
        self.ctx = ctx
        self.window = window
        self.stream = None

    @Slot()
    def run(self):
        ctx = self.ctx
        win = self.window
        core = win.core
        ctrl = win.controller

        emit_event = self.signals.eventReady.emit
        emit_error = self.signals.errorOccurred.emit
        emit_end = self.signals.end.emit

        state = WorkerState()
        state.generator = self.stream
        state.img_path = core.image.gen_unique_path(ctx)

        base_data = {"meta": ctx.meta, "ctx": ctx}
        emit_event(RenderEvent(RenderEvent.STREAM_BEGIN, base_data))

        try:
            if state.generator is not None:
                # print(state.generator)  # TODO: detect by obj type?
                for chunk in state.generator:
                    # cooperative stop
                    if self._should_stop(ctrl, state, ctx):
                        break

                    # if error flagged, stop early
                    if state.error is not None:
                        ctx.msg_id = None
                        state.stopped = True
                        break

                    etype: Optional[EventType] = None

                    # detect chunk type
                    if ctx.use_responses_api:
                        if hasattr(chunk, 'type'):
                            etype = chunk.type  # type: ignore[assignment]
                            state.chunk_type = ChunkType.API_CHAT_RESPONSES
                        else:
                            continue
                    else:
                        state.chunk_type = self._detect_chunk_type(chunk)

                    # process chunk according to type
                    response = self._process_chunk(ctx, core, state, chunk, etype)

                    # emit response delta if present
                    if response is not None and response != "" and not state.stopped:
                        self._append_response(ctx, state, response, emit_event)

                    # free per-iteration ref
                    chunk = None

                # after loop: handle tool-calls and images assembly
                self._handle_after_loop(ctx, core, state)

        except Exception as e:
            state.error = e

        finally:
            self._finalize(ctx, core, state, emit_end, emit_error)

    # ------------ Orchestration helpers ------------

    def _should_stop(
            self,
            ctrl,
            state: WorkerState,
            ctx: CtxItem
    ) -> bool:
        """
        Checks external stop signal and attempts to stop the generator gracefully.
        """
        if not ctrl.kernel.stopped():
            return False

        gen = state.generator
        if gen is not None:
            # Try common stop methods without raising
            for meth in ("close", "cancel", "stop"):
                if hasattr(gen, meth):
                    try:
                        getattr(gen, meth)()
                    except Exception:
                        pass

        ctx.msg_id = None
        state.stopped = True
        return True

    def _detect_chunk_type(self, chunk) -> ChunkType:
        """
        Detects chunk type for various providers/SDKs.
        Order matters: detect vendor-specific types before generic fallbacks.
        """
        # OpenAI SDK / OpenAI-compatible SSE
        choices = getattr(chunk, 'choices', None)
        if choices:
            choice0 = choices[0] if len(choices) > 0 else None
            if choice0 is not None and hasattr(choice0, 'delta') and choice0.delta is not None:
                return ChunkType.API_CHAT
            if choice0 is not None and hasattr(choice0, 'text') and choice0.text is not None:
                return ChunkType.API_COMPLETION

        # xAI SDK: chat.stream() yields (response, chunk) tuples
        if isinstance(chunk, (tuple, list)) and len(chunk) == 2:
            _resp, _ch = chunk[0], chunk[1]
            if hasattr(_ch, "content") or isinstance(_ch, str):
                return ChunkType.XAI_SDK

        # Anthropic: detect both SSE events and raw delta objects early
        t = getattr(chunk, "type", None)
        if isinstance(t, str):
            anthropic_events = {
                "message_start", "content_block_start", "content_block_delta",
                "content_block_stop", "message_delta", "message_stop",
                "ping", "error",                      # control / error
                "text_delta", "input_json_delta",     # content deltas
                "thinking_delta", "signature_delta",  # thinking deltas
            }
            if t in anthropic_events or t.startswith("message_") or t.startswith("content_block_"):
                return ChunkType.ANTHROPIC

        # Google python-genai
        if hasattr(chunk, "candidates"):
            return ChunkType.GOOGLE

        # LangChain chat-like objects
        if hasattr(chunk, 'content') and getattr(chunk, 'content') is not None:
            return ChunkType.LANGCHAIN_CHAT

        # LlamaIndex (generic delta fallback) - exclude Anthropic/Google shapes
        if hasattr(chunk, 'delta') and getattr(chunk, 'delta') is not None:
            # guard: do not misclassify Anthropic or Google objects
            if not hasattr(chunk, "type") and not hasattr(chunk, "candidates"):
                return ChunkType.LLAMA_CHAT

        return ChunkType.RAW

    def _append_response(
            self,
            ctx: CtxItem,
            state: WorkerState,
            response: str,
            emit_event
    ):
        """
        Appends response delta and emits STREAM_APPEND event.
        """
        if state.begin and response == "":
            return
        if state.out is None:
            state.out = io.StringIO()
        state.out.write(response)
        state.output_tokens += 1
        emit_event(
            RenderEvent(
                RenderEvent.STREAM_APPEND,
                {
                    "meta": ctx.meta,
                    "ctx": ctx,
                    "chunk": response,
                    "begin": state.begin,
                },
            )
        )
        state.begin = False

    def _handle_after_loop(
            self,
            ctx: CtxItem,
            core,
            state: WorkerState
    ):
        """
        Post-loop handling for tool calls and images assembly.
        """
        if state.tool_calls:
            ctx.force_call = state.force_func_call
            core.debug.info("[chat] Tool calls found, unpacking...")
            # Ensure function.arguments is JSON string
            for tc in state.tool_calls:
                fn = tc.get("function") or {}
                if isinstance(fn.get("arguments"), dict):
                    fn["arguments"] = json.dumps(fn["arguments"], ensure_ascii=False)
            core.command.unpack_tool_calls_chunks(ctx, state.tool_calls)

        # OpenAI partial image assembly
        if state.is_image and state.img_path:
            core.debug.info("[chat] OpenAI partial image assembled")
            ctx.images = [state.img_path]

        # Google inline images
        if state.image_paths:
            core.debug.info("[chat] Google inline images found")
            if not isinstance(ctx.images, list) or not ctx.images:
                ctx.images = list(state.image_paths)
            else:
                seen = set(ctx.images)
                for p in state.image_paths:
                    if p not in seen:
                        ctx.images.append(p)
                        seen.add(p)

        # xAI SDK: extract tool calls from final response if not already present
        if (not state.tool_calls) and (state.xai_last_response is not None):
            try:
                calls = self._xai_extract_tool_calls(state.xai_last_response)
                if calls:
                    state.tool_calls = calls
                    state.force_func_call = True
            except Exception:
                pass

        # xAI SDK: collect citations (final response) -> ctx.urls
        if state.xai_last_response is not None:
            try:
                cites = self._xai_extract_citations(state.xai_last_response) or []
                if cites:
                    if ctx.urls is None:
                        ctx.urls = []
                    for u in cites:
                        if u not in ctx.urls:
                            ctx.urls.append(u)
            except Exception:
                pass

    def _finalize(
            self,
            ctx: CtxItem,
            core,
            state: WorkerState,
            emit_end,
            emit_error
    ):
        """
        Finalize stream: build output, usage, tokens, files, errors, cleanup.
        """
        output = state.out.getvalue() if state.out is not None else ""
        if state.out is not None:
            try:
                state.out.close()
            except Exception:
                pass
            state.out = None

        if has_unclosed_code_tag(output):
            output += "\n```"

        # Resolve Google usage if present
        if ((state.usage_vendor is None or state.usage_vendor == "google")
                and not state.usage_payload and state.generator is not None):
            try:
                if hasattr(state.generator, "resolve"):
                    state.generator.resolve()
                    um = getattr(state.generator, "usage_metadata", None)
                    if um:
                        self._capture_google_usage(state, um)
            except Exception:
                pass

        # xAI SDK: usage from final response if still missing
        if (not state.usage_payload) and (state.xai_last_response is not None):
            try:
                up = self._xai_extract_usage(state.xai_last_response)
                if up:
                    state.usage_payload = up
                    state.usage_vendor = "xai"
            except Exception:
                pass

        # Close generator if possible
        gen = state.generator
        if gen and hasattr(gen, 'close'):
            try:
                gen.close()
            except Exception:
                pass

        self.stream = None
        ctx.output = output
        output = None  # free ref

        # Tokens usage
        if state.usage_payload:
            in_tok_final = state.usage_payload.get("in")
            out_tok_final = state.usage_payload.get("out")

            if in_tok_final is None:
                in_tok_final = ctx.input_tokens if ctx.input_tokens is not None else 0
            if out_tok_final is None:
                out_tok_final = state.output_tokens

            ctx.set_tokens(in_tok_final, out_tok_final)

            # Attach usage details in ctx.extra for debugging
            try:
                if not isinstance(ctx.extra, dict):
                    ctx.extra = {}
                ctx.extra["usage"] = {
                    "vendor": state.usage_vendor,
                    "input_tokens": in_tok_final,
                    "output_tokens": out_tok_final,
                    "reasoning_tokens": state.usage_payload.get("reasoning", 0),
                    "total_reported": state.usage_payload.get("total"),
                }
            except Exception:
                pass
        else:
            ctx.set_tokens(ctx.input_tokens if ctx.input_tokens is not None else 0, state.output_tokens)

        core.ctx.update_item(ctx)

        # OpenAI only: download container files if present
        if state.files and not state.stopped:
            core.debug.info("[chat] Container files found, downloading...")
            try:
                core.api.openai.container.download_files(ctx, state.files)
            except Exception as e:
                core.debug.error(f"[chat] Error downloading container files: {e}")

        # Emit error and end
        if state.error:
            emit_error(state.error)
        emit_end(ctx)

        # Cleanup local buffers
        for _buf in state.fn_args_buffers.values():
            try:
                _buf.close()
            except Exception:
                pass
        state.fn_args_buffers.clear()
        state.files.clear()
        state.tool_calls.clear()
        if state.citations is not None and state.citations is not ctx.urls:
            state.citations.clear()
        state.citations = None

        self.cleanup()

    # ------------ Chunk processors ------------

    def _process_chunk(
            self,
            ctx: CtxItem,
            core,
            state: WorkerState,
            chunk,
            etype: Optional[EventType]
    ) -> Optional[str]:
        """
        Dispatches processing to concrete provider-specific processing.
        """
        t = state.chunk_type
        if t == ChunkType.API_CHAT:
            return self._process_api_chat(ctx, state, chunk)
        if t == ChunkType.API_CHAT_RESPONSES:
            return self._process_api_chat_responses(ctx, core, state, chunk, etype)
        if t == ChunkType.API_COMPLETION:
            return self._process_api_completion(chunk)
        if t == ChunkType.LANGCHAIN_CHAT:
            return self._process_langchain_chat(chunk)
        if t == ChunkType.LLAMA_CHAT:
            return self._process_llama_chat(state, chunk)
        if t == ChunkType.GOOGLE:
            return self._process_google_chunk(ctx, core, state, chunk)
        if t == ChunkType.ANTHROPIC:
            return self._process_anthropic_chunk(ctx, core, state, chunk)
        if t == ChunkType.XAI_SDK:
            return self._process_xai_sdk_chunk(ctx, core, state, chunk)
        return self._process_raw(chunk)

    def _process_api_chat(
            self,
            ctx: CtxItem,
            state: WorkerState,
            chunk
    ) -> Optional[str]:
        """
        OpenAI-compatible Chat Completions stream delta (robust to dict/object tool_calls).
        """
        response = None
        delta = chunk.choices[0].delta if getattr(chunk, "choices", None) else None

        # Capture citations (top-level) if present
        try:
            cits = getattr(chunk, "citations", None)
            if cits:
                state.citations = cits
                ctx.urls = cits
        except Exception:
            pass

        # Capture usage (top-level) if present
        try:
            u = getattr(chunk, "usage", None)
            if u:
                self._capture_openai_usage(state, u)
        except Exception:
            pass

        # Text delta
        if delta and getattr(delta, "content", None) is not None:
            response = delta.content

        # Tool calls (support OpenAI object or xAI dict)
        if delta and getattr(delta, "tool_calls", None):
            state.force_func_call = True
            for tool_chunk in delta.tool_calls:
                # Normalize fields
                if isinstance(tool_chunk, dict):
                    idx = tool_chunk.get("index")
                    id_val = tool_chunk.get("id")
                    fn = tool_chunk.get("function") or {}
                    name_part = fn.get("name")
                    args_part = fn.get("arguments")
                else:
                    idx = getattr(tool_chunk, "index", None)
                    id_val = getattr(tool_chunk, "id", None)
                    fn_obj = getattr(tool_chunk, "function", None)
                    name_part = getattr(fn_obj, "name", None) if fn_obj else None
                    args_part = getattr(fn_obj, "arguments", None) if fn_obj else None

                # Default index when missing
                if idx is None or not isinstance(idx, int):
                    idx = len(state.tool_calls)

                # Ensure list length
                while len(state.tool_calls) <= idx:
                    state.tool_calls.append({
                        "id": "",
                        "type": "function",
                        "function": {"name": "", "arguments": ""}
                    })
                tool_call = state.tool_calls[idx]

                # Append id fragment (if streamed)
                if id_val:
                    frag = str(id_val)
                    if not tool_call["id"]:
                        tool_call["id"] = frag
                    else:
                        if not tool_call["id"].endswith(frag):
                            tool_call["id"] += frag

                # Append name fragment
                if name_part:
                    frag = str(name_part)
                    if not tool_call["function"]["name"]:
                        tool_call["function"]["name"] = frag
                    else:
                        if not tool_call["function"]["name"].endswith(frag):
                            tool_call["function"]["name"] += frag

                # Append arguments fragment (string or JSON)
                if args_part is not None:
                    if isinstance(args_part, (dict, list)):
                        frag = json.dumps(args_part, ensure_ascii=False)
                    else:
                        frag = str(args_part)
                    tool_call["function"]["arguments"] += frag

        return response

    def _process_api_chat_responses(
            self,
            ctx: CtxItem,
            core,
            state: WorkerState,
            chunk,
            etype: Optional[EventType]
    ) -> Optional[str]:
        """
        OpenAI Responses API stream events.
        """
        response = None

        if etype == "response.completed":
            # usage on final response
            try:
                u = getattr(chunk.response, "usage", None)
                if u:
                    self._capture_openai_usage(state, u)
            except Exception:
                pass

            for item in chunk.response.output:
                if item.type == "mcp_list_tools":
                    core.api.openai.responses.mcp_tools = item.tools
                elif item.type == "mcp_call":
                    call = {
                        "id": item.id,
                        "type": "mcp_call",
                        "approval_request_id": item.approval_request_id,
                        "arguments": item.arguments,
                        "error": item.error,
                        "name": item.name,
                        "output": item.output,
                        "server_label": item.server_label,
                    }
                    state.tool_calls.append({
                        "id": item.id,
                        "call_id": "",
                        "type": "function",
                        "function": {"name": item.name, "arguments": item.arguments}
                    })
                    ctx.extra["mcp_call"] = call
                    core.ctx.update_item(ctx)
                elif item.type == "mcp_approval_request":
                    call = {
                        "id": item.id,
                        "type": "mcp_call",
                        "arguments": item.arguments,
                        "name": item.name,
                        "server_label": item.server_label,
                    }
                    ctx.extra["mcp_approval_request"] = call
                    core.ctx.update_item(ctx)

        elif etype == "response.output_text.delta":
            response = chunk.delta

        elif etype == "response.output_item.added" and chunk.item.type == "function_call":
            state.tool_calls.append({
                "id": chunk.item.id,
                "call_id": chunk.item.call_id,
                "type": "function",
                "function": {"name": chunk.item.name, "arguments": ""}
            })
            state.fn_args_buffers[chunk.item.id] = io.StringIO()

        elif etype == "response.function_call_arguments.delta":
            buf = state.fn_args_buffers.get(chunk.item_id)
            if buf is not None:
                buf.write(chunk.delta)

        elif etype == "response.function_call_arguments.done":
            buf = state.fn_args_buffers.pop(chunk.item_id, None)
            if buf is not None:
                try:
                    args_val = buf.getvalue()
                finally:
                    buf.close()
                for tc in state.tool_calls:
                    if tc["id"] == chunk.item_id:
                        tc["function"]["arguments"] = args_val
                        break

        elif etype == "response.output_text.annotation.added":
            ann = chunk.annotation
            if ann['type'] == "url_citation":
                if state.citations is None:
                    state.citations = []
                url_citation = ann['url']
                state.citations.append(url_citation)
                ctx.urls = state.citations
            elif ann['type'] == "container_file_citation":
                state.files.append({
                    "container_id": ann['container_id'],
                    "file_id": ann['file_id'],
                })

        elif etype == "response.reasoning_summary_text.delta":
            response = chunk.delta

        elif etype == "response.output_item.done":
            tool_calls, has_calls = core.api.openai.computer.handle_stream_chunk(ctx, chunk, state.tool_calls)
            state.tool_calls = tool_calls
            if has_calls:
                state.force_func_call = True

        elif etype == "response.code_interpreter_call_code.delta":
            if not state.is_code:
                response = "\n\n**Code interpreter**\n```python\n" + chunk.delta
                state.is_code = True
            else:
                response = chunk.delta

        elif etype == "response.code_interpreter_call_code.done":
            response = "\n\n```\n-----------\n"

        elif etype == "response.image_generation_call.partial_image":
            image_base64 = chunk.partial_image_b64
            image_bytes = base64.b64decode(image_base64)
            if state.img_path:
                with open(state.img_path, "wb") as f:
                    f.write(image_bytes)
            del image_bytes
            state.is_image = True

        elif etype == "response.created":
            ctx.msg_id = str(chunk.response.id)
            core.ctx.update_item(ctx)

        elif etype in {"response.done", "response.failed", "error"}:
            pass

        return response

    def _process_api_completion(self, chunk) -> Optional[str]:
        """
        OpenAI Completions stream text delta.
        """
        if getattr(chunk, "choices", None):
            choice0 = chunk.choices[0]
            if getattr(choice0, "text", None) is not None:
                return choice0.text
        return None

    def _process_langchain_chat(self, chunk) -> Optional[str]:
        """
        LangChain chat streaming delta.
        """
        if getattr(chunk, "content", None) is not None:
            return str(chunk.content)
        return None

    def _process_llama_chat(
            self,
            state: WorkerState,
            chunk
    ) -> Optional[str]:
        """
        Llama chat streaming delta with optional tool call extraction.
        """
        response = None
        if getattr(chunk, "delta", None) is not None:
            response = str(chunk.delta)

        tool_chunks = getattr(getattr(chunk, "message", None), "additional_kwargs", {}).get("tool_calls", [])
        if tool_chunks:
            for tool_chunk in tool_chunks:
                id_val = getattr(tool_chunk, "call_id", None) or getattr(tool_chunk, "id", None)
                name = getattr(tool_chunk, "name", None) or getattr(getattr(tool_chunk, "function", None), "name", None)
                args = getattr(tool_chunk, "arguments", None)
                if args is None:
                    f = getattr(tool_chunk, "function", None)
                    args = getattr(f, "arguments", None) if f else None
                if id_val:
                    if not args:
                        args = "{}"
                    tool_call = {
                        "id": id_val,
                        "type": "function",
                        "function": {"name": name, "arguments": args}
                    }
                    state.tool_calls.clear()
                    state.tool_calls.append(tool_call)

        return response

    def _process_google_chunk(
            self,
            ctx: CtxItem,
            core,
            state: WorkerState,
            chunk
    ) -> Optional[str]:
        """
        Google python-genai streaming chunk.
        """
        response_parts: list[str] = []

        if state.google_stream_ref is None:
            state.google_stream_ref = state.generator

        try:
            um = getattr(chunk, "usage_metadata", None)
            if um:
                self._capture_google_usage(state, um)
        except Exception:
            pass

        t = None
        try:
            t = getattr(chunk, "text", None)
            if t:
                response_parts.append(t)
        except Exception:
            pass

        fc_list = []
        try:
            fc_list = getattr(chunk, "function_calls", None) or []
        except Exception:
            fc_list = []

        new_calls = []

        def _to_plain_dict(obj):
            """Best-effort conversion of SDK objects to plain dict/list."""
            try:
                if hasattr(obj, "to_json_dict"):
                    return obj.to_json_dict()
                if hasattr(obj, "model_dump"):
                    return obj.model_dump()
                if hasattr(obj, "to_dict"):
                    return obj.to_dict()
            except Exception:
                pass
            if isinstance(obj, dict):
                return {k: _to_plain_dict(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [_to_plain_dict(x) for x in obj]
            return obj

        if fc_list:
            for fc in fc_list:
                name = getattr(fc, "name", "") or ""
                args_obj = getattr(fc, "args", {}) or {}
                args_dict = _to_plain_dict(args_obj) or {}
                new_calls.append({
                    "id": getattr(fc, "id", "") or "",
                    "type": "function",
                    "function": {
                        "name": name,
                        "arguments": json.dumps(args_dict, ensure_ascii=False),
                    }
                })
        else:
            try:
                cands = getattr(chunk, "candidates", None) or []
                for cand in cands:
                    content = getattr(cand, "content", None)
                    parts = getattr(content, "parts", None) or []
                    for p in parts:
                        fn = getattr(p, "function_call", None)
                        if not fn:
                            continue
                        name = getattr(fn, "name", "") or ""
                        args_obj = getattr(fn, "args", {}) or {}
                        args_dict = _to_plain_dict(args_obj) or {}
                        new_calls.append({
                            "id": getattr(fn, "id", "") or "",
                            "type": "function",
                            "function": {
                                "name": name,
                                "arguments": json.dumps(args_dict, ensure_ascii=False),
                            }
                        })
            except Exception:
                pass

        if new_calls:
            seen = {(tc["function"]["name"], tc["function"]["arguments"]) for tc in state.tool_calls}
            for tc in new_calls:
                key = (tc["function"]["name"], tc["function"]["arguments"])
                if key not in seen:
                    state.tool_calls.append(tc)
                    seen.add(key)

        try:
            cands = getattr(chunk, "candidates", None) or []
            for cand in cands:
                content = getattr(cand, "content", None)
                parts = getattr(content, "parts", None) or []

                for p in parts:
                    ex = getattr(p, "executable_code", None)
                    if ex:
                        lang = (getattr(ex, "language", None) or "python").strip() or "python"
                        code_txt = (
                            getattr(ex, "code", None) or
                            getattr(ex, "program", None) or
                            getattr(ex, "source", None) or
                            ""
                        )
                        if code_txt is None:
                            code_txt = ""
                        if not state.is_code:
                            response_parts.append(f"\n\n**Code interpreter**\n```{lang.lower()}\n{code_txt}")
                            state.is_code = True
                        else:
                            response_parts.append(str(code_txt))

                    cer = getattr(p, "code_execution_result", None)
                    if cer:
                        if state.is_code:
                            response_parts.append("\n\n```\n-----------\n")
                            state.is_code = False

                    blob = getattr(p, "inline_data", None)
                    if blob:
                        mime = (getattr(blob, "mime_type", "") or "").lower()
                        if mime.startswith("image/"):
                            data = getattr(blob, "data", None)
                            if data:
                                if isinstance(data, (bytes, bytearray)):
                                    img_bytes = bytes(data)
                                else:
                                    img_bytes = base64.b64decode(data)
                                save_path = core.image.gen_unique_path(ctx)
                                with open(save_path, "wb") as f:
                                    f.write(img_bytes)
                                if not isinstance(ctx.images, list):
                                    ctx.images = []
                                ctx.images.append(save_path)
                                state.image_paths.append(save_path)
                                state.has_google_inline_image = True

                    fdata = getattr(p, "file_data", None)
                    if fdata:
                        uri = getattr(fdata, "file_uri", None) or getattr(fdata, "uri", None)
                        mime = (getattr(fdata, "mime_type", "") or "").lower()
                        if uri and mime.startswith("image/") and (uri.startswith("http://") or uri.startswith("https://")):
                            if ctx.urls is None:
                                ctx.urls = []
                            ctx.urls.append(uri)

            self._collect_google_citations(ctx, state, chunk)

        except Exception:
            pass

        return "".join(response_parts) if response_parts else None

    def _process_anthropic_chunk(self, ctx: CtxItem, core, state: WorkerState, chunk) -> Optional[str]:
        """
        Anthropic streaming events handler.
        Supports both full event objects and top-level delta objects.
        """
        state.usage_vendor = "anthropic"
        etype = str(getattr(chunk, "type", "") or "")
        response: Optional[str] = None

        # --- Top-level delta objects (when SDK yields deltas directly) ---
        if etype == "text_delta":
            # Print plain text piece
            txt = getattr(chunk, "text", None)
            return str(txt) if txt is not None else None

        if etype == "thinking_delta":
            # Do not surface internal reasoning to the user; ignore silently
            return None

        if etype == "input_json_delta":
            # Accumulate partial JSON for the most recent tool call
            pj = getattr(chunk, "partial_json", "") or ""
            # Use a single rolling buffer when we don't get a content_block index
            buf = state.fn_args_buffers.get("__anthropic_last__")
            if buf is None:
                buf = io.StringIO()
                state.fn_args_buffers["__anthropic_last__"] = buf
            buf.write(pj)
            # Keep tool call arguments in sync if we have at least one call
            if state.tool_calls:
                state.tool_calls[-1]["function"]["arguments"] = buf.getvalue()
            return None

        if etype == "signature_delta":
            # Not user-visible; ignore.
            return None

        # --- Standard event flow ---
        if etype == "message_start":
            # Capture input tokens if present
            try:
                msg = getattr(chunk, "message", None)
                um = getattr(msg, "usage", None) if msg else None
                if um:
                    inp = self._as_int(getattr(um, "input_tokens", None))
                    if inp is not None:
                        state.usage_payload["in"] = inp
            except Exception:
                pass
            return None

        if etype == "content_block_start":
            # Tool call started -> prepare buffer keyed by content_block index
            try:
                cb = getattr(chunk, "content_block", None)
                if cb and getattr(cb, "type", "") == "tool_use":
                    idx = getattr(chunk, "index", 0) or 0
                    tid = getattr(cb, "id", "") or ""
                    name = getattr(cb, "name", "") or ""
                    state.tool_calls.append({
                        "id": tid,
                        "type": "function",
                        "function": {"name": name, "arguments": ""}
                    })
                    state.fn_args_buffers[str(idx)] = io.StringIO()
                    # Keep the rolling buffer in sync as a fallback for SDKs that yield raw deltas later
                    state.fn_args_buffers["__anthropic_last__"] = state.fn_args_buffers[str(idx)]
            except Exception:
                pass

            # Optional: collect URLs from custom search block types if present
            try:
                cb = getattr(chunk, "content_block", None)
                if cb and getattr(cb, "type", "") == "web_search_tool_result":
                    results = getattr(cb, "content", None) or []
                    for r in results:
                        url = r.get("url") if isinstance(r, dict) else None
                        if url:
                            if ctx.urls is None:
                                ctx.urls = []
                            if url not in ctx.urls:
                                ctx.urls.append(url)
            except Exception:
                pass

            return None

        if etype == "content_block_delta":
            try:
                delta = getattr(chunk, "delta", None)
                if not delta:
                    return None
                # Text fragment within content block
                if getattr(delta, "type", "") == "text_delta":
                    txt = getattr(delta, "text", None)
                    if txt is not None:
                        response = str(txt)
                # Tool input JSON fragment within content block
                elif getattr(delta, "type", "") == "input_json_delta":
                    idx = str(getattr(chunk, "index", 0) or 0)
                    buf = state.fn_args_buffers.get(idx)
                    pj = getattr(delta, "partial_json", "") or ""
                    if buf is None:
                        buf = io.StringIO()
                        state.fn_args_buffers[idx] = buf
                    buf.write(pj)
                    # Keep last-tool rolling buffer updated for consistency
                    state.fn_args_buffers["__anthropic_last__"] = buf
                    try:
                        if state.tool_calls:
                            tc = state.tool_calls[-1]
                            tc["function"]["arguments"] = buf.getvalue()
                    except Exception:
                        pass
            except Exception:
                pass
            return response

        if etype == "content_block_stop":
            # Finalize the buffer for this block; copy to last tool call
            try:
                idx = str(getattr(chunk, "index", 0) or 0)
                buf = state.fn_args_buffers.pop(idx, None)
                if buf is not None:
                    try:
                        args_val = buf.getvalue()
                    finally:
                        try:
                            buf.close()
                        except Exception:
                            pass
                    if state.tool_calls:
                        state.tool_calls[-1]["function"]["arguments"] = args_val
                # Clear rolling buffer if it pointed to this block
                if state.fn_args_buffers.get("__anthropic_last__") is buf:
                    state.fn_args_buffers.pop("__anthropic_last__", None)
            except Exception:
                pass
            return None

        if etype == "message_delta":
            # Capture output tokens and detect stop reason
            try:
                usage = getattr(chunk, "usage", None)
                if usage:
                    out_tok = self._as_int(getattr(usage, "output_tokens", None))
                    if out_tok is not None:
                        state.usage_payload["out"] = out_tok
                delta = getattr(chunk, "delta", None)
                stop_reason = getattr(delta, "stop_reason", None) if delta else None
                if stop_reason == "tool_use":
                    state.force_func_call = True
            except Exception:
                pass
            return None

        if etype == "message_stop":
            return None

        # Ignore ping/error at this level; errors are surfaced elsewhere
        return None

    def _process_xai_sdk_chunk(
            self,
            ctx: CtxItem,
            core,
            state: WorkerState,
            item
    ) -> Optional[str]:
        """
        xAI SDK native streaming chunk.
        """
        try:
            response, chunk = item
        except Exception:
            return None

        state.xai_last_response = response

        try:
            if hasattr(chunk, "content") and chunk.content is not None:
                return str(chunk.content)
            if isinstance(chunk, str):
                return chunk
        except Exception:
            pass
        return None

    def _process_raw(self, chunk) -> Optional[str]:
        """
        Raw chunk fallback.
        """
        if chunk is not None:
            return chunk if isinstance(chunk, str) else str(chunk)
        return None

    # ------------ Usage helpers ------------

    def _safe_get(self, obj, path: str) -> Any:
        """
        Dot-path getter for dicts and objects.
        """
        cur = obj
        for seg in path.split("."):
            if cur is None:
                return None
            if isinstance(cur, dict):
                cur = cur.get(seg)
            else:
                if seg.isdigit() and isinstance(cur, (list, tuple)):
                    idx = int(seg)
                    if 0 <= idx < len(cur):
                        cur = cur[idx]
                    else:
                        return None
                else:
                    cur = getattr(cur, seg, None)
        return cur

    def _as_int(self, val) -> Optional[int]:
        """
        Coerce to int if possible, else None.
        """
        if val is None:
            return None
        try:
            return int(val)
        except Exception:
            try:
                return int(float(val))
            except Exception:
                return None

    def _capture_openai_usage(self, state: WorkerState, u_obj):
        """
        Extract usage for OpenAI/xAI-compatible chunks.
        """
        if not u_obj:
            return
        state.usage_vendor = "openai"
        in_tok = self._as_int(self._safe_get(u_obj, "input_tokens")) or self._as_int(self._safe_get(u_obj, "prompt_tokens"))
        out_tok = self._as_int(self._safe_get(u_obj, "output_tokens")) or self._as_int(self._safe_get(u_obj, "completion_tokens"))
        total = self._as_int(self._safe_get(u_obj, "total_tokens"))
        reasoning = (
            self._as_int(self._safe_get(u_obj, "output_tokens_details.reasoning_tokens")) or
            self._as_int(self._safe_get(u_obj, "completion_tokens_details.reasoning_tokens")) or
            self._as_int(self._safe_get(u_obj, "reasoning_tokens")) or
            0
        )
        out_with_reason = (out_tok or 0) + (reasoning or 0)
        state.usage_payload = {"in": in_tok, "out": out_with_reason, "reasoning": reasoning or 0, "total": total}

    def _capture_google_usage(self, state: WorkerState, um_obj):
        """
        Extract usage for Google python-genai; prefer total - prompt to include reasoning.
        """
        if not um_obj:
            return
        state.usage_vendor = "google"
        prompt = (
            self._as_int(self._safe_get(um_obj, "prompt_token_count")) or
            self._as_int(self._safe_get(um_obj, "prompt_tokens")) or
            self._as_int(self._safe_get(um_obj, "input_tokens"))
        )
        total = (
            self._as_int(self._safe_get(um_obj, "total_token_count")) or
            self._as_int(self._safe_get(um_obj, "total_tokens"))
        )
        candidates = (
            self._as_int(self._safe_get(um_obj, "candidates_token_count")) or
            self._as_int(self._safe_get(um_obj, "output_tokens"))
        )
        reasoning = (
            self._as_int(self._safe_get(um_obj, "candidates_reasoning_token_count")) or
            self._as_int(self._safe_get(um_obj, "reasoning_tokens")) or 0
        )
        if total is not None and prompt is not None:
            out_total = max(0, total - prompt)
        else:
            out_total = candidates
        state.usage_payload = {"in": prompt, "out": out_total, "reasoning": reasoning or 0, "total": total}

    def _collect_google_citations(
            self,
            ctx: CtxItem,
            state: WorkerState,
            chunk: Any
    ):
        """
        Collect web citations (URLs) from Google GenAI stream.
        """
        try:
            cands = getattr(chunk, "candidates", None) or []
        except Exception:
            cands = []

        if not isinstance(state.citations, list):
            state.citations = []

        def _add_url(url: Optional[str]):
            if not url or not isinstance(url, str):
                return
            url = url.strip()
            if not (url.startswith("http://") or url.startswith("https://")):
                return
            if ctx.urls is None:
                ctx.urls = []
            if url not in state.citations:
                state.citations.append(url)
            if url not in ctx.urls:
                ctx.urls.append(url)

        for cand in cands:
            gm = self._safe_get(cand, "grounding_metadata") or self._safe_get(cand, "groundingMetadata")
            if gm:
                atts = self._safe_get(gm, "grounding_attributions") or self._safe_get(gm, "groundingAttributions") or []
                try:
                    for att in atts or []:
                        for path in (
                            "web.uri",
                            "web.url",
                            "source.web.uri",
                            "source.web.url",
                            "source.uri",
                            "source.url",
                            "uri",
                            "url",
                        ):
                            _add_url(self._safe_get(att, path))
                except Exception:
                    pass
                for path in (
                    "search_entry_point.uri",
                    "search_entry_point.url",
                    "searchEntryPoint.uri",
                    "searchEntryPoint.url",
                    "search_entry_point.rendered_content_uri",
                    "searchEntryPoint.rendered_content_uri",
                ):
                    _add_url(self._safe_get(gm, path))

            cm = self._safe_get(cand, "citation_metadata") or self._safe_get(cand, "citationMetadata")
            if cm:
                cit_arrays = (
                    self._safe_get(cm, "citation_sources") or
                    self._safe_get(cm, "citationSources") or
                    self._safe_get(cm, "citations") or []
                )
                try:
                    for cit in cit_arrays or []:
                        for path in ("uri", "url", "source.uri", "source.url", "web.uri", "web.url"):
                            _add_url(self._safe_get(cit, path))
                except Exception:
                    pass

            try:
                parts = self._safe_get(cand, "content.parts") or []
                for p in parts:
                    pcm = self._safe_get(p, "citation_metadata") or self._safe_get(p, "citationMetadata")
                    if pcm:
                        arr = (
                            self._safe_get(pcm, "citation_sources") or
                            self._safe_get(pcm, "citationSources") or
                            self._safe_get(pcm, "citations") or []
                        )
                        for cit in arr or []:
                            for path in ("uri", "url", "source.uri", "source.url", "web.uri", "web.url"):
                                _add_url(self._safe_get(cit, path))
                    gpa = self._safe_get(p, "grounding_attributions") or self._safe_get(p, "groundingAttributions") or []
                    for att in gpa or []:
                        for path in ("web.uri", "web.url", "source.web.uri", "source.web.url", "uri", "url"):
                            _add_url(self._safe_get(att, path))
            except Exception:
                pass

        if state.citations and (ctx.urls is None or not ctx.urls):
            ctx.urls = list(state.citations)

    def _xai_extract_tool_calls(self, response) -> list[dict]:
        """
        Extract tool calls from xAI SDK final response (proto).
        """
        out: list[dict] = []
        try:
            proto = getattr(response, "proto", None)
            if not proto:
                return out
            choices = getattr(proto, "choices", None) or []
            if not choices:
                return out
            msg = getattr(choices[0], "message", None)
            if not msg:
                return out
            tool_calls = getattr(msg, "tool_calls", None) or []
            for tc in tool_calls:
                try:
                    name = getattr(getattr(tc, "function", None), "name", "") or ""
                    args = getattr(getattr(tc, "function", None), "arguments", "") or "{}"
                    out.append({
                        "id": getattr(tc, "id", "") or "",
                        "type": "function",
                        "function": {"name": name, "arguments": args},
                    })
                except Exception:
                    continue
        except Exception:
            pass
        return out

    def _xai_extract_citations(self, response) -> list[str]:
        """
        Extract citations (URLs) from xAI final response if present.
        """
        urls: list[str] = []
        try:
            cites = getattr(response, "citations", None)
            if isinstance(cites, (list, tuple)):
                for u in cites:
                    if isinstance(u, str) and (u.startswith("http://") or u.startswith("https://")):
                        if u not in urls:
                            urls.append(u)
        except Exception:
            pass
        try:
            proto = getattr(response, "proto", None)
            if proto:
                proto_cites = getattr(proto, "citations", None) or []
                for u in proto_cites:
                    if isinstance(u, str) and (u.startswith("http://") or u.startswith("https://")):
                        if u not in urls:
                            urls.append(u)
        except Exception:
            pass
        return urls

    def _xai_extract_usage(self, response) -> dict:
        """
        Extract usage from xAI final response via proto.usage -> {'in','out','reasoning','total'}.
        """
        try:
            proto = getattr(response, "proto", None)
            usage = getattr(proto, "usage", None) if proto else None
            if not usage:
                return {}

            def as_int(v):
                try:
                    return int(v)
                except Exception:
                    try:
                        return int(float(v))
                    except Exception:
                        return 0

            p = as_int(getattr(usage, "prompt_tokens", 0) or 0)
            c = as_int(getattr(usage, "completion_tokens", 0) or 0)
            t = as_int(getattr(usage, "total_tokens", (p + c)) or (p + c))
            out_total = max(0, t - p) if t else c
            return {"in": p, "out": out_total, "reasoning": 0, "total": t}
        except Exception:
            return {}

    def cleanup(self):
        """Cleanup resources after worker execution."""
        sig = self.signals
        self.signals = None
        if sig is not None:
            try:
                sig.deleteLater()
            except RuntimeError:
                pass