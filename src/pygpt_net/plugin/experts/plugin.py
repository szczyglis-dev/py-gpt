#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.11 23:55:00                  #
# ================================================== #

from PySide6.QtCore import Slot

from pygpt_net.core.events import Event
from pygpt_net.core.types import MODE_AGENT, MODE_EXPERT, TOOL_EXPERT_CALL_NAME
from pygpt_net.item.ctx import CtxItem
from pygpt_net.plugin.base.plugin import BasePlugin

from .config import Config


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "experts"
        self.name = "Experts (inline)"
        self.description = "Enables inline experts in current mode."
        self.prefix = "Experts"
        # expert_call is a regular inline command tool. In dedicated Experts and
        # legacy Agent modes the controller activates this plugin implicitly.
        self.type = ["expert", "cmd.inline"]
        self.allowed_cmds = [TOOL_EXPERT_CALL_NAME]
        self.order = 9998
        self.use_locale = True
        self.worker = None
        self.config = Config(self)
        self.init_options()

    def init_options(self):
        self.config.from_defaults(self)

    def handle(self, event: Event, *args, **kwargs):
        name = event.name
        data = event.data
        ctx = event.ctx

        if name in (Event.CMD_SYNTAX, Event.CMD_SYNTAX_INLINE):
            self.cmd_syntax(data)
            return

        if name in (Event.CMD_EXECUTE, Event.CMD_INLINE):
            self.cmd(ctx, data.get("commands", []))
            return

        if name == Event.SYSTEM_PROMPT:
            # Dedicated Experts/legacy Agent prompts are composed by the agent
            # controller. The plugin prompt hook is only for inline Experts.
            mode = self.window.core.config.get("mode")
            if mode in (MODE_AGENT, MODE_EXPERT):
                return
            if data.get("is_expert"):
                return  # never recursively expose Experts inside an Expert
            data["value"] = self.on_system_prompt(data.get("value", ""))

    def cmd_syntax(self, data: dict):
        """Advertise expert_call exactly like any other plugin tool."""
        existing = {
            str(item.get("cmd") or "")
            for item in data.get("cmd", [])
            if isinstance(item, dict)
        }
        for item in self.window.core.experts.get_functions():
            if item.get("cmd") not in existing:
                data.setdefault("cmd", []).append(item)

    def cmd(self, ctx: CtxItem, cmds: list):
        """Execute expert_call through the standard plugin result lifecycle."""
        from pygpt_net.core.experts.worker import ExpertWorker

        my_commands = [
            item for item in (cmds or [])
            if item.get("cmd") in self.allowed_cmds
        ]
        if not my_commands:
            return

        self.cmd_prepare(ctx, my_commands)
        try:
            worker = ExpertWorker()
            worker.from_defaults(self)
            worker.signals.event.connect(self.handle_event)
            worker.signals.event_sync.connect(self.handle_event_sync)
            worker.cmds = my_commands
            worker.ctx = ctx
            self.worker = worker

            if not self.is_async(ctx):
                worker.run()
                return
            worker.run_async()
        except Exception as e:
            self.error(e)

    @Slot(object)
    def handle_event(self, event):
        """Forward headless Agents v2 local-tool events onto the Qt thread."""
        if not self.window.controller.kernel.stopped():
            self.window.dispatch(event)

    @Slot(object, object)
    def handle_event_sync(self, event, done):
        """Run a worker prompt hook on the Qt thread and release the worker."""
        try:
            if not self.window.controller.kernel.stopped():
                self.window.dispatch(event)
        finally:
            done.set()

    def on_system_prompt(self, prompt: str) -> str:
        if prompt is not None and prompt.strip() != "":
            prompt += "\n\n"
        return (prompt or "") + self.window.core.experts.get_prompt()
