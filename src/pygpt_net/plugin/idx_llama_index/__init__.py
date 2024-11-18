#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.18 05:00:00                  #
# ================================================== #
import copy
import json

from pygpt_net.plugin.base import BasePlugin
from pygpt_net.core.dispatcher import Event
from pygpt_net.item.ctx import CtxItem

from .worker import Worker
from ...core.bridge import BridgeContext


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "idx_llama_index"
        self.name = "Llama-index (inline)"
        self.description = "Integrates Llama-index storage in any chat"
        self.allowed_cmds = [
            "get_context",
        ]
        self.ignored_modes = [
            "llama_index",
        ]
        self.type = [
            "cmd.inline",
        ]
        self.order = 100
        self.use_locale = True
        self.worker = None
        self.mode = None  # current mode
        self.init_options()

    def init_options(self):
        """Initialize options"""
        prompt = 'ADDITIONAL CONTEXT: I will provide you with additional context about my question. ' \
                 'When it is provided, then use this data as additional context and use it in your response. ' \
                 'Additional context will be prefixed with an "ADDITIONAL CONTEXT:" prefix. You can also provide a ' \
                 'command to query my context database anytime you need any additional context - to do this, return ' \
                 'to me the prepared prompt in JSON format, all in one line, using the following syntax: ' \
                 '~###~{"cmd": "get_context", "params": {"query": "<simple question here>"}}~###~. ' \
                 'Use ONLY this syntax and remember to surround the JSON string with ~###~. DO NOT use any other ' \
                 'syntax. When making query use language that I spoke to you.'

        self.add_option(
            "prompt",
            type="textarea",
            value=prompt,
            label="Prompt",
            description="Prompt used for instruct how to use additional data provided from Llama-index",
            tooltip="Prompt",
            advanced=True,
        )
        self.add_option(
            "idx",
            type="text",
            value="base",
            label="Indexes to use",
            description="ID's of indexes to use, default: base, separate by comma if you want to use "
                        "more than one index at once",
            tooltip="Index name",
        )
        self.add_option(
            "ask_llama_first",
            type="bool",
            value=False,
            label="Ask Llama-index first",
            description="When enabled, then Llama-index will be asked first, and response will be used "
                        "as additional knowledge in prompt. When disabled, then Llama-index will be "
                        "asked only when needed.",
        )
        self.add_option(
            "prepare_question",
            type="bool",
            value=False,
            label="Auto-prepare question before asking Llama-index first",
            description="When enabled, then question will be prepared before asking Llama-index first to create"
                        "best question for Llama-index.",
        )
        self.add_option(
            "model_prepare_question",
            type="combo",
            use="models",
            value="gpt-3.5-turbo",
            label="Model for question preparation",
            description="Model used to prepare question before asking Llama-index, default: gpt-3.5-turbo",
            tooltip="Model",
        )
        self.add_option(
            "prepare_question_max_tokens",
            type="int",
            value=500,
            label="Max output tokens for question preparation",
            description="Max tokens in output when preparing question before asking Llama-index",
            min=1,
            max=None,
        )
        self.add_option(
            "model_query",
            type="combo",
            value="gpt-3.5-turbo",
            label="Model",
            description="Model used for querying Llama-index, default: gpt-3.5-turbo",
            tooltip="Query model",
            use="models",
        )
        self.add_option(
            "max_question_chars",
            type="int",
            value=1000,
            label="Max characters in question",
            description="Max characters in question when querying Llama-index, 0 = no limit",
            min=0,
            max=None,
        )
        self.add_option(
            "append_meta",
            type="bool",
            value=False,
            label="Append metadata to context",
            description="If enabled, then metadata from Llama-index will be appended to additional context",
        )
        self.add_option(
            "syntax_prepare_question",
            type="textarea",
            value='Simplify the question into a short query for retrieving information from a vector store.',
            label="Prompt for question preparation",
            description="System prompt for question preparation",
            advanced=True,
        )
        self.add_cmd(
            "get_context",
            instruction="get additional context for a given query",
            params=[
                {
                    "name": "query",
                    "type": "str",
                    "description": "query to retrieve additional context for",
                    "required": True,
                },
            ],
            enabled=True,
            description="If enabled, model will be able to get additional context for a given query",
        )

    def setup(self) -> dict:
        """
        Return available config options

        :return: config options
        """
        return self.options

    def attach(self, window):
        """
        Attach window

        :param window: Window instance
        """
        self.window = window

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

        elif name == Event.POST_PROMPT:
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
        response = self.window.core.bridge.quick_call(
            context=bridge_context,
        )
        if response is not None and response != "":
            prepared_question = response
        return prepared_question


    def on_post_prompt(self, prompt: str, ctx: CtxItem) -> str:
        """
        Event: POST_PROMPT

        :param prompt: system prompt
        :param ctx: CtxItem
        :return: updated system prompt
        """
        if (not self.get_option_value("ask_llama_first")
                or self.window.controller.agent.enabled()):
            return prompt

        question = ctx.input
        if self.get_option_value("prepare_question"):
            question = self.prepare_question(ctx)
            if question == "":
                return prompt

        self.log("Querying Llama-index for: " + question)

        response, doc_ids, metas = self.query(question)
        if response is None or len(response) == 0:
            self.log("No additional context. Aborting.")
            return prompt
        else:
            ctx.doc_ids = doc_ids

        prompt += "\nADDITIONAL CONTEXT: " + response
        return prompt

    def query(self, question: str) -> (str, list, list):
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

    def cmd(self, ctx: CtxItem, cmds: list):
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

        try:
            # worker
            self.worker = Worker()
            self.worker.plugin = self
            self.worker.cmds = my_commands
            self.worker.ctx = ctx

            # signals (base handlers)
            self.worker.signals.finished_more.connect(self.handle_finished_more)
            self.worker.signals.log.connect(self.handle_log)
            self.worker.signals.debug.connect(self.handle_debug)
            self.worker.signals.status.connect(self.handle_status)
            self.worker.signals.error.connect(self.handle_error)

            # check if async allowed
            if not self.window.core.dispatcher.async_allowed(ctx):
                self.worker.run()
                return

            # start
            self.window.threadpool.start(self.worker)

        except Exception as e:
            self.error(e)

    def log(self, msg: str):
        """
        Log message to console

        :param msg: message to log
        """
        if self.is_threaded():
            return
        full_msg = '[LLAMA-INDEX] ' + str(msg)
        self.debug(full_msg)
        self.window.ui.status(full_msg.replace("\n", " "))
        if self.is_log():
            print(full_msg)
        self.window.idx_logger_message.emit(msg)
