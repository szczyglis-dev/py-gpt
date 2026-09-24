#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.24 19:27:00                  #
# ================================================== #

from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem
from pygpt_net.plugin.base.plugin import BasePlugin

from .config import Config


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "jev"
        self.name = "Jev / System One"
        self.description = (
            "Uses TypeSafe AI Jev / System One for bounded structured decisions such as "
            "classification, routing, selection, verification and scoring. Jev exposes Choice, "
            "Score and Noul primitives and returns typed JSON decisions rather than chat text."
        )
        self.prefix = "Jev"
        self.type = ["cmd.inline"]
        self.allowed_cmds = ["jev_evaluate"]
        self.order = 100
        self.use_locale = True
        self.urls = {
            "Documentation": "https://docs.typesafe.ai/api",
            "API keys": "https://console.typesafe.ai/keys",
        }
        self.worker = None
        self.config = Config(self)
        self.init_options()

    def init_options(self):
        """Initialize plugin options."""
        self.config.from_defaults(self)

    def handle(self, event: Event, *args, **kwargs):
        """Handle dispatched event."""
        name = event.name
        data = event.data
        ctx = event.ctx

        if name in (Event.CMD_SYNTAX_INLINE, Event.CMD_SYNTAX):
            self.cmd_syntax(data)
        elif name in (Event.CMD_INLINE, Event.CMD_EXECUTE):
            self.cmd(ctx, data.get("commands", []))

    def cmd_syntax(self, data: dict):
        """Append Jev command syntax."""
        for option in self.allowed_cmds:
            if self.has_cmd(option):
                data["cmd"].append(self.get_cmd(option))

    def cmd(self, ctx: CtxItem, cmds: list):
        """Execute Jev commands."""
        from .worker import Worker

        my_commands = [
            item for item in cmds
            if item.get("cmd") in self.allowed_cmds and self.has_cmd(item.get("cmd"))
        ]
        if not my_commands:
            return

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
