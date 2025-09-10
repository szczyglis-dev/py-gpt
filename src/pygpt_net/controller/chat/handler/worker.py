#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.07 05:00:00                  #
# ================================================== #

import io
import json
from dataclasses import dataclass, field
from typing import Optional, Literal, Any
from enum import Enum

from PySide6.QtCore import QObject, Signal, Slot, QRunnable
from openai.types.chat import ChatCompletionChunk

from pygpt_net.core.events import RenderEvent
from pygpt_net.core.text.utils import has_unclosed_code_tag
from pygpt_net.item.ctx import CtxItem

from . import (
    openai_stream,
    google_stream,
    anthropic_stream,
    xai_stream,
    llamaindex_stream,
    langchain_stream,
    utils as stream_utils,
)

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
    - `chunk`: CtxItem, chunk str, begin bool
    """
    end = Signal(object)
    errorOccurred = Signal(Exception)
    eventReady = Signal(object)
    chunk = Signal(object, str, bool)  # CtxItem, chunk, begin


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

    # --- XAI SDK only ---
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
        emit_chunk = self.signals.chunk.emit

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
                        self._append_response(ctx, state, response, emit_chunk)

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

        :param ctrl: Controller instance for stop checking
        :param state: Current worker state
        :param ctx: Current context item
        :return: True if should stop
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

        :param chunk: The chunk object to classify
        :return: Detected ChunkType
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

        # fallback: OpenAI ChatCompletionChunk not caught above
        if isinstance(chunk, ChatCompletionChunk):
            return ChunkType.API_CHAT

        return ChunkType.RAW

    def _append_response(
            self,
            ctx: CtxItem,
            state: WorkerState,
            response: str,
            emit_chunk
    ):
        """
        Appends response delta and emits STREAM_APPEND event.

        :param ctx: Current context item
        :param state: Current worker state
        :param response: Response delta to append
        :param emit_chunk: Function to emit chunk event
        """
        if state.begin and response == "":
            return
        if state.out is None:
            state.out = io.StringIO()
        state.out.write(response)
        state.output_tokens += 1
        emit_chunk(ctx, response, state.begin)
        state.begin = False

    def _handle_after_loop(
            self,
            ctx: CtxItem,
            core,
            state: WorkerState
    ):
        """
        Post-loop handling for tool calls and images assembly.

        :param ctx: Current context item
        :param core: Core instance
        :param state: Current worker state
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

        # OpenAI: partial image assembly
        if state.is_image and state.img_path:
            core.debug.info("[chat] OpenAI partial image assembled")
            ctx.images = [state.img_path]

        # Google: inline images
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

        # xAI: extract tool calls from final response if not already present
        if (not state.tool_calls) and (state.xai_last_response is not None):
            try:
                calls = xai_stream.xai_extract_tool_calls(state.xai_last_response)
                if calls:
                    state.tool_calls = calls
            except Exception:
                pass

        # xAI: collect citations (final response) -> ctx.urls
        if state.xai_last_response is not None:
            try:
                cites = xai_stream.xai_extract_citations(state.xai_last_response) or []
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

        :param ctx: Current context item
        :param core: Core instance
        :param state: Current worker state
        :param emit_end: Function to emit end event
        :param emit_error: Function to emit error event
        """
        output = state.out.getvalue() if state.out is not None else ""
        if state.out is not None:
            try:
                state.out.close()
            except Exception:
                pass
            state.out = None

        #if has_unclosed_code_tag(output):
            #output += "\n```"

        # Google: resolve usage if present
        if ((state.usage_vendor is None or state.usage_vendor == "google")
                and not state.usage_payload and state.generator is not None):
            try:
                if hasattr(state.generator, "resolve"):
                    state.generator.resolve()
                    um = getattr(state.generator, "usage_metadata", None)
                    if um:
                        stream_utils.capture_google_usage(state, um)
            except Exception:
                pass

        # xAI: usage from final response if still missing
        if (not state.usage_payload) and (state.xai_last_response is not None):
            try:
                up = xai_stream.xai_extract_usage(state.xai_last_response)
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

        # OpenAI: download container files if present
        if state.files and not state.stopped:
            core.debug.info("[chat] Container files found, downloading...")
            try:
                core.api.openai.container.download_files(ctx, state.files)
            except Exception as e:
                core.debug.error(f"[chat] Error downloading container files: {e}")

        # Emit error and end
        if state.error:
            emit_error(state.error)
            ctx.msg_id = None
            # clear response_id on error - this prevents no response_id in API on next call
            # prev messages will be sent again, new response_id will be generated
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

        :param ctx: Current context item
        :param core: Core instance
        :param state: Current worker state
        :param chunk: The chunk to process
        :param etype: Optional event type for Responses API
        :return: Processed string delta or None
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

    def _process_api_chat(self, ctx, state, chunk):
        return openai_stream.process_api_chat(ctx, state, chunk)

    def _process_api_chat_responses(self, ctx, core, state, chunk, etype):
        return openai_stream.process_api_chat_responses(ctx, core, state, chunk, etype)

    def _process_api_completion(self, chunk):
        return openai_stream.process_api_completion(chunk)

    def _process_langchain_chat(self, chunk):
        return langchain_stream.process_langchain_chat(chunk)

    def _process_llama_chat(self, state, chunk):
        return llamaindex_stream.process_llama_chat(state, chunk)

    def _process_google_chunk(self, ctx, core, state, chunk):
        return google_stream.process_google_chunk(ctx, core, state, chunk)

    def _process_anthropic_chunk(self, ctx, core, state, chunk):
        return anthropic_stream.process_anthropic_chunk(ctx, core, state, chunk)

    def _process_xai_sdk_chunk(self, ctx, core, state, item):
        return xai_stream.process_xai_sdk_chunk(ctx, core, state, item)

    def _process_raw(self, chunk) -> Optional[str]:
        """
        Raw chunk fallback.

        :param chunk: The chunk to process
        :return: String representation or None
        """
        if chunk is not None:
            return chunk if isinstance(chunk, str) else str(chunk)
        return None

    def cleanup(self):
        """Cleanup resources after worker execution."""
        sig = self.signals
        self.signals = None
        if sig is not None:
            try:
                sig.deleteLater()
            except RuntimeError:
                pass