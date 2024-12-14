#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 22:00:00                  #
# ================================================== #

from pygpt_net.plugin.base.plugin import BasePlugin
from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem
from .config import Config


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "agent"
        self.name = "Autonomous Agent (inline)"
        self.description = "Enables inline autonomous mode (Agent) in current mode. " \
                           "WARNING: Please use with caution - this mode, when connected with other plugins, " \
                           "may produce unexpected results!"
        self.prefix = "Agent"
        self.type = [
            "agent",
            "cmd.inline",
        ]
        self.order = 9998
        self.use_locale = True
        self.config = Config(self)
        self.init_options()

    def init_options(self):
        """Initialize options"""
        self.config.from_defaults(self)

    def is_allowed(self) -> bool:
        """
        Check if plugin is allowed to run

        :return: True if plugin is allowed to run
        """
        return self.window.core.config.get("mode") != "agent"  # check global mode

    def handle(self, event: Event, *args, **kwargs):
        """
        Handle dispatched event

        :param event: event object
        :param args: event args
        :param kwargs: event kwargs
        """
        name = event.name
        data = event.data
        ctx = event.ctx

        always_events = [
            Event.FORCE_STOP,
            Event.PLUGIN_SETTINGS_CHANGED,
            Event.ENABLE,
            Event.DISABLE
        ]

        if not self.is_allowed() and name != Event.DISABLE:
            return

        if name not in always_events and not self.is_active_prompt():
            return

        if name == Event.CTX_BEFORE:
            self.on_ctx_before(ctx)

        elif name == Event.CTX_AFTER:
            self.on_ctx_after(ctx)

        elif name == Event.CTX_END:
            self.on_ctx_end(ctx)

        elif name == Event.USER_SEND:
            self.on_user_send(data['value'])

        elif name == Event.FORCE_STOP:
            self.on_stop()

        elif name == Event.SYSTEM_PROMPT:
            data['value'] = self.on_system_prompt(data['value'])

        elif name == Event.INPUT_BEFORE:
            data['value'] = self.on_input_before(data['value'])

        elif name in [
            Event.ENABLE,
            Event.DISABLE,
        ]:
            if data['value'] == self.id:
                self.window.controller.agent.legacy.update()  # update agent status bar

        elif name == Event.PLUGIN_SETTINGS_CHANGED:
            self.window.controller.agent.legacy.update()  # update agent status bar

        elif name in [
            Event.CMD_INLINE,
            Event.CMD_EXECUTE,
        ]:
            if self.get_option_value("auto_stop"):
                self.cmd(
                    ctx,
                    data['commands'],
                )

    def is_active_prompt(self) -> bool:
        """
        Check if active prompt is enabled

        :return: True if active prompt is enabled
        """
        for item in self.get_option_value("prompts"):
            if item["enabled"]:
                return True
        return False

    def on_system_prompt(self, prompt: str) -> str:
        """
        Event: SYSTEM_PROMPT

        :param prompt: prompt
        :return: updated prompt
        """
        pre_prompt = ("YOU ARE NOW AN AUTONOMOUS AGENT AND YOU ARE ENTERING NOW INTO AGENT MODE.\n"
                      "Use below instructions in every agent run iteration:\n\n")
        return pre_prompt + self.window.controller.agent.legacy.on_system_prompt(
            prompt,
            append_prompt=self.get_first_active_prompt(),
            auto_stop=self.get_option_value("auto_stop"),
        )

    def on_input_before(self, prompt: str) -> str:
        """
        Event: INPUT_BEFORE

        :param prompt: prompt
        :return: updated prompt
        """
        return self.window.controller.agent.legacy.on_input_before(prompt)

    def cmd(self, ctx: CtxItem, cmds: list):
        """
        Events: CMD_INLINE, CMD_EXECUTE

        :param ctx: CtxItem
        :param cmds: commands dict
        """
        self.window.controller.agent.legacy.cmd(ctx, cmds)  # force execute

    def on_stop(self):
        """
        Event: FORCE_STOP
        """
        self.window.controller.agent.legacy.on_stop()  # force stop

    def on_user_send(self, text: str):
        """
        Event: USER_SEND

        :param text: text
        """
        self.window.controller.agent.legacy.on_user_send(text)

    def on_ctx_end(self, ctx: CtxItem):
        """
        Event: CTX_END

        :param ctx: CtxItem
        """
        self.window.controller.agent.legacy.on_ctx_end(
            ctx,
            iterations=int(self.get_option_value("iterations")),
        )

    def on_ctx_before(self, ctx: CtxItem):
        """
        Event: CTX_BEFORE

        :param ctx: CtxItem
        """
        self.window.controller.agent.legacy.on_ctx_before(
            ctx,
            reverse_roles=self.get_option_value("reverse_roles"),
        )

    def on_ctx_after(self, ctx: CtxItem):
        """
        Event: CTX_AFTER

        :param ctx: CtxItem
        """
        self.window.controller.agent.legacy.on_ctx_after(ctx)

    def get_first_active_prompt(self) -> str:
        """
        Get first active prompt from prompts list

        :return: system prompt
        """
        for item in self.get_option_value("prompts"):
            if item["enabled"]:
                return item["prompt"]
        return ""
