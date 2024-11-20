#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.20 03:00:00                  #
# ================================================== #

from pygpt_net.plugin.base.plugin import BasePlugin
from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem

from .config import Config


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "voice_control"
        self.name = "Voice Control (inline)"
        self.type = [
            "cmd.inline",
            "audio.control",
        ]
        self.description = "Provide voice control command execution within a conversation."
        self.prefix = "Voice"
        self.input_text = None
        self.allowed_cmds = [
            "voice_cmd",
        ]
        self.order = 100
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

        if name in [
            Event.CMD_SYNTAX_INLINE,  # inline is allowed
            Event.CMD_SYNTAX,
        ]:
            self.cmd_syntax(data)

        elif name in [
            Event.CMD_INLINE,  # inline is allowed
            Event.CMD_EXECUTE,
        ]:
            self.cmd(
                ctx,
                data['commands'],
            )

        elif name in [
            Event.ENABLE,
            Event.DISABLE,
        ]:
            if name == Event.ENABLE:
                if data["value"] == self.id:
                    self.window.controller.plugins.enable("audio_input")

    def prepare_cmd_list(self) -> dict:
        """
        Prepare command list

        :return: command list
        """
        magic_prefix = self.get_option_value("cmd_prefix")
        instruction = self.window.core.access.voice.get_inline_prompt(magic_prefix).strip()
        cmd_syntax = {
            "cmd": "voice_cmd",
            "instruction": instruction,
            "params": [
                {
                    "name": "action",
                    "type": "enum",
                    "required": True,
                    "description": "Voice action",
                    "enum": {
                        "action": self.window.core.access.voice.get_commands(),  # voice cmds list
                    },
                },
                {
                    "name": "args",
                    "type": "text",
                    "required": False,
                    "description": "Voice action arguments",
                }
            ],
            "enabled": True,  # enabled
        }
        return cmd_syntax

    def cmd_syntax(self, data: dict):
        """
        Event: CMD_SYNTAX

        :param data: event data dict
        """
        data['cmd'].append(self.prepare_cmd_list())  # append command

    def cmd(self, ctx: CtxItem, cmds: list):
        """
        Events: CMD_EXECUTE

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

        # prepare voice commands
        voice_commands = []
        available_commands = self.window.core.access.voice.get_commands()
        for cmd in my_commands:
            if cmd["cmd"] == "voice_cmd":
                if "action" not in cmd["params"]:
                    return
                action = cmd["params"]["action"]
                params = ""
                if "args" in cmd["params"]:
                    params = cmd["params"]["args"]
                if action not in available_commands:
                    voice_commands.append({
                        "cmd": "unrecognized",
                        "params": "",
                    })
                    continue
                voice_commands.append({
                    "cmd": action,
                    "params": params,
                })

        # execute voice commands
        self.window.controller.access.voice.handle_commands(voice_commands)
