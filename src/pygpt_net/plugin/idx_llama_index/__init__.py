#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.11 04:00:00                  #
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
            "get_knowledge"
        ]
        self.order = 100
        self.use_locale = True
        self.init_options()

    def init_options(self):
        """Initialize options"""
        prompt = 'ADDITIONAL KNOWLEDGE: I will provide you with additional data about my question. ' \
                 'When it is provided, then use this data as your additional knowledge and use it in your response. ' \
                 'Additional knowledge will be prefixed with an "Additional data:" prefix. ' \
                 'You can also provide a command to query my knowledge database anytime you need any additional data ' \
                 '- to do this, return to me the prepared prompt in JSON format, all in one line, using the following' \
                 ' syntax: ~###~{"cmd": "get_knowledge", "params": {"question": "simple and concrete question here"}}~###~. ' \
                 'Use ONLY this syntax and remember to surround the JSON string with ~###~. DO NOT use any other' \
                 ' syntax. When making query use language that I spoke to you.'
        self.add_option("prompt", "textarea", prompt,
                        "Prompt",
                        "Prompt used for instruct how to use additional data provided from Llama-index",
                        tooltip="Prompt", advanced=True)
        self.add_option("idx", "text", "base",
                        "Indexes to use",
                        "ID's of indexes to use, default: base, "
                        "separate by comma if you want to use more than one index at once",
                        tooltip="Index name")
        self.add_option("ask_llama_first", "bool", False,
                        "Ask Llama-index first",
                        "When enabled, then Llama-index will be asked first, and response will be used as additional "
                        "knowledge in prompt. When disabled, then Llama-index will be asked only when needed.")
        self.add_option("model_query", "combo", "gpt-3.5-turbo",
                        "Model",
                        "Model used for querying Llama-index, default: gpt-3.5-turbo",
                        tooltip="Query model", use="models")

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
        """
        name = event.name
        data = event.data
        ctx = event.ctx

        if name == 'system.prompt':
            data['value'] = self.on_system_prompt(data['value'])
        if name == 'post.prompt':
            data['value'] = self.on_post_prompt(data['value'], ctx)
        elif name == 'cmd.only' or name == 'cmd.execute':
            self.cmd(ctx, data['commands'])

    def log(self, msg: str):
        """
        Log message to console

        :param msg: message to log
        """
        full_msg = '[LLAMA-INDEX] ' + str(msg)
        self.debug(full_msg)
        self.window.ui.status(full_msg)
        print(full_msg)

    def on_system_prompt(self, prompt: str):
        """
        Event: On prepare system prompt

        :param prompt: prompt
        :return: updated prompt
        """
        prompt += "\n" + self.get_option_value("prompt")
        return prompt

    def on_post_prompt(self, prompt: str, ctx: CtxItem):
        """
        Event: On post system prompt

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

    def query(self, question: str):
        """
        Query Llama-index

        :param question: question
        :return: response
        """
        model = "gpt-3.5-turbo"
        idx = self.get_option_value("idx")
        if self.get_option_value("model_query") is not None:
            model = self.get_option_value("model_query")
        indexes = idx.split(",")
        if len(indexes) > 1:
            responses = []
            for index in indexes:
                responses.append(self.window.core.idx.query(question, idx=index.strip(), model=model))
            return "\n".join(responses)
        else:
            return self.window.core.idx.query(question, idx=idx, model=model)

    def cmd(self, ctx: CtxItem, cmds: list):
        """
        Event: On command

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
                    request = {"cmd": item["cmd"]}
                    data = self.query(question)  # send question to Llama-index
                    response = {"request": request, "result": data}
                    ctx.results.append(response)
                    ctx.reply = True
            except Exception as e:
                self.log("Error: " + str(e))
                return
