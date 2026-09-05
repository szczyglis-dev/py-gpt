#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.04 21:08:00                  #
# ================================================== #

from typing import Any

from pygpt_net.item.model import ModelItem
from pygpt_net.item.ctx import CtxItem
from pygpt_net.provider.api.reasoning import (
    is_tagged_reasoning_model, strip_and_store_tagged_reasoning,
)
from pygpt_net.provider.api.llama_index.stream import message_has_tool_calls

class Response:
    def __init__(self, window=None):
        """
        Response handler for processing responses from LLM or index.

        :param window: Window instance
        """
        self.window = window

    def _collect_llm_urls(self, ctx: CtxItem, llm) -> None:
        """Drain provider-native source URLs captured by a LlamaIndex LLM adapter."""
        if ctx is None or llm is None:
            return
        pop_urls = getattr(llm, "pop_pygpt_urls", None)
        if not callable(pop_urls):
            return
        try:
            urls = pop_urls() or []
        except Exception as exc:
            self.window.core.debug.log(exc)
            return
        if not urls:
            return
        if not isinstance(ctx.urls, list):
            ctx.urls = []
        seen = set(ctx.urls)
        for url in urls:
            value = str(url or "").strip()
            if not value or value in seen:
                continue
            ctx.urls.append(value)
            seen.add(value)

    def _stream_with_llm_artifacts(self, ctx: CtxItem, llm, stream):
        """Yield a sync LlamaIndex stream and collect provider artifacts at EOF."""
        try:
            for chunk in stream:
                yield chunk
        finally:
            self._collect_llm_urls(ctx, llm)

    def _prepare_output(self, ctx: CtxItem, model: ModelItem, output: Any) -> str:
        """Normalize local <think> reasoning without affecting other providers."""
        text = str(output)
        if is_tagged_reasoning_model(model):
            provider = str(getattr(model, "provider", "") or "local")
            text = strip_and_store_tagged_reasoning(ctx, text, provider=provider)
        return text

    def handle(
            self,
            ctx: CtxItem,
            model: ModelItem,
            llm,
            response: Any,
            cmd_enabled: bool,
            use_react: bool,
            use_index: bool,
            stream: bool
    ) -> None:
        """
        Handle response based on the context, model, and response type.

        :param ctx: Context item
        :param model: Model item
        :param llm: LLM instance
        :param response: Response data
        :param cmd_enabled: Tools enabled flag
        :param use_react: Use REACT flag
        :param use_index: Use index flag
        :param stream: Stream enabled flag
        """
        if cmd_enabled:
            # tools enabled
            if use_react:
                self.from_react(ctx, model, llm, response)  # TOOLS + REACT, non-stream
            else:
                if stream:
                    if use_index:
                        self.from_index_stream(ctx, model, llm, response)  # INDEX + STREAM
                    else:
                        self.from_llm_stream(ctx, model, llm, response)  # LLM + STREAM
                else:
                    if use_index:
                        self.from_index(ctx, model, llm, response)  # TOOLS + INDEX
                    else:
                        self.from_llm(ctx, model, llm, response)  # TOOLS + LLM
        else:
            # no tools
            if stream:
                if use_index:
                    self.from_index_stream(ctx, model, llm, response)  # INDEX + STREAM
                else:
                    self.from_llm_stream(ctx, model, llm, response)  # LLM + STREAM
            else:
                if use_index:
                    self.from_index(ctx, model, llm, response)  # INDEX
                else:
                    self.from_llm(ctx, model, llm, response)  # LLM

    def from_react(
            self,
            ctx: CtxItem,
            model: ModelItem,
            llm,
            response: Any
    ) -> None:
        """
        Handle response from REACT.

        :param ctx: CtxItem
        :param model: ModelItem
        :param response: Response data
        """
        output = self._prepare_output(ctx, model, response)
        ctx.set_output(output, "")
        self._collect_llm_urls(ctx, llm)

    def from_index(
            self,
            ctx: CtxItem,
            model: ModelItem,
            llm,
            response: Any
    ) -> None:
        """
        Handle response from index.

        :param ctx: CtxItem
        :param model: ModelItem
        :param response: Response data
        """
        output = self._prepare_output(ctx, model, response.response)
        ctx.set_output(output, "")
        self._collect_llm_urls(ctx, llm)

    def from_llm(
            self,
            ctx: CtxItem,
            model: ModelItem,
            llm,
            response: Any
    ) -> None:
        """
        Handle response from LLM.

        :param ctx: CtxItem
        :param model: ModelItem
        :param llm: LLM instance
        :param response: Response data
        """
        msg = getattr(response, "message", None)
        output = (getattr(msg, "content", None) if msg else None) or ""
        if isinstance(output, str):
            output = output.strip() or output
        output = self._prepare_output(ctx, model, output)
        tool_calls = llm.get_tool_calls_from_response(
            response,
            error_on_no_tool_call=False,
        )
        ctx.set_output(output, "")
        ctx.tool_calls = self.window.core.command.unpack_tool_calls_from_llama(tool_calls)
        self._collect_llm_urls(ctx, llm)

    def from_index_stream(
            self,
            ctx: CtxItem,
            model: ModelItem,
            llm,
            response: Any
    ) -> None:
        """
        Handle streaming response from index.

        :param ctx: CtxItem
        :param model: ModelItem
        :param response: Response data
        """
        ctx.stream = self._stream_with_llm_artifacts(ctx, llm, response.response_gen)
        ctx.set_output("", "")

    def from_llm_stream(
            self,
            ctx: CtxItem,
            model: ModelItem,
            llm,
            response: Any
    ) -> None:
        """
        Handle streaming response from LLM.

        :param ctx: CtxItem
        :param model: ModelItem
        :param llm: LLM instance
        :param response: Response data
        """
        stream = self._stream_with_prev_message(response)  # chunk is in response.delta
        ctx.stream = self._stream_with_llm_artifacts(ctx, llm, stream)
        ctx.set_output("", "")

    def _stream_with_prev_message(self, response: Any):
        """
        Preserve the native assistant message for a streamed LlamaIndex tool call.

        Chat with Files without ReAct uses the normal two-request native tool-call
        flow. The non-stream path stores ``response.message`` in
        ``core.idx.chat.prev_message`` so the follow-up request can contain the
        required ``assistant(tool_calls) -> tool(result)`` sequence. Previously
        the streamed path discarded the ChatResponse objects after yielding them,
        so the plugin executed but the follow-up request had no native assistant
        tool-call message to continue from.

        Keep the exact LlamaIndex/provider ChatMessage instead of rebuilding it
        from normalized dictionaries. This preserves provider-specific tool-call
        objects for both ChatCompletions and Responses API.

        :param response: LlamaIndex streaming response iterator
        :return: wrapped response iterator
        """
        tool_call_message = None
        for chunk in response:
            message = getattr(chunk, "message", None)
            if message_has_tool_calls(message):
                tool_call_message = message
            yield chunk

        if tool_call_message is None:
            return

        try:
            self.window.core.idx.chat.prev_message = tool_call_message
            self.window.core.debug.info(
                "[chat] Preserved streamed LlamaIndex tool-call message for reply continuation."
            )
        except Exception as e:
            self.window.core.debug.log(e)
