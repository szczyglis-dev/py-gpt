#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.05.01 03:00:00                  #
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
        Call chat or query mode

        :param context: Bridge context
        :param extra: Extra arguments
        :return: True if success
        """
        model = context.model
        idx_raw = context.idx_raw  # raw mode

        if model is None or not isinstance(model, ModelItem):  # check if model is provided
            raise Exception("Model config not provided")

        if idx_raw:  # query index (raw mode)
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

        if model is None or not isinstance(model, ModelItem):
            raise Exception("Model config not provided")

        self.log("Query index...")
        self.log("Idx: {}, query: {}, model: {}".format(
            idx,
            query,
            model.id,
        ))

        # check if index exists
        if not self.storage.exists(idx):
            raise Exception("Index not prepared")

        service_context = self.window.core.idx.llm.get_service_context(model=model)
        index = self.storage.get(idx, service_context=service_context)  # get index
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
                streaming=stream,
                text_qa_template=tpl,
            ).query(query)  # query with custom sys prompt
        else:
            response = index.as_query_engine(
                streaming=stream,
            ).query(query)  # query with default prompt

        if response:
            if stream:
                ctx.add_doc_meta(response.metadata)  # store metadata
                ctx.stream = response.response_gen
                ctx.input_tokens = input_tokens
                ctx.set_output("", "")
            else:
                ctx.add_doc_meta(response.metadata)  # store metadata
                ctx.input_tokens = input_tokens
                ctx.output_tokens = self.window.core.tokens.from_llama_messages(
                    response.response,
                    [],
                    model.id,
                )  # calc from response
                ctx.set_output(str(response.response), "")
            self.log("Found in metadata: {}".format(response.metadata))
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

        if model is None or not isinstance(model, ModelItem):
            raise Exception("Model config not provided")

        self.log("Chat with index...")
        self.log("Idx: {}, query: {}, model: {}".format(
            idx,
            query,
            model.id,
        ))

        # check if index exists
        if not self.storage.exists(idx):
            raise Exception("Index not prepared")

        service_context = self.window.core.idx.llm.get_service_context(model=model)
        index = self.storage.get(idx, service_context=service_context)  # get index

        # append context from DB
        history = self.context.get_messages(
            ctx.input,
            system_prompt,
            context.history,
        )
        memory = self.get_memory_buffer(history, service_context.llm)
        input_tokens = self.window.core.tokens.from_llama_messages(
            query,
            history,
            model.id,
        )
        chat_engine = index.as_chat_engine(
            chat_mode="context",
            memory=memory,
            system_prompt=system_prompt,
        )
        if stream:
            response = chat_engine.stream_chat(query)
        else:
            response = chat_engine.chat(query)

        if response:
            if stream:
                ctx.stream = response.response_gen
                ctx.input_tokens = input_tokens
                ctx.set_output("", "")
                # no metadata here in agent chat stream response!
            else:
                ctx.add_doc_meta(response.metadata)  # store metadata
                ctx.input_tokens = input_tokens
                ctx.output_tokens = self.window.core.tokens.from_llama_messages(
                    response.response,
                    [],
                    model.id,
                )  # calc from response
                ctx.set_output(str(response.response), "")
                self.log("Found in metadata: {}".format(response.metadata))
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
                streaming=False,
            ).query(query)  # query with default prompt
            if response:
                ctx.add_doc_meta(response.metadata)  # store metadata
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
                streaming=False,
            ).query(query)  # query with default prompt
            if response:
                ctx.add_doc_meta(response.metadata)  # store metadata
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

    def log(self, msg: str):
        """
        Log info message

        :param msg: message
        """
        is_log = False
        if self.window.core.config.has("log.llama") \
                and self.window.core.config.get("log.llama"):
            is_log = True
        self.window.core.debug.info(msg, not is_log)
        if is_log:
            print("[LLAMA-INDEX] {}".format(msg))
        self.window.idx_logger_message.emit(msg)
