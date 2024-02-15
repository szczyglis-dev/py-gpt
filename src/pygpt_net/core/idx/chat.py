#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.27 15:00:00                  #
# ================================================== #

from llama_index.llms import ChatMessage, MessageRole
from llama_index.prompts import ChatPromptTemplate
from llama_index.memory import ChatMemoryBuffer

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

    def call(self, **kwargs) -> bool:
        """
        Call chat or query mode

        :param kwargs: keyword arguments
        :return: True if success
        """
        model = kwargs.get("model", None)
        idx_raw = kwargs.get("idx_raw", False)  # raw mode
        if model is None:  # check if model is provided
            raise Exception("Model config not provided")

        if idx_raw:  # query index (raw mode)
            return self.raw_query(**kwargs)

        # if not raw, check if chat mode is available
        if "chat" in model.llama_index['mode']:
            return self.chat(**kwargs)
        else:
            return self.query(**kwargs)  # if not, use query mode

    def raw_query(self, **kwargs) -> bool:
        """
        Raw query mode

        :param kwargs: keyword arguments
        :return: True if success
        """
        return self.query(**kwargs)

    def query(self, **kwargs) -> bool:
        """
        Query index

        :param kwargs: keyword arguments
        :return: True if success
        """
        ctx = kwargs.get("ctx", CtxItem())
        idx = kwargs.get("idx", "base")
        model = kwargs.get("model", None)
        system_prompt = kwargs.get("system_prompt_raw", None)  # raw system prompt, without plugin ads
        stream = kwargs.get("stream", False)
        query = ctx.input

        # log query
        is_log = False
        if self.window.core.config.has("log.llama") \
                and self.window.core.config.get("log.llama"):
            is_log = True

        if model is None:
            raise Exception("Model config not provided")

        log_msg = "[LLAMA-INDEX] Query index..."
        self.window.core.debug.info(log_msg, not is_log)
        if is_log:
            print(log_msg)

        log_msg = "[LLAMA-INDEX] Idx: {}, query: {}, model: {}".format(
            idx,
            query,
            model.id,
        )
        self.window.core.debug.info(log_msg, not is_log)
        if is_log:
            print(log_msg)

        # check if index exists
        if not self.storage.exists(idx):
            raise Exception("Index not prepared")

        context = self.window.core.idx.llm.get_service_context(model=model)
        index = self.storage.get(idx, service_context=context)  # get index
        input_tokens = self.window.core.tokens.from_llama_messages(
            query,
            [],
            model.id,
        )
        # query index
        tpl = self.get_custom_prompt(system_prompt)
        if tpl is not None:
            log_msg = "[LLAMA-INDEX] Query index with custom prompt: {}...".format(system_prompt)
            self.window.core.debug.info(log_msg, not is_log)
            if is_log:
                print(log_msg)
            response = index.as_query_engine(
                streaming=stream,
                text_qa_template=tpl,
            ).query(query)  # query with custom sys prompt
        else:
            response = index.as_query_engine(
                streaming=stream,
            ).query(query)  # query with default prompt

        if stream:
            ctx.stream = response.response_gen
            ctx.input_tokens = input_tokens
            ctx.set_output("", "")
            return True

        ctx.input_tokens = input_tokens
        ctx.output_tokens = self.window.core.tokens.from_llama_messages(
            response,
            [],
            model.id,
        )  # calc from response
        ctx.set_output(str(response), "")
        return True

    def chat(self, **kwargs) -> bool:
        """
        Chat using index

        :param kwargs: keyword arguments
        :return: True if success
        """
        ctx = kwargs.get("ctx", CtxItem())
        idx = kwargs.get("idx", "base")
        model = kwargs.get("model", None)
        system_prompt = kwargs.get("system_prompt", None)
        stream = kwargs.get("stream", False)
        query = ctx.input

        # log query
        is_log = False
        if self.window.core.config.has("log.llama") \
                and self.window.core.config.get("log.llama"):
            is_log = True

        if model is None:
            raise Exception("Model config not provided")

        log_msg = "[LLAMA-INDEX] Chat with index..."
        self.window.core.debug.info(log_msg, not is_log)
        if is_log:
            print(log_msg)

        log_msg = "[LLAMA-INDEX] Idx: {}, query: {}, model: {}".format(
            idx,
            query,
            model.id,
        )
        self.window.core.debug.info(log_msg, not is_log)
        if is_log:
            print(log_msg)

        # check if index exists
        if not self.storage.exists(idx):
            raise Exception("Index not prepared")

        context = self.window.core.idx.llm.get_service_context(model=model)
        index = self.storage.get(idx, service_context=context)  # get index

        # append context from DB
        history = self.context.get_messages(ctx.input, system_prompt)
        memory = self.get_memory_buffer(history)
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
            ctx.stream = response.response_gen
            ctx.input_tokens = input_tokens
            ctx.set_output("", "")
            return True
        else:
            response = chat_engine.chat(query)

        ctx.input_tokens = input_tokens
        ctx.output_tokens = self.window.core.tokens.from_llama_messages(
            response,
            [],
            model.id,
        )  # calc from response
        ctx.set_output(str(response), "")

        return True

    def get_memory_buffer(self, history: list) -> ChatMemoryBuffer:
        """
        Get memory buffer

        :param history: Memory with chat history
        """
        return ChatMemoryBuffer.from_defaults(chat_history=history)

    def get_custom_prompt(self, prompt: str = None) -> ChatPromptTemplate or None:
        """
        Get custom prompt template if sys prompt is not empty

        :param prompt: system prompt
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
