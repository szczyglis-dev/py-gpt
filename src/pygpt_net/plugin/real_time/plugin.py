#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.15 23:00:00                  #
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
            silent = bool(data.get('silent'))
            data['value'] = self.on_system_prompt(data['value'], silent)

        elif name == Event.AGENT_PROMPT:
            silent = bool(data.get('silent'))
            data['value'] = self.on_agent_prompt(data['value'], silent)

        elif name == Event.CMD_SYNTAX:
            self.cmd_syntax(data)

        elif name == Event.CMD_EXECUTE:
            self.cmd(ctx, data['commands'])

    def cmd_syntax(self, data: dict):
        """
        Event: CMD_SYNTAX

        :param data: event data dict
        """
        append = data['cmd'].append
        for option in self.allowed_cmds:
            if self.has_cmd(option):
                append(self.get_cmd(option))  # append command

    def cmd(self, ctx: CtxItem, cmds: list):
        """
        Event: CMD_EXECUTE

        :param ctx: CtxItem
        :param cmds: commands dict
        """
        my_commands = [item for item in cmds if item.get("cmd") in self.allowed_cmds]
        if not my_commands:
            return

        response = None
        now_str = None

        for item in my_commands:
            try:
                cmd_name = item.get("cmd")
                if cmd_name in self.allowed_cmds and self.has_cmd(cmd_name):
                    if cmd_name == "get_time":
                        if now_str is None:
                            now_str = datetime.now().strftime('%A, %Y-%m-%d %H:%M:%S')
                        response = {
                            "request": {
                                "cmd": cmd_name
                            },
                            "result": now_str,
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
        get_opt = self.get_option_value
        hour = get_opt("hour")
        date = get_opt("date")

        if hour or date:
            if prompt and not prompt.isspace():
                prompt += "\n\n"

            tpl = get_opt("tpl")
            now = datetime.now()

            if hour and date:
                prompt += tpl.format(time=now.strftime('%A, %Y-%m-%d %H:%M:%S'))
            elif hour:
                prompt += tpl.format(time=now.strftime('%H:%M:%S'))
            elif date:
                prompt += tpl.format(time=now.strftime('%A, %Y-%m-%d'))
        return prompt

    def on_agent_prompt(self, prompt: str, silent: bool = False) -> str:
        """
        Event: AGENT_PROMPT

        :param prompt: prompt
        :param silent: silent mode (no logs)
        :return: updated prompt
        """
        get_opt = self.get_option_value
        hour = get_opt("hour")
        date = get_opt("date")

        if hour or date:
            tpl = get_opt("tpl")
            now = datetime.now()

            if hour and date:
                prompt = tpl.format(time=now.strftime('%A, %Y-%m-%d %H:%M:%S')) + "\n\n" + prompt
            elif hour:
                prompt = tpl.format(time=now.strftime('%H:%M:%S') + "\n\n" + prompt)
            elif date:
                prompt = tpl.format(time=now.strftime('%A, %Y-%m-%d')) + "\n\n" + prompt
        return prompt