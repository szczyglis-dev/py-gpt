#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.29 23:00:00                  #
# ================================================== #

from datetime import datetime

from pygpt_net.plugin.base.plugin import BasePlugin
from pygpt_net.item.ctx import CtxItem
from pygpt_net.core.events import Event

from .config import Config


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "real_time"
        self.name = "Real Time"
        self.type = ["time"]
        self.description = "Appends current time and date to every system prompt."
        self.prefix = "Time"
        self.allowed_cmds = [
            "get_time",
        ]
        self.order = 2
        self.use_locale = True
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

        if name == Event.POST_PROMPT_END:
            silent = False
            if 'silent' in data and data['silent']:
                silent = True
            data['value'] = self.on_system_prompt(
                data['value'],
                silent,
            )

        if name == Event.AGENT_PROMPT:
            silent = False
            if 'silent' in data and data['silent']:
                silent = True
            data['value'] = self.on_agent_prompt(
                data['value'],
                silent,
            )

        elif name == Event.CMD_SYNTAX:
            self.cmd_syntax(data)

        elif name == Event.CMD_EXECUTE:
            self.cmd(
                ctx,
                data['commands'],
            )

    def cmd_syntax(self, data: dict):
        """
        Event: CMD_SYNTAX

        :param data: event data dict
        """
        for option in self.allowed_cmds:
            if self.has_cmd(option):
                data['cmd'].append(self.get_cmd(option))  # append command

    def cmd(self, ctx: CtxItem, cmds: list):
        """
        Event: CMD_EXECUTE

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

        response = None
        for item in my_commands:
            try:
                if item["cmd"] in self.allowed_cmds and self.has_cmd(item["cmd"]):
                    # get time
                    if item["cmd"] == "get_time":
                        time = datetime.now().strftime('%A, %Y-%m-%d %H:%M:%S')
                        response = {
                            "request": {
                                "cmd": item["cmd"]
                            },
                            "result": time,
                        }
            except Exception as e:
                self.error(e)

        if response:
            self.reply(response, ctx)

    def on_system_prompt(self, prompt: str, silent: bool = False) -> str:
        """
        Event: SYSTEM_PROMPT

        :param prompt: prompt
        :param silent: silent mode (no logs)
        :return: updated prompt
        """
        if self.get_option_value("hour") or self.get_option_value("date"):
            if prompt.strip() != "":
                prompt += "\n\n"
            if self.get_option_value("hour") and self.get_option_value("date"):
                prompt += self.get_option_value("tpl").\
                    format(time=datetime.now().strftime('%A, %Y-%m-%d %H:%M:%S'))
            elif self.get_option_value("hour"):
                prompt += self.get_option_value("tpl").\
                    format(time=datetime.now().strftime('%H:%M:%S'))
            elif self.get_option_value("date"):
                prompt += self.get_option_value("tpl").\
                    format(time=datetime.now().strftime('%A, %Y-%m-%d'))
        return prompt

    def on_agent_prompt(self, prompt: str, silent: bool = False) -> str:
        """
        Event: AGENT_PROMPT

        :param prompt: prompt
        :param silent: silent mode (no logs)
        :return: updated prompt
        """
        if self.get_option_value("hour") or self.get_option_value("date"):
            if self.get_option_value("hour") and self.get_option_value("date"):
                prompt = self.get_option_value("tpl").\
                    format(time=datetime.now().strftime('%A, %Y-%m-%d %H:%M:%S')) + "\n\n" + prompt
            elif self.get_option_value("hour"):
                prompt = self.get_option_value("tpl").\
                    format(time=datetime.now().strftime('%H:%M:%S') + "\n\n" + prompt)
            elif self.get_option_value("date"):
                prompt = self.get_option_value("tpl").\
                    format(time=datetime.now().strftime('%A, %Y-%m-%d')) + "\n\n" + prompt
        return prompt


