#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.06.30 02:00:00                  #
# ================================================== #

import json
from typing import Tuple, Dict, List

from pygpt_net.core.types import (
    MODE_LLAMA_INDEX,
)
from pygpt_net.plugin.base.plugin import BasePlugin
from pygpt_net.core.events import Event, KernelEvent
from pygpt_net.item.ctx import CtxItem
from pygpt_net.core.bridge.context import BridgeContext

from .config import Config
from .worker import Worker

class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "idx_llama_index"
        self.name = "Llama-index (inline)"
        self.description = "Integrates Llama-index storage in any chat"
        self.prefix = "Idx"
        self.allowed_cmds = [
            "get_context",
        ]
        self.ignored_modes = [
            MODE_LLAMA_INDEX,
        ]
        self.type = [
            "cmd.inline",
        ]
        self.order = 100
        self.use_locale = True
        self.worker = None
        self.mode = None  # current mode
        self.config = Config(self)
        self.init_options()

    def init_options(self):
        """Initialize options"""
        self.config.from_defaults(self)

    def handle(self, event: Event, *args, **kwargs):
        """
        Handle dispatched event

        :param event: event object
        :param args: args
        :param kwargs: kwargs
        """
        name = event.name
        data = event.data
        ctx = event.ctx

        # ignore events in llama_index mode
        if name == Event.SYSTEM_PROMPT:
            if self.mode in self.ignored_modes:  # ignore
                return
            # data['value'] = self.on_system_prompt(data['value'])

        elif name == Event.INPUT_BEFORE:  # get only mode
            if "mode" in data:
                self.mode = data['mode']

        elif name == Event.POST_PROMPT_END:
            if self.mode in self.ignored_modes:  # ignore
                return

            # ignore if reply for command or internal
            if ctx.reply or data["reply"]:
                return

            data['value'] = self.on_post_prompt(
                data['value'],
                ctx,
            )

        elif name in [
            Event.CMD_SYNTAX,
            Event.CMD_SYNTAX_INLINE,
        ]:
            if self.mode in self.ignored_modes:  # ignore
                return

            self.cmd_syntax(data)

        elif name in [
            Event.CMD_INLINE,
            Event.CMD_EXECUTE,
        ]:
            if self.mode in self.ignored_modes:  # ignore
                return

            if ctx.reply:
                return

            self.cmd(
                ctx,
                data['commands'],
            )
        elif name == Event.SETTINGS_CHANGED:
            self.refresh_option("idx")  # update indexes list

        elif name == Event.MODELS_CHANGED:
            # update models list
            self.refresh_option("model_prepare_question")
            self.refresh_option("model_query")

    def on_system_prompt(self, prompt: str) -> str:
        """
        Event: SYSTEM_PROMPT

        :param prompt: prompt
        :return: updated prompt
        """
        prompt += "\n" + self.get_option_value("prompt")
        return prompt

    def cmd_syntax(self, data: dict):
        """
        Event: CMD_SYNTAX

        :param data: event data dict
        """
        for option in self.allowed_cmds:
            if not self.has_cmd(option):
                continue
            data['cmd'].append(self.get_cmd(option))  # append command

    def prepare_question(self, ctx: CtxItem) -> str:
        """
        Prepare query for Llama-index

        :param ctx: CtxItem
        :return: prepared question for Llama-index
        """
        prepared_question = ""
        sys_prompt = self.get_option_value("syntax_prepare_question")
        self.log("Preparing context question for Llama-index...")

        # get model
        model = self.window.core.models.from_defaults()
        tmp_model = self.get_option_value("model_prepare_question")
        if self.window.core.models.has(tmp_model):
            model = self.window.core.models.get(tmp_model)

        tmp_ctx = CtxItem()  # use copy of original context
        tmp_ctx.from_dict(ctx.to_dict())

        bridge_context = BridgeContext(
            ctx=tmp_ctx,
            prompt=tmp_ctx.input,
            system_prompt=sys_prompt,
            model=model,
            max_tokens=self.get_option_value("prepare_question_max_tokens"),
            temperature=0.0,
        )
        event = KernelEvent(KernelEvent.CALL, {
            'context': bridge_context,
            'extra': {},
        })
        self.window.dispatch(event)
        response = event.data.get('response')
        if response is not None and response != "":
            prepared_question = response
        return prepared_question

    def get_from_retrieval(self, query: str) -> str:
        """
        Get response from retrieval

        :param query: query
        :return: response
        """
        idx = self.get_option_value("idx")
        indexes = idx.split(",")
        response = ""
        for index in indexes:
            response = self.window.core.idx.chat.query_retrieval(query, index)
            if response is not None and response != "":
                break
        return response

    def on_post_prompt(self, prompt: str, ctx: CtxItem) -> str:
        """
        Event: POST_PROMPT

        :param prompt: system prompt
        :param ctx: CtxItem
        :return: updated system prompt
        """
        if (not self.get_option_value("ask_llama_first")
                or self.window.controller.agent.legacy.enabled()):
            return prompt

        question = ctx.input
        if self.get_option_value("prepare_question"):
            question = self.prepare_question(ctx)
            if question == "":
                return prompt

        self.log("Querying Llama-index for: " + question)

        # at first, try to get from retrieval
        response = self.get_from_retrieval(question)
        if response is not None and response != "":
            self.log("Found using retrieval...")
            return prompt + "\nADDITIONAL CONTEXT: " + response

        response, doc_ids, metas = self.query(question)
        if response is None or len(response) == 0:
            self.log("No additional context. Aborting.")
            return prompt
        else:
            ctx.doc_ids = doc_ids

        prompt += "\nADDITIONAL CONTEXT: " + response
        return prompt

    def query(self, question: str) -> Tuple[str, list, list]:
        """
        Query Llama-index

        :param question: question
        :return: response, list of document ids, list of metadata
        """
        doc_ids = []
        metas = []
        idx = self.get_option_value("idx")
        model = self.window.core.models.from_defaults()

        if self.get_option_value("model_query") is not None:
            model_query = self.get_option_value("model_query")
            if self.window.core.models.has(model_query):
                model = self.window.core.models.get(model_query)

        # get indexes
        indexes = idx.split(",")

        # max length of question for Llama-index
        max_len = self.get_option_value("max_question_chars")
        if max_len > 0:
            if len(question) > max_len:
                question = question[:max_len]

        # query multiple indexes
        if len(indexes) > 1:
            responses = []
            for index in indexes:
                ctx = CtxItem()  # tmp ctx
                ctx.input = question
                bridge_context = BridgeContext(
                    ctx=ctx,
                    idx=index.strip(),
                    model=model,
                    stream=False,
                )
                self.window.core.idx.chat.query(
                    context=bridge_context,
                )
                if ctx.index_meta:
                    doc_ids.append(ctx.index_meta)
                    metas.append(ctx.index_meta)
                    self.append_meta_to_response(ctx)

                self.log("Using additional context")
                responses.append(ctx.output)

            return "\n---\n".join(responses), doc_ids, metas

        # query single index
        else:
            ctx = CtxItem()  # tmp ctx
            ctx.input = question
            bridge_context = BridgeContext(
                ctx=ctx,
                idx=idx,
                model=model,
                stream=False,
            )
            self.window.core.idx.chat.query(
                context=bridge_context,
            )
            if ctx.index_meta:
                doc_ids.append(ctx.index_meta)
                metas.append(ctx.index_meta)
                self.append_meta_to_response(ctx)

            self.log("Using additional context")
            return ctx.output, doc_ids, metas  # tmp ctx, llama doc_ids, meta

    def append_meta_to_response(self, ctx: CtxItem):
        """
        Append metadata from Llama-index to context response

        :param ctx: CtxItem
        """
        meta = None
        if ctx.index_meta is not None and isinstance(ctx.index_meta, dict):
            meta = json.dumps(ctx.index_meta)
        if self.get_option_value("append_meta") and meta:
            ctx.output += "\n--------------------------------\nMetadata: " + meta

    def cmd(self, ctx: CtxItem, cmds: List[Dict]):
        """
        Events: CMD_INLINE, CMD_EXECUTE

        :param ctx: CtxItem
        :param cmds: commands dict
        """
        is_cmd = False
        my_commands = []
        for item in cmds:
            if item["cmd"] in self.allowed_cmds:
                my_commands.append(item)
                is_cmd = True

        if not is_cmd:
            return

        # set state: busy
        self.cmd_prepare(ctx, my_commands)

        try:
            worker = Worker()
            worker.from_defaults(self)
            worker.cmds = my_commands
            worker.ctx = ctx
            if not self.is_async(ctx):
                worker.run()
                return
            worker.run_async()

        except Exception as e:
            self.error(e)

    def log(self, msg: str):
        """
        Log message to console

        :param msg: message to log
        """
        if self.is_threaded():
            return
        super(Plugin, self).log(msg)
        self.window.idx_logger_message.emit(msg)
