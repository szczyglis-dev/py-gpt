#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.18 00:00:00                  #
# ================================================== #

import json

from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core.prompts import ChatPromptTemplate
from llama_index.core.memory import ChatMemoryBuffer

from pygpt_net.core.bridge import BridgeContext
from pygpt_net.item.model import ModelItem
from pygpt_net.item.ctx import CtxItem

from .context import Context


class Chat:
    def __init__(self, window=None, storage=None):
        """
        Chat with index core

        :param window: Window instance
        """
        self.window = window
        self.storage = storage
        self.context = Context(window)

    def call(self, context: BridgeContext, extra: dict = None) -> bool:
        """
        Call chat, complete or query mode

        :param context: Bridge context
        :param extra: Extra arguments
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

        # if not raw, check if chat mode is available
        if "chat" in model.llama_index['mode']:
            return self.chat(
                context=context,
                extra=extra,
            )
        else:
            return self.query(
                context=context,
                extra=extra,
            )  # if not, use query mode

    def raw_query(self, context: BridgeContext, extra: dict = None) -> bool:
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

    def query(self, context: BridgeContext, extra: dict = None) -> bool:
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
        query = ctx.input  # user input
        verbose = self.window.core.config.get("log.llama", False)

        if model is None or not isinstance(model, ModelItem):
            raise Exception("Model config not provided")

        self.log("Query index...")
        self.log("Idx: {}, query: {}, model: {}".format(
            idx,
            query,
            model.id,
        ))

        index, service_context = self.get_index(idx, model)
        llm = service_context.llm
        input_tokens = self.window.core.tokens.from_llama_messages(
            query,
            [],
            model.id,
        )
        # query index
        tpl = self.get_custom_prompt(system_prompt)
        if tpl is not None:
            self.log("Query index with custom prompt: {}...".format(system_prompt))
            response = index.as_query_engine(
                llm=llm,
                streaming=stream,
                text_qa_template=tpl,
                verbose=verbose,
            ).query(query)  # query with custom sys prompt
        else:
            response = index.as_query_engine(
                llm=llm,
                streaming=stream,
                verbose=verbose,
            ).query(query)  # query with default prompt

        if response:
            if stream:
                ctx.add_doc_meta(self.get_metadata(response.source_nodes))  # store metadata
                ctx.stream = response.response_gen
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
            return True
        return False

    def chat(self, context: BridgeContext, extra: dict = None) -> bool:
        """
        Chat mode (conversation, using context from index) and append result to the context

        :param context: Bridge context
        :param extra: Extra arguments
        """
        idx = context.idx
        model = context.model
        system_prompt = context.system_prompt  # get final system prompt
        stream = context.stream
        ctx = context.ctx
        query = ctx.input  # user input
        chat_mode = self.window.core.config.get("llama.idx.chat.mode")
        use_index = True
        verbose = self.window.core.config.get("log.llama", False)

        if idx is None or idx == "_":
            chat_mode = "simple"  # do not use query engine if no index
            use_index = False

        if model is None or not isinstance(model, ModelItem):
            raise Exception("Model config not provided")

        self.log("Chat with index...")
        self.log("Idx: {}, query: {}, chat_mode: {}, model: {}".format(
            idx,
            query,
            chat_mode,
            model.id,
        ))

        # use index only if idx is not empty, otherwise use only LLM
        index = None
        if use_index:
            index, service_context = self.get_index(idx, model)
            llm = service_context.llm  # no multimodal LLM in service context
        else:
            llm = self.window.core.idx.llm.get(model)

        # if multimodal support, try to get multimodal provider
        # if model.is_multimodal():
            # llm = self.window.core.idx.llm.get(model, multimodal=True)  # get multimodal LLM model

        # append context from DB
        history = self.context.get_messages(
            ctx.input,
            system_prompt,
            context.history,
        )
        memory = self.get_memory_buffer(history, llm)
        input_tokens = self.window.core.tokens.from_llama_messages(
            query,
            history,
            model.id,
        )

        if use_index:
            # index as query engine
            chat_engine = index.as_chat_engine(
                llm=llm,
                chat_mode=chat_mode,
                memory=memory,
                verbose=verbose,
                system_prompt=system_prompt,
            )
            if stream:
                response = chat_engine.stream_chat(query)
            else:
                response = chat_engine.chat(query)
        else:
            # prepare tools (native calls if enabled)
            tools = self.window.core.agents.tools.prepare(context, extra)

            # without index, use LLM as chat engine
            history.insert(0, self.context.add_system(system_prompt))
            history.append(self.context.add_user(query))
            if stream:
                response = llm.stream_chat_with_tools(
                    tools=tools,
                    messages=history,
                )
            else:
                response = llm.chat_with_tools(
                    tools=tools,
                    messages=history,
                )

        # handle response
        if response:
            if use_index:
                # from index as query engine
                if stream:
                    ctx.stream = response.response_gen
                    ctx.input_tokens = input_tokens
                    ctx.set_output("", "")
                    ctx.add_doc_meta(self.get_metadata(response.source_nodes))  # store metadata
                else:
                    ctx.input_tokens = input_tokens
                    ctx.output_tokens = self.window.core.tokens.from_llama_messages(
                        response.response,
                        [],
                        model.id,
                    )  # calc from response
                    output = response.response
                    if output is None:
                        output = ""
                    ctx.set_output(output, "")
                    print("output", output)
                    ctx.add_doc_meta(self.get_metadata(response.source_nodes))  # store metadata
            else:
                # from LLM
                if stream:
                    # tools handled in stream output controller
                    ctx.stream = response  # chunk is in response.delta
                    ctx.input_tokens = input_tokens
                    ctx.set_output("", "")
                else:
                    # unpack tool calls
                    tool_calls = llm.get_tool_calls_from_response(
                        response, error_on_no_tool_call=False
                    )
                    ctx.tool_calls = self.window.core.command.unpack_tool_calls_from_llama(tool_calls)
                    output = response.message.content
                    if output is None:
                        output = ""
                    ctx.set_output(output, "")
                    ctx.input_tokens = input_tokens
                    ctx.output_tokens = self.window.core.tokens.from_llama_messages(
                        output,
                        [],
                        model.id,
                    ) # calc from response
            return True
        return False

    def query_file(
            self,
            ctx: CtxItem,
            path: str,
            query: str,
            model: ModelItem = None
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

        service_context = self.window.core.idx.llm.get_service_context(model=model)
        llm = service_context.llm
        tmp_id, index = self.storage.get_tmp(path, service_context=service_context)  # get or create tmp index

        idx = "tmp:{}".format(path)  # tmp index id
        self.log("Indexing to temporary in-memory index: {}...".format(idx))

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
            self.log("Querying temporary in-memory index: {}...".format(idx))
            response = index.as_query_engine(
                llm=llm,
                streaming=False,
            ).query(query)  # query with default prompt
            if response:
                ctx.add_doc_meta(self.get_metadata(response.source_nodes))  # store metadata
                output = response.response

        # clean tmp index
        self.log("Removing temporary in-memory index: {} ({})...".format(idx, tmp_id))
        self.storage.clean_tmp(tmp_id)  # clean memory
        self.log("Returning response: {}".format(output))
        return output

    def query_web(
            self,
            ctx: CtxItem,
            type: str,
            url: str,
            args: dict,
            query: str,
            model: ModelItem = None
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
        context = self.window.core.idx.llm.get_service_context(model=model)
        tmp_id, index = self.storage.get_tmp(id, service_context=context)  # get or create tmp index
        llm = context.llm

        idx = "tmp:{}".format(id)  # tmp index id
        self.log("Indexing to temporary in-memory index: {}...".format(idx))

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
            self.log("Querying temporary in-memory index: {}...".format(idx))
            response = index.as_query_engine(
                llm=llm,
                streaming=False,
            ).query(query)  # query with default prompt
            if response:
                ctx.add_doc_meta(self.get_metadata(response.source_nodes))  # store metadata
                output = response.response

        # clean tmp index# clean tmp index
        self.log("Removing temporary in-memory index: {} ({})...".format(idx, tmp_id))
        self.storage.clean_tmp(tmp_id)  # clean memory
        self.log("Returning response: {}...".format(output))
        return output

    def get_memory_buffer(self, history: list, llm = None) -> ChatMemoryBuffer:
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

    def get_custom_prompt(self, prompt: str = None) -> ChatPromptTemplate or None:
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

    def get_index(self, idx, model):
        """
        Get index instance

        :param idx: idx name (id)
        :param model: model name
        :return:
        """
        # check if index exists
        if not self.storage.exists(idx):
            if idx is None:
                # create empty in memory idx
                service_context = self.window.core.idx.llm.get_service_context(model=model)
                index = self.storage.index_from_empty()
                return index, service_context
            # raise Exception("Index not prepared")

        service_context = self.window.core.idx.llm.get_service_context(model=model)
        index = self.storage.get(idx, service_context=service_context)  # get index
        return index, service_context

    def get_metadata(self, source_nodes: list):
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
        i = 1
        max = 3
        min_score = 0.3
        for node in source_nodes:
            if hasattr(node, "id_"):
                id = node.id_
                if node.metadata is not None:
                    score = node.get_score()
                    if score > min_score:
                        metadata[id] = node.metadata
                        metadata[id]["score"] = score
                        i += 1
                        if i > max:
                            break
        return metadata

    def parse_metadata(self, metadata: dict):
        """
        Parse metadata

        :param metadata: metadata
        :return: metadata
        """
        if (metadata is None
                or not isinstance(metadata, dict)
                or len(metadata) == 0):
            return {}
        meta = {}
        for node in metadata:
            doc_id = list(node.keys())[0]
            meta[doc_id] = node[doc_id]
            break
        return meta

    def log(self, msg: str):
        """
        Log info message

        :param msg: message
        """
        # disabled logging for thread safety
        if self.window.core.config.get("mode") == "agent_llama":
            return
        is_log = False
        if self.window.core.config.has("log.llama") \
                and self.window.core.config.get("log.llama"):
            is_log = True
        self.window.core.debug.info(msg, not is_log)
        if is_log:
            print("[LLAMA-INDEX] {}".format(msg))
        self.window.idx_logger_message.emit(msg)
