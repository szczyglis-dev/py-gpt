#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.14 13:00:00                  #
# ================================================== #

from llama_index.llms import ChatMessage, MessageRole
from llama_index.prompts import ChatPromptTemplate
from llama_index.memory import ChatMemoryBuffer

from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.model import ModelItem
from .context import Context


class Chat:
    def __init__(self, window=None, storage=None):
        """
        Query index core

        :param window: Window instance
        """
        self.window = window
        self.storage = storage
        self.context = Context(window)
        self.input_tokens = 0
        self.max_tokens = 0

    def call(self, ctx: CtxItem, idx: str, model: ModelItem, sys_prompt: str = None, stream: bool = False) -> any:
        """
        Call chat or query mode

        :param ctx: Context item
        :param idx: Index name
        :param model: Model item
        :param sys_prompt: System prompt
        :param stream: Stream mode
        :return: Response or bool
        """
        # check if chat mode is available
        if "chat" in model.llama_index['mode']:
            return self.chat(ctx, idx, model, sys_prompt, stream)
        else:
            # if not, use query mode
            return self.query(ctx.input, idx, model, sys_prompt)

    def query(self, query, idx: str, model: ModelItem, sys_prompt: str = None) -> str:
        """
        Query using index

        :param query: Query string
        :param idx: Index name
        :param model: Model item
        :param sys_prompt: System prompt
        :return: Response
        """
        # log query
        is_log = False
        if self.window.core.config.has("llama.log") and self.window.core.config.get("llama.log"):
            is_log = True

        if is_log:
            print("[LLAMA-INDEX] Query index...")
            print("[LLAMA-INDEX] Idx: {}, query: {}, model: {}".format(idx, query, model.id))

        # check if index exists
        if not self.storage.exists(idx):
            raise Exception("Index not prepared")
        index = self.storage.get(idx, model=model)  # get index

        # query index
        tpl = self.get_custom_prompt(sys_prompt)
        if tpl is not None:
            if is_log:
                print("[LLAMA-INDEX] Query index with custom prompt: {}...".format(sys_prompt))
            response = index.as_query_engine(
                text_qa_template=tpl
            ).query(query)  # query with custom sys prompt
        else:
            response = index.as_query_engine().query(query)  # query with default prompt
        return str(response)

    def chat(self, ctx: CtxItem, idx: str, model: ModelItem, sys_prompt: str = None, stream: bool = False) -> bool:
        """
        Chat using index

        :param ctx: Context item
        :param idx: Index name
        :param model: Model item
        :param sys_prompt: System prompt
        :param stream: Stream response
        :return: True if success
        """
        query = ctx.input
        self.input_tokens = 0

        # log query
        is_log = False
        if self.window.core.config.has("llama.log") and self.window.core.config.get("llama.log"):
            is_log = True

        if is_log:
            print("[LLAMA-INDEX] Chat with index...")
            print("[LLAMA-INDEX] Idx: {}, query: {}, model: {}".format(idx, query, model.id))

        # check if index exists
        if not self.storage.exists(idx):
            raise Exception("Index not prepared")
        index = self.storage.get(idx, model=model)  # get index

        # append context from DB
        history = self.context.get_messages(ctx.input, sys_prompt)
        memory = ChatMemoryBuffer.from_defaults(chat_history=history)
        self.input_tokens = self.window.core.tokens.from_llama_messages(query, history, model.id)
        chat_engine = index.as_chat_engine(
            chat_mode="context",
            memory=memory,
            system_prompt=sys_prompt,
        )
        if stream:
            response = chat_engine.stream_chat(query)
            ctx.stream = response.response_gen
            ctx.input_tokens = self.input_tokens
            ctx.set_output("", "")
            return True
        else:
            response = chat_engine.chat(query)

        ctx.input_tokens = self.input_tokens
        ctx.output_tokens = self.window.core.tokens.from_llama_messages(response, [], model.id)  # calc from response
        ctx.set_output(str(response), "")

        return True

    def get_custom_prompt(self, prompt: str = None) -> ChatPromptTemplate or None:
        """
        Get custom prompt template if sys prompt is not empty

        :param prompt: System prompt
        :return: ChatPromptTemplate
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