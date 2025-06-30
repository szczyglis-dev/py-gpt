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

from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_AGENT_LLAMA,
    MODE_ASSISTANT,
    MODE_AUDIO,
    MODE_CHAT,
    MODE_LANGCHAIN,
    MODE_LLAMA_INDEX,
    MODE_VISION,
    MODE_RESEARCH,
)
from pygpt_net.plugin.base.plugin import BasePlugin
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.item.model import ModelItem
from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem

from .config import Config


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "openai_dalle"
        self.name = "DALL-E 3: Image generation"
        self.description = "Integrates DALL-E 3 image generation with any chat"
        self.prefix = "DALL-E"
        self.type = [
            "cmd.inline",
        ]
        self.allowed_modes = [
            MODE_CHAT,
            MODE_LANGCHAIN,
            MODE_VISION,
            MODE_LLAMA_INDEX,
            MODE_ASSISTANT,
            MODE_AGENT,
            MODE_AUDIO,
            MODE_RESEARCH,
        ]
        self.allowed_cmds = [
            "image",
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

        if name == Event.SYSTEM_PROMPT:
            if self.is_native_cmd():  # only if native commands are disabled, otherwise use commands only
                return

            mode = ""
            if "mode" in data:
                mode = data["mode"]
            if mode not in self.allowed_modes:
                return
            data['value'] = self.on_system_prompt(data['value'])

        elif name in [
            Event.CMD_SYNTAX_INLINE,  # inline is allowed
            Event.CMD_SYNTAX,
        ]:
            if not self.is_native_cmd() and "force" not in data:  # only if native commands are enabled, otherwise use prompt only
                return

            self.cmd_syntax(data)

        elif name in [
            Event.CMD_INLINE,
            Event.CMD_EXECUTE,
        ]:
            self.cmd(
                ctx,
                data['commands'],
            )

        elif name == Event.MODELS_CHANGED:
            # update models list
            self.refresh_option("model")

    def cmd_syntax(self, data: dict):
        """
        Event: CMD_SYNTAX or CMD_SYNTAX_INLINE

        :param data: event data dict
        """
        for option in self.allowed_cmds:
            if not self.has_cmd(option):
                continue
            data['cmd'].append(self.get_cmd(option))  # append command

    def on_system_prompt(self, prompt: str) -> str:
        """
        Event: SYSTEM_PROMPT

        :param prompt: prompt
        :return: updated prompt
        """
        prompt += "\n" + self.get_option_value("prompt")
        return prompt

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
                if item["cmd"] == "image":
                    query = item["params"]["query"]
                    # if internal call (ctx.internal = True), then re-send OK response
                    # if not internal call, then append image to chat only
                    model = ModelItem()
                    model.id = "dall-e-3"
                    bridge_context = BridgeContext(
                        ctx=ctx,
                        mode="image",  # fake mode, not-img mode
                        model=model,  # model instance
                        prompt=query,
                    )
                    extra = {
                        "num": 1,  # force 1 image if dall-e-3 model is used
                        "inline": True, # force inline mode
                    }
                    sync = False
                    if self.window.core.config.get("mode") == MODE_AGENT_LLAMA:
                        sync = True
                    self.window.core.gpt.image.generate(bridge_context, extra, sync)  # force inline mode, async call
            except Exception as e:
                self.log("Error: " + str(e))
                return
