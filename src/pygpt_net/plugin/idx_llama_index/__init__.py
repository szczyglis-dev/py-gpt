#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.14 15:00:00                  #
# ================================================== #

from pygpt_net.plugin.base import BasePlugin
from pygpt_net.core.dispatcher import Event
from pygpt_net.item.ctx import CtxItem


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "idx_llama_index"
        self.name = "Llama-index (inline)"
        self.description = "Integrates Llama-index storage in any chat"
        self.allowed_cmds = [
            "get_knowledge",
        ]
        self.ignored_modes = [
            "llama_index",
        ]
        self.order = 100
        self.use_locale = True
        self.mode = None  # current mode
        self.init_options()

    def init_options(self):
        """Initialize options"""   # TODO: make better prompt, redefine context
        prompt = 'ADDITIONAL CONTEXT: I will provide you with additional data about my question. ' \
                 'When it is provided, then use this data as your additional knowledge and use it in your response. ' \
                 'Additional context will be prefixed with an "Additional data:" prefix. You can also provide a ' \
                 'command to query my knowledge database anytime you need any additional data - to do this, return ' \
                 'to me the prepared prompt in JSON format, all in one line, using the following syntax: ' \
                 '~###~{"cmd": "get_knowledge", "params": {"question": "simple and concrete question here"}}~###~. ' \
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
            "model_query",
            type="combo",
            value="gpt-3.5-turbo",
            label="Model",
            description="Model used for querying Llama-index, default: gpt-3.5-turbo",
            tooltip="Query model",
            use="models",
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
            data['value'] = self.on_system_prompt(data['value'])

        elif name == Event.INPUT_BEFORE:  # get only mode
            if "mode" in data:
                self.mode = data['mode']

        elif name == Event.POST_PROMPT:
            if self.mode in self.ignored_modes:  # ignore
                return

            # ignore if reply for command or internal
            if ctx.reply or ctx.internal or data["reply"]:
                return

            data['value'] = self.on_post_prompt(
                data['value'],
                ctx
            )

        elif name in [
            Event.CMD_INLINE,
            Event.CMD_EXECUTE,
        ]:
            if self.mode in self.ignored_modes:  # ignore
                return
            if ctx.reply or ctx.internal:
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

    def on_post_prompt(self, prompt: str, ctx: CtxItem) -> str:
        """
        Event: POST_PROMPT

        :param prompt: system prompt
        :param ctx: CtxItem
        :return: updated system prompt
        """
        if not self.get_option_value("ask_llama_first"):
            return prompt

        response = self.query(ctx.input)
        if response is None or len(response) == 0:
            return prompt

        prompt += "\nADDITIONAL KNOWLEDGE: " + response
        return prompt

    def query(self, question: str) -> str:
        """
        Query Llama-index

        :param question: question
        :return: response
        """
        idx = self.get_option_value("idx")
        model = self.window.core.models.from_defaults()
        if self.get_option_value("model_query") is not None:
            model_query = self.get_option_value("model_query")
            if self.window.core.models.has(model_query):
                model = self.window.core.models.get(model_query)
        indexes = idx.split(",")

        # max length of question
        max_len = 1000
        if len(question) > max_len:
            question = question[:max_len]

        if len(indexes) > 1:
            responses = []
            for index in indexes:
                ctx = CtxItem()
                ctx.input = question
                self.window.core.idx.chat.query(
                    ctx=ctx,
                    idx=index.strip(),
                    model=model,
                    stream=False,
                )
                responses.append(ctx.output)
            return "\n".join(responses)
        else:
            ctx = CtxItem()
            ctx.input = question
            self.window.core.idx.chat.query(
                ctx=ctx,
                idx=idx,
                model=model,
                stream=False,
            )
            return ctx.output

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

        for item in my_commands:
            try:
                if item["cmd"] == "get_knowledge":
                    question = item["params"]["question"]
                    request = {
                        "cmd": item["cmd"],
                    }
                    data = self.query(question)  # send question to Llama-index
                    response = {
                        "request": request,
                        "result": data,
                    }
                    ctx.results.append(response)
                    ctx.reply = True
            except Exception as e:
                self.log("Error: " + str(e))
                return

    def log(self, msg: str):
        """
        Log message to console

        :param msg: message to log
        """
        full_msg = '[LLAMA-INDEX] ' + str(msg)
        self.debug(full_msg)
        self.window.ui.status(full_msg)
        if self.is_log():
            print(full_msg)
