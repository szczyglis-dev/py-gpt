#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.22 00:50:00                  #
# ================================================== #

import json
from typing import Optional, Dict, Any, List

from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core.prompts import ChatPromptTemplate
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.tools import BaseTool, QueryEngineTool

from pygpt_net.core.types import (
    MODE_CHAT,
    MODE_LLAMA_INDEX,
    MODE_AGENT_LLAMA,
    MODE_AGENT_OPENAI,
    MODE_AGENT_V2,
    MODE_COMPUTER,
    TOOL_QUERY_ENGINE_NAME,
    TOOL_QUERY_ENGINE_DESCRIPTION,
)
from pygpt_net.core.bridge.worker import BridgeSignals
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.provider.llms.agent_computer import ComputerRuntime
from pygpt_net.item.model import ModelItem
from pygpt_net.item.ctx import CtxItem

from .context import Context
from .rag_context import RAGContextPreparer
from .response import Response

class Chat:
    # Retrieval scores are backend/model dependent and are not a portable
    # confidence scale. Ask the retriever for a bounded set of its best-ranked
    # candidates and keep that ordering instead of applying absolute score
    # thresholds (e.g. 0.2/0.5), which can silently discard valid context.
    RETRIEVAL_TOP_K = 5
    METADATA_MAX_NODES = 3

    def __init__(self, window=None, storage=None):
        """
        Chat with index core

        :param window: Window instance
        """
        self.window = window
        self.storage = storage
        self.context = Context(window)
        self.response = Response(window)
        self.rag_context = RAGContextPreparer(
            top_k=self.RETRIEVAL_TOP_K,
            logger=self.log,
        )
        self.prev_message = None  # previous message, used in chat mode

    def call(
            self,
            context: BridgeContext,
            extra: Optional[Dict[str, Any]] = None,
            signals: Optional[BridgeSignals] = None
    ) -> bool:
        """
        Call chat, complete or query mode

        :param context: Bridge context
        :param extra: Extra arguments
        :param signals: Bridge signals
        :return: True if success
        """
        model = context.model
        idx_mode = context.idx_mode  # mode

        if model is None or not isinstance(model, ModelItem):  # check if model is provided
            raise Exception("Model config not provided")

        if idx_mode == "query":  # query index only (raw mode)
            return self.raw_query(
                context=context,
                extra=extra,
            )
        elif idx_mode == "retrieval":  # retrieval mode
            return self.retrieval(
                context=context,
                extra=extra,
            )

        # chat
        return self.chat(
            context=context,
            extra=extra,
            signals=signals,
        )

    def raw_query(
            self,
            context: BridgeContext,
            extra: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Raw query mode

        :param context: Bridge context
        :param extra: Extra arguments
        :return: True if success
        """
        return self.query(
            context=context,
            extra=extra,
        )

    def query(
            self,
            context: BridgeContext,
            extra: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Query index mode (no chat, only single query) and append results to context

        :param context: Bridge context
        :param extra: Extra arguments
        :return: True if success
        """
        idx = context.idx
        model = context.model
        system_prompt = context.system_prompt_raw  # get raw system prompt, without plugin addons
        stream = context.stream
        ctx = context.ctx
        query = context.prompt if context.prompt else ctx.final_input  # final user input (incl. attachment context)
        verbose = self.window.core.config.get("log.llama", False)

        if model is None or not isinstance(model, ModelItem):
            raise Exception("Model config not provided")

        self.log("Query index...")
        self.log(f"Idx: {idx}, query: {query}, model: {model.id}")

        index, llm = self.get_index(idx, model, stream=stream)
        input_tokens = self.window.core.tokens.from_llama_messages(
            query,
            [],
            model.id,
        )
        # query index
        tpl = self.get_custom_prompt(system_prompt)
        query_engine_kwargs = {
            "llm": llm,
            "streaming": stream,
            "verbose": verbose,
        }
        if tpl is not None:
            self.log(f"Query index with custom prompt: {system_prompt}...")
            query_engine_kwargs["text_qa_template"] = tpl
        self.window.core.api.logger.log_input(
            type="llama_index.query",
            provider=model.provider,
            kwargs=query_engine_kwargs,
            input=query,
            extra=extra,
            model=model.id,
            path="index.as_query_engine(...).query",
        )
        response = index.as_query_engine(**query_engine_kwargs).query(query)

        if response:
            if not stream:
                self.window.core.api.logger.log_output(
                    type="llama_index.query",
                    provider=model.provider,
                    output=response,
                    model=model.id,
                )
            if stream:
                ctx.add_doc_meta(self.get_metadata(response.source_nodes))  # store metadata
                ctx.stream = self.response.stream_with_llm_artifacts(
                    ctx,
                    llm,
                    response.response_gen,
                )
                ctx.input_tokens = input_tokens
                ctx.set_output("", "")
            else:
                ctx.add_doc_meta(self.get_metadata(response.source_nodes))  # store metadata
                ctx.input_tokens = input_tokens
                ctx.output_tokens = self.window.core.tokens.from_llama_messages(
                    response.response,
                    [],
                    model.id,
                )  # calc from response
                ctx.set_output(str(response.response), "")
                self.response.collect_llm_urls(ctx, llm)
            return True
        return False

    def retrieval(
            self,
            context: BridgeContext,
            extra: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Retrieve documents from index only

        :param context: Bridge context
        :param extra: Extra arguments
        :return: True if success
        """
        idx = context.idx
        model = context.model
        stream = context.stream
        ctx = context.ctx
        query = context.prompt if context.prompt else ctx.final_input  # final user input (incl. attachment context)
        verbose = self.window.core.config.get("log.llama", False)

        self.log("Retrieval...")
        self.log(f"Idx: {idx}, retrieve only: {query}")

        index, llm = self.get_index(idx, model, stream=stream)
        nodes = self._retrieve_nodes(index, query)
        outputs = []
        self.log(f"Retrieved {len(nodes)} nodes...")
        for node in nodes:
            outputs.append({
                "text": self._get_node_text(node),
                "score": self._get_node_score(node),
            })
        if outputs:
            response = ""
            for output in outputs:
                response += f"**Score: {output['score']}**\n\n{output['text']}"
                if output != outputs[-1]:
                    response += "\n\n-------\n\n"
            ctx.set_output(response)
            ctx.add_doc_meta(self.get_metadata(nodes))
        return True

    def chat(
            self,
            context: BridgeContext,
            extra: Optional[Dict[str, Any]] = None,
            disable_cmd: bool = False,
            signals: Optional[BridgeSignals] = None
    ) -> bool:
        """
        Chat mode (conversation, using context from index) and append result to the context

        :param context: Bridge context
        :param extra: Extra arguments
        :param disable_cmd: Disable tools
        :param signals: Bridge signals
        """
        idx = context.idx
        model = context.model
        system_prompt = context.system_prompt  # get final system prompt
        stream = context.stream
        ctx = context.ctx
        query = context.prompt if context.prompt else ctx.final_input  # final user input (incl. attachment context)
        chat_mode = self.window.core.config.get("llama.idx.chat.mode")
        use_index = True
        verbose = self.window.core.config.get("log.llama", False)
        allow_native_tool_calls = True
        response = None
        attachments = context.attachments  # attachments
        cmd_enabled = self.window.core.config.get("cmd", False)  # use tools
        if not self.window.core.models.is_tool_call_allowed(context.mode, model):
            allow_native_tool_calls = False
        if disable_cmd or (extra and extra.get("disable_tools", False)):
            cmd_enabled = False

        # ReAct is an automatic fallback for models/providers that cannot use
        # native tool calls in the current Chat with Files path. There is no
        # user-facing switch: native tool calls are preferred whenever they are
        # available, and ReAct is used only when tools are enabled and the
        # native path is unavailable.
        use_react = bool(cmd_enabled and not allow_native_tool_calls)

        if not self.window.core.idx.is_valid(idx):
            chat_mode = "simple"  # do not use query engine if no index
            use_index = False

        if model is None or not isinstance(model, ModelItem):
            raise Exception("Model config not provided")

        # Provider-native Computer Use is a client-side continuation protocol.
        # Chat with Files is synchronous LlamaIndex code, so bind a tiny runtime
        # adapter that reuses the same provider adapters/executor as Agents v2.
        computer_runtime = ComputerRuntime(self.window, context)
        force_computer_use = context.parent_mode == MODE_COMPUTER

        # When Computer Use is routed through RAG/LlamaIndex, the visible mode
        # is still Computer Use even though the bridge runtime is llama_index.
        # Force the provider-native Computer Use remote tool in that case so the
        # RAG backend keeps the same computer-control capability as native mode.

        # Direct RAG prefetch for native tool calls is handled later, after the
        # index, LLM, chat history and tool schemas are available. This lets the
        # same RAGContextPreparer account for the real final-request token budget.
        auto_retrieve = self.window.core.config.get("llama.idx.chat.auto_retrieve", False)

        # -- log ---
        self.log("Chat with index...")
        self.log(
            f"Idx: {idx}, "
            f"chat_mode: {chat_mode}, "
            f"model: {model.id}, "
            f"stream: {stream}, "
            f"native tool calls: {allow_native_tool_calls}, "
            f"use react: {use_react}, "
            f"use index: {use_index}, "
            f"cmd enabled: {cmd_enabled}, "
            f"num_attachments: {len(context.attachments) if context.attachments else 0}, "
            f"auto retrieve: {auto_retrieve}, "
            f"query: {query}"
        )

        # use index only if idx is not empty, otherwise use only LLM
        index = None
        if use_index:
            index, llm = self.get_index(
                idx,
                model,
                stream=stream,
                computer_runtime=computer_runtime,
                force_computer_use=force_computer_use,
            )
        else:
            llm = self.window.core.idx.llm.get(
                model,
                stream=stream,
                computer_runtime=computer_runtime,
                force_computer_use=force_computer_use,
            )

        # TODO: if multimodal support, try to get multimodal provider
        # if model.is_multimodal():
            # llm = self.window.core.idx.llm.get(model, multimodal=True)  # get multimodal LLM model

        # append context from DB
        history = self.context.get_messages(
            input_prompt=query,
            system_prompt=system_prompt,
            history=context.history,
            allow_native_tool_calls=allow_native_tool_calls,
            prev_message=self.prev_message,
            attachments=attachments,
        )

        # Native tool-result continuations are already reconstructed by Context as
        # ``assistant(tool_calls) -> tool(result)``.  The internal reply prompt is
        # only a transport envelope for the plugin result and must not be appended
        # again as a normal user message.  Doing so produces
        # ``... -> tool(result) -> user(result)``; OpenAI-compatible Ollama/Gemma
        # is especially sensitive to that invalid continuation shape and may return
        # no final assistant content after a successfully executed tool.
        last_role = getattr(history[-1], "role", None) if history else None
        if hasattr(last_role, "value"):
            last_role = last_role.value
        native_tool_continuation = bool(
            allow_native_tool_calls
            and self.prev_message is not None
            and last_role == MessageRole.TOOL.value
        )
        if native_tool_continuation:
            self.log(
                "Native tool continuation: tool result already present in history; "
                "skipping synthetic user reply."
            )

            # ``attach_runtime_file`` returns the protocol-required textual tool
            # result plus an ephemeral local attachment. Tool-result messages do
            # not have a portable image payload across LlamaIndex providers, so
            # promote runtime images to a normal user multimodal message for the
            # immediate follow-up, just like the Agents v2 main FunctionAgent.
            # The attachment stays transport-only and is not persisted in ctx.
            if model.is_image_input() and context.attachments:
                runtime_message = self.context.add_runtime_images(context.attachments)
                if runtime_message is not None:
                    history.append(runtime_message)
                    self.log(
                        "Native tool continuation: appended runtime image(s) as "
                        "a multimodal user message."
                    )

        # Prepare the real tool set before RAG packing so PromptHelper can reserve
        # space for native tool schemas in the final request. ReAct keeps the
        # native LlamaIndex QueryEngineTool path inside call_agent().
        tools = self.window.core.agents.tools.prepare(context, extra, force=True)

        # LlamaIndex 0.14.22+ can buffer Context/CompactAndRefine streaming before
        # PyGPT's StreamWorker consumes it. Use one shared pre-answer RAG pipeline
        # for direct provider calls:
        #   * tools OFF + stream: always prepare context before llm.stream_chat();
        #   * native tools + auto-retrieve: prepare the same context before
        #     llm.[stream_]chat_with_tools().
        # ReAct is intentionally excluded here: its RAG path remains fully
        # handled by LlamaIndex through QueryEngineTool/as_query_engine().
        direct_rag = bool(
            use_index
            and (
                (stream and not cmd_enabled)
                or (
                    cmd_enabled
                    and not use_react
                    and auto_retrieve
                    and not ctx.internal
                )
            )
        )
        if direct_rag:
            prepared_rag = self.prepare_rag_context(
                index=index,
                llm=llm,
                query=query,
                history=history,
                chat_mode=chat_mode,
                system_prompt=system_prompt,
                model=model,
                tools=tools if cmd_enabled else None,
            )
            if prepared_rag.has_context:
                system_prompt += "\n\n" + prepared_rag.context
            if prepared_rag.nodes:
                ctx.add_doc_meta(self.get_metadata(prepared_rag.nodes))

            self.log(
                f"Direct RAG context prepared: nodes={len(prepared_rag.nodes)}, "
                f"chat_mode={chat_mode}, condensed={prepared_rag.condensed}, "
                f"retrieval_query={prepared_rag.retrieval_query}, "
                f"tools={cmd_enabled}"
            )
            # Final generation now belongs to the normal provider path.
            use_index = False

        self.prev_message = None  # reset previous message
        memory = self.get_memory_buffer(history, llm)
        input_tokens = self.window.core.tokens.from_llama_messages(
            query,
            history,
            model.id,
        )
        ctx.input_tokens = input_tokens

        if use_index:
            # 1) if tools enabled use agent engine
            if cmd_enabled:
                if use_react: # TOOLS + REACT + INDEX
                    ctx.agent_call = True  # directly return tool call response
                    ctx.use_agent_final_response = True  # use agent final response as output
                    response = self.call_agent(
                        context=context,
                        signals=signals,
                        tools=tools,
                        ctx=ctx,
                        query=query,
                        history=context.history,
                        llm=llm,
                        index=index,
                        system_prompt=system_prompt,
                        chat_mode=chat_mode,
                        verbose=verbose,
                    )
                else:
                    use_index = False # fallback to LLM if tools enabled but not using ReAct
            else:
                # 2) tools disabled + non-stream: keep the LlamaIndex chat engine.
                # Streaming requests have already been routed to direct LLM
                # streaming above after explicit RAG retrieval.
                chat_engine_kwargs = {
                    "llm": llm,
                    "chat_mode": chat_mode,
                    "memory": memory,
                    "verbose": verbose,
                    "system_prompt": system_prompt,
                }
                self.window.core.api.logger.log_input(
                    type="llama_index.index.chat",
                    provider=model.provider,
                    kwargs=chat_engine_kwargs,
                    input=query,
                    history=history,
                    extra=extra,
                    model=model.id,
                    path="index.as_chat_engine(...).chat",
                )
                chat_engine = index.as_chat_engine(**chat_engine_kwargs)
                response = chat_engine.chat(query)

                # check for not empty
                if hasattr(response, "source_nodes") and len(response.source_nodes) == 0:
                    self.log("No source nodes found in response, fallback to LLM directly...")
                    use_index = False # fallback

        if not use_index:
            if cmd_enabled:
                if use_react:  # TOOLS + REACT + NO INDEX
                    ctx.agent_call = True  # directly return tool call response
                    ctx.use_agent_final_response = True  # use agent final response as output
                    response = self.call_agent(
                        context=context,
                        signals=signals,
                        tools=tools,
                        ctx=ctx,
                        query=query,
                        history=context.history,
                        llm=llm,
                        index=index,
                        system_prompt=system_prompt,
                        chat_mode=chat_mode,
                        verbose=verbose,
                    )
                else:
                    history.insert(0, self.context.add_system(system_prompt))
                    if not native_tool_continuation:
                        history.append(self.context.add_user(
                            query,
                            attachments=context.attachments,
                            allow_images=model.is_image_input(),
                        ))
                    if stream: # TOOLS + STREAM + NO INDEX
                        # IMPORTANT: stream chat with tools not supported by all providers
                        if allow_native_tool_calls and hasattr(llm, "stream_chat_with_tools"):
                            self.log("Using with tools...")
                            request_kwargs = {"tools": tools, "messages": history}
                            self.window.core.api.logger.log_input(
                                type="llama_index.stream_chat_with_tools", provider=model.provider,
                                kwargs=request_kwargs, input=query, history=history, extra=extra,
                                model=model.id, path="llm.stream_chat_with_tools",
                            )
                            response = llm.stream_chat_with_tools(**request_kwargs)
                        else:
                            request_kwargs = {"messages": history}
                            self.window.core.api.logger.log_input(
                                type="llama_index.stream_chat", provider=model.provider,
                                kwargs=request_kwargs, input=query, history=history, extra=extra,
                                model=model.id, path="llm.stream_chat",
                            )
                            response = llm.stream_chat(**request_kwargs)
                    else: # TOOLS + NO INDEX
                        # IMPORTANT: stream chat with tools not supported by all providers
                        if allow_native_tool_calls and hasattr(llm, "chat_with_tools"):
                            self.log("Using with tools...")
                            request_kwargs = {"tools": tools, "messages": history}
                            self.window.core.api.logger.log_input(
                                type="llama_index.chat_with_tools", provider=model.provider,
                                kwargs=request_kwargs, input=query, history=history, extra=extra,
                                model=model.id, path="llm.chat_with_tools",
                            )
                            response = llm.chat_with_tools(**request_kwargs)
                        else:
                            request_kwargs = {"messages": history}
                            self.window.core.api.logger.log_input(
                                type="llama_index.chat", provider=model.provider,
                                kwargs=request_kwargs, input=query, history=history, extra=extra,
                                model=model.id, path="llm.chat",
                            )
                            response = llm.chat(**request_kwargs)
            else:
                # NO TOOLS + DIRECT LLM. If RAG is active in streaming mode,
                # the prepared RAG context was already appended to the system prompt.
                history.insert(0, self.context.add_system(system_prompt))
                history.append(self.context.add_user(
                    query,
                    attachments=context.attachments,
                    allow_images=model.is_image_input(),
                ))
                if stream:
                    request_kwargs = {"messages": history}
                    self.window.core.api.logger.log_input(
                        type="llama_index.stream_chat", provider=model.provider,
                        kwargs=request_kwargs, input=query, history=history, extra=extra,
                        model=model.id, path="llm.stream_chat",
                    )
                    response = llm.stream_chat(**request_kwargs)
                else:
                    request_kwargs = {"messages": history}
                    self.window.core.api.logger.log_input(
                        type="llama_index.chat", provider=model.provider,
                        kwargs=request_kwargs, input=query, history=history, extra=extra,
                        model=model.id, path="llm.chat",
                    )
                    response = llm.chat(**request_kwargs)

        # handle response, append output to ctx, etc.
        if response:
            if not stream:
                self.window.core.api.logger.log_output(
                    type="llama_index.chat",
                    provider=model.provider,
                    output=response,
                    model=model.id,
                )
            self.response.handle(
                ctx=ctx,
                model=model,
                llm=llm,
                response=response,
                cmd_enabled=cmd_enabled,
                use_react=use_react,
                use_index=use_index,
                stream=stream,
            )

            # append attachment images to context
            self.context.append_images(ctx)

            if not stream:
                # store output tokens
                ctx.output_tokens = self.window.core.tokens.from_llama_messages(
                    response,
                    [],
                    model.id,
                )

                # store prev message
                if (cmd_enabled and not use_react and not use_index) or (not cmd_enabled and not use_index):
                    self.prev_message = response.message

            # store metadata from response
            if hasattr(response, "source_nodes") and response.source_nodes:
                ctx.add_doc_meta(self.get_metadata(response.source_nodes))  # store metadata
            return True

        return False

    def prepare_rag_context(
            self,
            index,
            llm,
            query: str,
            history: Optional[List[ChatMessage]],
            chat_mode: str,
            system_prompt: str,
            model: ModelItem,
            tools: Optional[List[BaseTool]] = None,
    ):
        """Prepare selected-index evidence for a direct model/tool request.

        This is the shared integration point used by streaming RAG without tools
        and native tool-call auto-retrieval. ReAct intentionally keeps the native
        LlamaIndex QueryEngineTool/as_query_engine path.
        """
        context_window_limit = self.window.core.config.get("max_total_tokens")
        if not isinstance(context_window_limit, int):
            context_window_limit = 0

        model_context_window = self.window.core.models.get_num_ctx(model.id)
        if model_context_window > 0 and (
                context_window_limit <= 0
                or model_context_window < context_window_limit
        ):
            context_window_limit = model_context_window

        return self.rag_context.prepare(
            index=index,
            llm=llm,
            query=query,
            history=history or [],
            chat_mode=chat_mode,
            system_prompt=system_prompt,
            tools=tools,
            context_window_limit=context_window_limit,
        )

    def call_agent(
            self,
            context: BridgeContext,
            signals: Optional[BridgeSignals] = None,
            tools: Optional[List[BaseTool]] = None,
            ctx: Optional[CtxItem] = None,
            query: str = "",
            history: Optional[List[ChatMessage]] = None,
            llm=None,
            index=None,
            system_prompt: str = "",
            chat_mode: str = MODE_CHAT,
            verbose: bool = False,

    ) -> str:
        """
        Call agent with tools and index

        :param context: Bridge context
        :param signals: Bridge signals
        :param tools: Agent tools
        :param ctx: CtxItem
        :param query: Input prompt
        :param history: Chat history
        :param llm: LLM provider
        :param index: Index to use for additional context
        :param system_prompt: System prompt to use for agent
        :param chat_mode: Chat mode to use for agent, default is MODE_CHAT
        :param verbose: Verbose mode, default is False
        :return: True if success, False otherwise
        """
        tools = list(tools or [])
        if index:
            query_engine = index.as_query_engine(
                llm=llm,
                chat_mode=chat_mode,
                verbose=verbose,
            )
            index_tool = QueryEngineTool.from_defaults(
                query_engine=query_engine,
                name=TOOL_QUERY_ENGINE_NAME,
                description=TOOL_QUERY_ENGINE_DESCRIPTION,
                return_direct=True,
            )
            tools.append(index_tool)

        bridge_context = BridgeContext(
            ctx=ctx,
            model=context.model,
            history=history,
            prompt=query,
            stream=False,
        )
        extra = {
            "agent_provider": "react",  # use React workflow provider
            "agent_tools": tools,
        }
        self.window.core.api.logger.log_input(
            type="llama_index.react_agent",
            provider=context.model.provider if context.model else "",
            kwargs={"context": bridge_context, "extra": extra, "signals": None},
            input=query,
            history=history,
            extra={"system_prompt": system_prompt, "tools": tools, "chat_mode": chat_mode},
            model=context.model.id if context.model else None,
            path="core.agents.runner.call_once",
        )
        response_ctx = self.window.core.agents.runner.call_once(
            context=bridge_context,
            extra=extra,
            signals=None,
        )
        output = str(response_ctx.output) if response_ctx else "No response from agent."
        self.window.core.api.logger.log_output(
            type="llama_index.react_agent",
            provider=context.model.provider if context.model else "",
            output=output,
            model=context.model.id if context.model else None,
        )
        return output

    def is_stream_allowed(self, model: Optional[ModelItem] = None) -> bool:
        """
        Return whether Chat with Files can use the normal streaming path.

        Tools no longer disable streaming at the RAG/bridge level. Providers
        with native tool calls use ``stream_chat_with_tools``; providers that
        require the ReAct fallback still complete that fallback non-streaming
        inside ``call_agent``. Keep this hook for compatibility with callers
        and plugins that may query it.

        :param model: Current model, kept for API compatibility
        :return: True
        """
        return True

    def query_file(
            self,
            ctx: CtxItem,
            path: str,
            query: str,
            model: Optional[ModelItem] = None
    ) -> str:
        """
        Query file using temp index (created on the fly)

        :param ctx: context
        :param path: path to file to index (in memory)
        :param query: query
        :param model: model
        :return: response
        """
        if model is None:
            model = self.window.core.models.from_defaults()

        llm, embed_model = self.window.core.idx.llm.get_service_context(model=model, stream=False)
        tmp_id, index = self.storage.get_tmp(path, llm, embed_model)  # get or create tmp index

        idx = f"tmp:{path}"  # tmp index id
        self.log(f"Indexing to temporary in-memory index: {idx}...")

        # index file to tmp index
        files, errors = self.window.core.idx.indexing.index_files(
            idx=idx,
            index=index,
            path=path,
            is_tmp=True,  # do not try to remove old doc id
        )

        # query tmp index
        output = None
        if len(files) > 0:
            self.log(f"Querying temporary in-memory index: {idx}...")
            query_kwargs = {"llm": llm, "streaming": False}
            self.window.core.api.logger.log_input(
                type="llama_index.query_file", provider=model.provider,
                kwargs=query_kwargs, input=query, model=model.id,
                path="index.as_query_engine(...).query", extra={"path": path},
            )
            response = index.as_query_engine(**query_kwargs).query(query)
            if response:
                self.window.core.api.logger.log_output(
                    type="llama_index.query_file", provider=model.provider,
                    output=response, model=model.id,
                )
                ctx.add_doc_meta(self.get_metadata(response.source_nodes))  # store metadata
                output = response.response
                self.response.collect_llm_urls(ctx, llm)

        # clean tmp index
        self.log(f"Removing temporary in-memory index: {idx} ({tmp_id})...")
        self.storage.clean_tmp(tmp_id)  # clean memory
        self.log(f"Returning response: {output}")
        return output

    def query_web(
            self,
            ctx: CtxItem,
            type: str,
            url: str,
            args: Dict[str, Any],
            query: str,
            model: Optional[ModelItem] = None
    ) -> str:
        """
        Query web using temp index (created on the fly)

        :param ctx: context
        :param type: type of content
        :param url: url to index (in memory)
        :param args: extra args
        :param query: query
        :param model: model
        :return: response
        """
        parts = {
            "type": type,
            "url": url,
            "args": args,
        }
        id = json.dumps(parts)
        if model is None:
            model = self.window.core.models.from_defaults()
        llm, embed_model = self.window.core.idx.llm.get_service_context(model=model, stream=False)
        tmp_id, index = self.storage.get_tmp(id, llm, embed_model)  # get or create tmp index

        idx = f"tmp:{id}"  # tmp index id
        self.log(f"Indexing to temporary in-memory index: {idx}...")

        # index file to tmp index
        num, errors = self.window.core.idx.indexing.index_urls(
            idx=id,
            index=index,
            urls=[url],
            type=type,
            extra_args=args,
            is_tmp=True,  # do not try to remove old doc id
        )

        # query tmp index
        output = None
        if num > 0:
            self.log(f"Querying temporary in-memory index: {idx}...")
            query_kwargs = {"llm": llm, "streaming": False}
            self.window.core.api.logger.log_input(
                type="llama_index.query_web", provider=model.provider,
                kwargs=query_kwargs, input=query, model=model.id,
                path="index.as_query_engine(...).query",
                extra={"url": url, "content_type": type, "args": args},
            )
            response = index.as_query_engine(**query_kwargs).query(query)
            if response:
                self.window.core.api.logger.log_output(
                    type="llama_index.query_web", provider=model.provider,
                    output=response, model=model.id,
                )
                ctx.add_doc_meta(self.get_metadata(response.source_nodes))  # store metadata
                output = response.response
                self.response.collect_llm_urls(ctx, llm)

        # clean tmp index
        self.log(f"Removing temporary in-memory index: {idx} ({tmp_id})...")
        self.storage.clean_tmp(tmp_id)  # clean memory
        self.log(f"Returning response: {output}...")
        return output

    def query_attachment(
            self,
            query: str,
            path: str,
            model: Optional[ModelItem] = None,
            history: Optional[List[CtxItem]] = None,
            verbose: bool = False,
    ) -> str:
        """
        Query attachment

        :param query: query
        :param path: path to index
        :param model: model
        :param history: chat history
        :param verbose: verbose mode
        :return: response
        """
        if model is None:
            model = self.window.core.models.from_defaults()
        llm, embed_model = self.window.core.idx.llm.get_service_context(model=model, stream=False, auto_embed=True)
        index = self.storage.get_ctx_idx(path, llm, embed_model)

        # 1. try to retrieve directly from index. Similarity scores are not
        # comparable across all embedding models/vector stores, so do not use
        # a fixed confidence threshold here. The retriever already returns the
        # best-ranked candidates; provide the bounded top-k context downstream.
        nodes = self._retrieve_nodes(index, query)
        response = self._format_retrieved_nodes(nodes)
        output = ""
        if response:
            output = str(response)
            if verbose:
                score = self._get_node_score(nodes[0]) if nodes else None
                print(
                    f"Found using retrieval: {output} "
                    f"(nodes: {len(nodes)}, best score: {score})"
                )
        else:
            if verbose:
                print("Not found using retrieval, trying with query engine...")
            history = self.context.get_messages(
                query,
                "",
                history,
            )
            memory = self.get_memory_buffer(history, llm)
            chat_kwargs = {"llm": llm, "streaming": False, "memory": memory}
            self.window.core.api.logger.log_input(
                type="llama_index.query_attachment", provider=model.provider,
                kwargs=chat_kwargs, input=query, history=history, model=model.id,
                path="index.as_chat_engine(...).chat", extra={"path": path},
            )
            response = index.as_chat_engine(**chat_kwargs).chat(query)
            if response:
                self.window.core.api.logger.log_output(
                    type="llama_index.query_attachment", provider=model.provider,
                    output=response, model=model.id,
                )
                output = str(response.response)
        return output

    def query_retrieval(
            self,
            query: str,
            idx: str,
            model: Optional[ModelItem] = None
    ) -> str:
        """
        Retrieve and prepare RAG context without generating the final answer.

        This helper is shared by Agents v2 prefetch, legacy agents and RAG
        plugins. Keep the return value as plain prepared context text (without
        the system-prompt RAG wrapper) so existing callers remain compatible.

        :param query: query
        :param idx: index id
        :param model: model
        :return: prepared context text
        """
        if model is None:
            model = self.window.core.models.from_defaults()

        index, llm = self.get_index(idx, model, stream=False)
        prepared = self.prepare_rag_context(
            index=index,
            llm=llm,
            query=query,
            history=[],
            chat_mode="context",
            system_prompt="",
            model=model,
            tools=None,
        )

        # query_retrieval() historically returns only the retrieved material.
        # Callers such as Agents v2/legacy agents add their own prompt wrappers.
        if prepared.packed_chunks:
            return str(prepared.packed_chunks[0]).strip()
        return ""

    @staticmethod
    def _get_node_text(node: Any) -> str:
        """Return text from a retrieved node without depending on score."""
        if node is None:
            return ""
        text = getattr(node, "text", None)
        if text is None:
            wrapped = getattr(node, "node", None)
            text = getattr(wrapped, "text", None) if wrapped is not None else None
        if text is None:
            return ""
        return str(text).strip()

    @staticmethod
    def _get_node_score(node: Any):
        """Return a node score for diagnostics/metadata only, never filtering."""
        if node is None:
            return None
        try:
            return node.get_score()
        except (AttributeError, TypeError, ValueError):
            return getattr(node, "score", None)

    def _retrieve_nodes(
            self,
            index,
            query: str,
            top_k: Optional[int] = None,
    ) -> List[Any]:
        """Retrieve a bounded set of best-ranked, non-empty unique nodes.

        The retriever's ordering is authoritative. Raw similarity scores are
        intentionally not thresholded or re-ranked because their scale and
        interpretation can vary between embedding models and vector stores.
        """
        if index is None:
            return []

        if top_k is None:
            top_k = self.RETRIEVAL_TOP_K

        kwargs = {}
        if top_k is not None and top_k > 0:
            kwargs["similarity_top_k"] = top_k

        retriever = index.as_retriever(**kwargs)
        retrieved = retriever.retrieve(query) or []
        nodes = []
        seen = set()

        for node in retrieved:
            text = self._get_node_text(node)
            if not text:
                continue

            node_id = getattr(node, "node_id", None) or getattr(node, "id_", None)
            if node_id is not None:
                key = ("id", str(node_id))
            else:
                key = ("text", text)
            if key in seen:
                continue

            seen.add(key)
            nodes.append(node)

        return nodes

    def _format_retrieved_nodes(self, nodes: List[Any]) -> str:
        """Join retrieved chunks in retriever ranking order."""
        parts = []
        for node in nodes or []:
            text = self._get_node_text(node)
            if text:
                parts.append(text)
        return "\n\n---\n\n".join(parts)

    def get_memory_buffer(
            self,
            history: List[ChatMessage],
            llm = None
    ) -> ChatMemoryBuffer:
        """
        Get memory buffer

        :param history: list with chat history (ChatMessage)
        :param llm: LLM model
        :return: memory buffer with chat history
        """
        return ChatMemoryBuffer.from_defaults(
            chat_history=history,
            llm=llm,
        )

    def get_custom_prompt(
            self,
            prompt: Optional[str] = None
    ) -> Optional[ChatPromptTemplate]:
        """
        Get custom prompt template if sys prompt is not empty

        :param prompt: system prompt (optional)
        :return: ChatPromptTemplate or None if prompt is empty
        """
        if prompt is None or prompt.strip() == "":
            return None

        qa_msgs = [
            ChatMessage(
                role=MessageRole.SYSTEM,
                content=prompt,
            ),
            ChatMessage(
                role=MessageRole.USER,
                content=(
                    "Context information is below.\n"
                    "---------------------\n"
                    "{context_str}\n"
                    "---------------------\n"
                    "Given the context information and not prior knowledge, "
                    "answer the question: {query_str}\n"
                ),
            ),
        ]
        return ChatPromptTemplate(qa_msgs)

    def get_index(
            self,
            idx: str,
            model: ModelItem,
            stream: bool = False,
            computer_runtime=None,
            force_computer_use: bool = False,
    ):
        """
        Get index instance

        :param idx: idx name (id)
        :param model: model instance
        :param stream: stream mode
        :param computer_runtime: optional shared Computer Use runtime
        :param force_computer_use: force provider-native Computer Use remote tool
        """
        requested_idx = idx
        idx = self.window.core.idx.resolve_idx(idx)
        # check if index exists
        if idx is None:
            llm, embed_model = self.window.core.idx.llm.get_service_context(
                model=model,
                stream=stream,
                computer_runtime=computer_runtime,
                force_computer_use=force_computer_use,
            )
            return self.storage.index_from_empty(embed_model), llm
        if not self.storage.exists(idx):
            if idx is None:
                # create empty in memory idx
                llm, embed_model = self.window.core.idx.llm.get_service_context(
                    model=model,
                    stream=stream,
                    computer_runtime=computer_runtime,
                    force_computer_use=force_computer_use,
                )
                index = self.storage.index_from_empty(embed_model)
                return index, llm
            # raise Exception("Index not prepared")

        llm, embed_model = self.window.core.idx.llm.get_service_context(
            model=model,
            stream=stream,
            computer_runtime=computer_runtime,
            force_computer_use=force_computer_use,
        )
        index = self.storage.get(idx, llm, embed_model)  # get index
        if self.window.core.idx.project.is_virtual(requested_idx):
            group_id = self.window.core.idx.project.get_group_id_from_idx(idx)
            if group_id is not None:
                self.window.core.idx.project.ensure(group_id)
        return index, llm

    def get_metadata(
            self,
            source_nodes: Optional[list]
    ) -> Dict[str, Any]:
        """
        Get metadata from source nodes

        :param source_nodes: source nodes
        :return: metadata
        """
        if (source_nodes is None
                or not isinstance(source_nodes, list)
                or len(source_nodes) == 0):
            return {}
        metadata = {}
        for node in source_nodes:
            if len(metadata) >= self.METADATA_MAX_NODES:
                break
            if not hasattr(node, "id_"):
                continue

            node_metadata = getattr(node, "metadata", None)
            if node_metadata is None:
                continue

            # Keep the query engine/retriever ranking and do not hide sources
            # behind a backend-specific absolute score threshold. Copy metadata
            # before adding the diagnostic score so the source node is not
            # mutated as a side effect of rendering citations.
            item = dict(node_metadata)
            score = self._get_node_score(node)
            if score is not None:
                item["score"] = score
            metadata[node.id_] = item
        return metadata

    def log(self, msg: str):
        """
        Log info message

        :param msg: message
        """
        # disabled logging for thread safety
        if self.window.core.config.get("mode") in (MODE_AGENT_LLAMA, MODE_AGENT_OPENAI, MODE_AGENT_V2):
            return
        is_log = False
        if self.window.core.config.has("log.llama") \
                and self.window.core.config.get("log.llama"):
            is_log = True
        self.window.core.debug.info(msg, not is_log)
        if is_log:
            print(f"[LlamaIndex] {msg}")
        self.window.idx_logger_message.emit(msg)
