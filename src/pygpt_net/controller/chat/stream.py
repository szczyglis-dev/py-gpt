#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.28 20:00:00                  #
# ================================================== #

import base64
import io
import json
from dataclasses import dataclass, field
from typing import Optional, Literal, Any

from PySide6.QtCore import QObject, Signal, Slot, QRunnable

from pygpt_net.core.bridge import BridgeContext
from pygpt_net.core.events import RenderEvent
from pygpt_net.core.types import MODE_ASSISTANT
from pygpt_net.core.text.utils import has_unclosed_code_tag
from pygpt_net.item.ctx import CtxItem

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
ChunkType = Literal[
    "api_chat",
    "api_chat_responses",
    "api_completion",
    "langchain_chat",
    "llama_chat",
    "google",
    "raw",
]


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


@dataclass
class WorkerState:
    """Holds mutable state for the streaming loop."""
    output_parts: list[str] = field(default_factory=list)
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
    chunk_type: ChunkType = "raw"
    generator: Any = None
    usage_vendor: Optional[str] = None
    usage_payload: dict = field(default_factory=dict)
    google_stream_ref: Any = None
    tool_calls: list[dict] = field(default_factory=list)


class StreamWorker(QRunnable):
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
                            state.chunk_type = "api_chat_responses"
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

    def _should_stop(self, ctrl, state: WorkerState, ctx: CtxItem) -> bool:
        """
        Checks external stop signal and attempts to stop the generator gracefully.

        :param ctrl: Controller with stop signal
        :param state: WorkerState
        :param ctx: CtxItem
        :return: True if stopped, False otherwise
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

        :param chunk: The chunk object from the stream
        :return: Detected ChunkType
        """
        if (hasattr(chunk, 'choices')
                and chunk.choices
                and hasattr(chunk.choices[0], 'delta')
                and chunk.choices[0].delta is not None):
            return "api_chat"
        if (hasattr(chunk, 'choices')
                and chunk.choices
                and hasattr(chunk.choices[0], 'text')
                and chunk.choices[0].text is not None):
            return "api_completion"
        if hasattr(chunk, 'content') and chunk.content is not None:
            return "langchain_chat"
        if hasattr(chunk, 'delta') and chunk.delta is not None:
            return "llama_chat"
        if hasattr(chunk, "candidates"):  # Google python-genai chunk
            return "google"
        return "raw"

    def _append_response(
            self,
            ctx: CtxItem,
            state: WorkerState,
            response: str,
            emit_event
    ):
        """
        Appends response delta and emits STREAM_APPEND event.

        Skips empty initial chunks if state.begin is True.

        :param ctx: CtxItem
        :param state: WorkerState
        :param response: Response delta string
        :param emit_event: Function to emit RenderEvent
        """
        if state.begin and response == "":
            return
        state.output_parts.append(response)
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

    def _handle_after_loop(self, ctx: CtxItem, core, state: WorkerState):
        """
        Post-loop handling for tool calls and images assembly.

        :param ctx: CtxItem
        :param core: Core instance
        :param state: WorkerState
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

    def _finalize(self, ctx: CtxItem, core, state: WorkerState, emit_end, emit_error):
        """
        Finalize stream: build output, usage, tokens, files, errors, cleanup.

        :param ctx: CtxItem
        :param core: Core instance
        :param state: WorkerState
        :param emit_end: Function to emit end signal
        """
        # Build final output
        output = "".join(state.output_parts)
        state.output_parts.clear()

        if has_unclosed_code_tag(output):
            output += "\n```"

        # Attempt to resolve Google usage from the stream object if missing
        if (state.usage_vendor is None or state.usage_vendor == "google") and not state.usage_payload and state.generator is not None:
            try:
                if hasattr(state.generator, "resolve"):
                    state.generator.resolve()
                    um = getattr(state.generator, "usage_metadata", None)
                    if um:
                        self._capture_google_usage(state, um)
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
            # Fallback when usage is not available
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

        # Worker cleanup (signals etc.)
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

        :param ctx: CtxItem
        :param core: Core instance
        :param state: WorkerState
        :param chunk: The chunk object from the stream
        :param etype: Optional event type for Responses API
        :return: Response delta string or None
        """
        t = state.chunk_type
        if t == "api_chat":
            return self._process_api_chat(ctx, state, chunk)
        if t == "api_chat_responses":
            return self._process_api_chat_responses(ctx, core, state, chunk, etype)
        if t == "api_completion":
            return self._process_api_completion(chunk)
        if t == "langchain_chat":
            return self._process_langchain_chat(chunk)
        if t == "llama_chat":
            return self._process_llama_chat(state, chunk)
        if t == "google":
            return self._process_google_chunk(ctx, core, state, chunk)
        # raw fallback
        return self._process_raw(chunk)

    def _process_api_chat(
            self,
            ctx: CtxItem,
            state: WorkerState,
            chunk
    ) -> Optional[str]:
        """
        OpenAI Chat Completions stream delta.

        Handles text deltas, citations, and streamed tool_calls.

        :param ctx: CtxItem
        :param state: WorkerState
        :param chunk: The chunk object from the stream
        :return: Response delta string or None
        """
        response = None
        state.citations = None  # as in original, reset to None for this type

        delta = chunk.choices[0].delta if getattr(chunk, "choices", None) else None
        if delta and getattr(delta, "content", None) is not None:
            if state.citations is None and hasattr(chunk, 'citations') and chunk.citations is not None:
                state.citations = chunk.citations
                ctx.urls = state.citations
            response = delta.content

        # Accumulate streamed tool_calls
        if delta and getattr(delta, "tool_calls", None):
            for tool_chunk in delta.tool_calls:
                if tool_chunk.index is None:
                    tool_chunk.index = 0
                if len(state.tool_calls) <= tool_chunk.index:
                    state.tool_calls.append(
                        {
                            "id": "",
                            "type": "function",
                            "function": {"name": "", "arguments": ""}
                        }
                    )
                tool_call = state.tool_calls[tool_chunk.index]
                if getattr(tool_chunk, "id", None):
                    tool_call["id"] += tool_chunk.id
                if getattr(getattr(tool_chunk, "function", None), "name", None):
                    tool_call["function"]["name"] += tool_chunk.function.name
                if getattr(getattr(tool_chunk, "function", None), "arguments", None):
                    tool_call["function"]["arguments"] += tool_chunk.function.arguments

        # Capture usage (if available on final chunk with include_usage=True)
        try:
            u = getattr(chunk, "usage", None)
            if u:
                self._capture_openai_usage(state, u)
        except Exception:
            pass

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
        OpenAI Responses API stream events

        Handles various event types including text deltas, tool calls, citations, images, and usage.

        :param ctx: CtxItem
        :param core: Core instance
        :param state: WorkerState
        :param chunk: The chunk object from the stream
        :param etype: EventType string
        :return: Response delta string or None
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
            # Delegate to computer handler which may add tool calls
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
        OpenAI Completions stream delta.

        :param chunk: The chunk object from the stream
        :return: Response delta string or None
        """
        if getattr(chunk, "choices", None):
            choice0 = chunk.choices[0]
            if getattr(choice0, "text", None) is not None:
                return choice0.text
        return None

    def _process_langchain_chat(self, chunk) -> Optional[str]:
        """
        LangChain chat streaming delta.

        :param chunk: The chunk object from the stream
        :return: Response delta string or None
        """
        if getattr(chunk, "content", None) is not None:
            return str(chunk.content)
        return None

    def _process_llama_chat(self, state: WorkerState, chunk) -> Optional[str]:
        """
        Llama chat streaming delta with optional tool call extraction.

        :param state: WorkerState
        :param chunk: The chunk object from the stream
        :return: Response delta string or None
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

    def _process_google_chunk(self, ctx: CtxItem, core, state: WorkerState, chunk) -> Optional[str]:
        """
        Google python-genai streaming chunk.

        Handles text, tool calls, inline images, code execution parts, citations, and usage.

        :param ctx: CtxItem
        :param core: Core instance
        :param state: WorkerState
        :param chunk: The chunk object from the stream
        :return: Response delta string or None
        """
        response_parts: list[str] = []

        # Keep a reference to stream object for resolve() later if needed
        if state.google_stream_ref is None:
            state.google_stream_ref = state.generator

        # Try to capture usage from this chunk (usage_metadata)
        try:
            um = getattr(chunk, "usage_metadata", None)
            if um:
                self._capture_google_usage(state, um)
        except Exception:
            pass

        # 1) Plain text delta (if present)
        t = None
        try:
            t = getattr(chunk, "text", None)
            if t:
                response_parts.append(t)
        except Exception:
            pass

        # 2) Tool calls (function_calls property preferred)
        fc_list = []
        try:
            fc_list = getattr(chunk, "function_calls", None) or []
        except Exception:
            fc_list = []

        new_calls = []

        def _to_plain_dict(obj):
            """
            Best-effort conversion of SDK objects to plain dict/list.
            """
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
            # Fallback: read from candidates -> parts[].function_call
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

        # De-duplicate tool calls and mark force flag if any found
        if new_calls:
            seen = {(tc["function"]["name"], tc["function"]["arguments"]) for tc in state.tool_calls}
            for tc in new_calls:
                key = (tc["function"]["name"], tc["function"]["arguments"])
                if key not in seen:
                    state.tool_calls.append(tc)
                    seen.add(key)

        # 3) Inspect candidates for code execution parts, inline images, and citations
        try:
            cands = getattr(chunk, "candidates", None) or []
            for cand in cands:
                content = getattr(cand, "content", None)
                parts = getattr(content, "parts", None) or []

                for p in parts:
                    # Code execution: executable code part -> open or append within fenced block
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

                    # Code execution result -> close fenced block (output will be streamed as normal text if provided)
                    cer = getattr(p, "code_execution_result", None)
                    if cer:
                        if state.is_code:
                            response_parts.append("\n\n```\n-----------\n")
                            state.is_code = False
                        # Note: We do not append execution outputs here to avoid duplicating chunk.text.

                    # Inline image blobs
                    blob = getattr(p, "inline_data", None)
                    if blob:
                        mime = (getattr(blob, "mime_type", "") or "").lower()
                        if mime.startswith("image/"):
                            data = getattr(blob, "data", None)
                            if data:
                                # inline_data.data may be bytes or base64-encoded string
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

                    # File data that points to externally hosted image (http/https)
                    fdata = getattr(p, "file_data", None)
                    if fdata:
                        uri = getattr(fdata, "file_uri", None) or getattr(fdata, "uri", None)
                        mime = (getattr(fdata, "mime_type", "") or "").lower()
                        if uri and mime.startswith("image/") and (uri.startswith("http://") or uri.startswith("https://")):
                            if ctx.urls is None:
                                ctx.urls = []
                            ctx.urls.append(uri)

            # Collect citations (web search URLs) if present in candidates metadata
            self._collect_google_citations(ctx, state, chunk)

        except Exception:
            # Never break stream on extraction failures
            pass

        # Combine all response parts
        response = "".join(response_parts) if response_parts else None
        return response

    def _process_raw(self, chunk) -> Optional[str]:
        """
        Raw chunk fallback.

        :param chunk: The chunk object from the stream
        :return: String representation of chunk or None
        """
        if chunk is not None:
            return chunk if isinstance(chunk, str) else str(chunk)
        return None

    # ------------ Usage helpers ------------

    def _safe_get(self, obj, path: str):
        """
        Dot-path getter for dicts and objects.

        :param obj: dict or object
        :param path: Dot-separated path string
        """
        cur = obj
        for seg in path.split("."):
            if cur is None:
                return None
            if isinstance(cur, dict):
                cur = cur.get(seg)
            else:
                # Support numeric indices for lists like candidates.0...
                if seg.isdigit() and isinstance(cur, (list, tuple)):
                    idx = int(seg)
                    if 0 <= idx < len(cur):
                        cur = cur[idx]
                    else:
                        return None
                else:
                    cur = getattr(cur, seg, None)
        return cur

    def _as_int(self, val):
        """
        Coerce to int if possible, else None.

        :param val: Any value
        :return: int or None
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
        Extract usage for OpenAI; include reasoning tokens in output if available.

        :param state: WorkerState
        :param u_obj: Usage object from OpenAI response
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

        :param state: WorkerState
        :param um_obj: Usage metadata object from Google chunk
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

    def _collect_google_citations(self, ctx: CtxItem, state: WorkerState, chunk: Any):
        """
        Collect web citations (URLs) from Google GenAI stream.

        Tries multiple known locations (grounding metadata and citation metadata)
        in a defensive manner to remain compatible with SDK changes.
        """
        try:
            cands = getattr(chunk, "candidates", None) or []
        except Exception:
            cands = []

        if not isinstance(state.citations, list):
            state.citations = []

        # Helper to add URLs with de-duplication
        def _add_url(url: Optional[str]):
            if not url or not isinstance(url, str):
                return
            url = url.strip()
            if not (url.startswith("http://") or url.startswith("https://")):
                return
            # Initialize ctx.urls if needed
            if ctx.urls is None:
                ctx.urls = []
            if url not in state.citations:
                state.citations.append(url)
            if url not in ctx.urls:
                ctx.urls.append(url)

        # Candidate-level metadata extraction
        for cand in cands:
            # Grounding metadata (web search attributions)
            gm = self._safe_get(cand, "grounding_metadata") or self._safe_get(cand, "groundingMetadata")
            if gm:
                atts = self._safe_get(gm, "grounding_attributions") or self._safe_get(gm, "groundingAttributions") or []
                try:
                    for att in atts or []:
                        # Try several common paths for URI
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
                # Also check search entry point
                for path in (
                    "search_entry_point.uri",
                    "search_entry_point.url",
                    "searchEntryPoint.uri",
                    "searchEntryPoint.url",
                    "search_entry_point.rendered_content_uri",
                    "searchEntryPoint.rendered_content_uri",
                ):
                    _add_url(self._safe_get(gm, path))

            # Citation metadata (legacy and alt paths)
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

            # Part-level citation metadata
            try:
                parts = self._safe_get(cand, "content.parts") or []
                for p in parts:
                    # Per-part citation metadata
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
                    # Per-part grounding attributions (rare)
                    gpa = self._safe_get(p, "grounding_attributions") or self._safe_get(p, "groundingAttributions") or []
                    for att in gpa or []:
                        for path in ("web.uri", "web.url", "source.web.uri", "source.web.url", "uri", "url"):
                            _add_url(self._safe_get(att, path))
            except Exception:
                pass

        # Bind to ctx on first discovery for compatibility with other parts of the app
        if state.citations and (ctx.urls is None or not ctx.urls):
            ctx.urls = list(state.citations)

    def cleanup(self):
        """Cleanup resources after worker execution."""
        sig = self.signals
        self.signals = None
        if sig is not None:
            try:
                sig.deleteLater()
            except RuntimeError:
                pass


class Stream:
    def __init__(self, window=None):
        """
        Stream controller

        :param window: Window instance
        """
        self.window = window
        self.ctx = None
        self.mode = None
        self.thread = None
        self.worker = None
        self.is_response = False
        self.reply = False
        self.internal = False
        self.context = None
        self.extra = {}

    def append(
            self,
            ctx: CtxItem,
            mode: str = None,
            is_response: bool = False,
            reply: str = False,
            internal: bool = False,
            context: Optional[BridgeContext] = None,
            extra: Optional[dict] = None
    ):
        """
        Asynchronous append of stream worker to the thread.

        :param ctx: Context item
        :param mode: Mode of operation (e.g., MODE_ASSISTANT)
        :param is_response: Whether this is a response stream
        :param reply: Reply identifier
        :param internal: Whether this is an internal stream
        :param context: Optional BridgeContext for additional context
        :param extra: Additional data to pass to the stream
        """
        self.ctx = ctx
        self.mode = mode
        self.is_response = is_response
        self.reply = reply
        self.internal = internal
        self.context = context
        self.extra = extra if extra is not None else {}

        worker = StreamWorker(ctx, self.window)

        worker.stream = ctx.stream
        worker.signals.eventReady.connect(self.handleEvent)
        worker.signals.errorOccurred.connect(self.handleError)
        worker.signals.end.connect(self.handleEnd)
        ctx.stream = None
        self.worker = worker

        self.window.core.debug.info("[chat] Stream begin...")
        self.window.threadpool.start(worker)

    @Slot(object)
    def handleEnd(self, ctx: CtxItem):
        """
        Slot for handling end of stream

        :param ctx: Context item
        """
        self.window.controller.ui.update_tokens()

        data = {"meta": self.ctx.meta, "ctx": self.ctx}
        event = RenderEvent(RenderEvent.STREAM_END, data)
        self.window.dispatch(event)
        self.window.controller.chat.output.handle_after(
            ctx=ctx,
            mode=self.mode,
            stream=True,
        )

        if self.mode == MODE_ASSISTANT:
            self.window.controller.assistant.threads.handle_output_message_after_stream(ctx)
        else:
            if self.is_response:
                self.window.controller.chat.response.post_handle(
                    ctx=ctx,
                    mode=self.mode,
                    stream=True,
                    reply=self.reply,
                    internal=self.internal
                )

        self.worker = None

    def handleEvent(self, event):
        """
        Slot for handling stream events

        :param event: RenderEvent
        """
        self.window.dispatch(event)

    def handleError(self, error):
        """
        Slot for handling stream errors

        :param error: Exception or error message
        """
        self.window.core.debug.log(error)
        if self.is_response:
            if not isinstance(self.extra, dict):
                self.extra = {}
            self.extra["error"] = error
            self.window.controller.chat.response.failed(self.context, self.extra)
            self.window.controller.chat.response.post_handle(
                ctx=self.ctx,
                mode=self.mode,
                stream=True,
                reply=self.reply,
                internal=self.internal,
            )

    def log(self, data: object):
        """
        Log data to the debug console

        :param data: object to log
        """
        self.window.core.debug.info(data)