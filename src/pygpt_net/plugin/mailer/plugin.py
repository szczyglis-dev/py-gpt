#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.15 04:00:00                  #
# ================================================== #

from pygpt_net.plugin.base.plugin import BasePlugin
from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem

from .config import Config
from .runner import Runner
from .worker import Worker

from pygpt_net.utils import trans


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "mailer"
        self.name = "Mailer"
        self.description = "Provides email sending"
        self.prefix = "Email"
        self.type = [
            'email',
        ]
        self.order = 100
        self.allowed_cmds = [
            "send_mail",
            "get_emails",
            "get_email_body",
        ]
        self.use_locale = True
        self.runner = Runner(self)
        self.worker = None
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
        silent = data.get("silent", False)

        if name == Event.CMD_SYNTAX:
            self.cmd_syntax(data)

        elif name == Event.CMD_EXECUTE:
            self.cmd(
                ctx,
                data['commands'],
                silent,
            )

    def cmd_syntax(self, data: dict):
        """
        Event: CMD_SYNTAX

        :param data: event data dict
        """
        for item in self.allowed_cmds:
            if self.has_cmd(item):
                cmd = self.get_cmd(item)
                data['cmd'].append(cmd)  # append command

    def cmd(self, ctx: CtxItem, cmds: list, silent: bool = False):
        """
        Event: CMD_EXECUTE

        :param ctx: CtxItem
        :param cmds: commands dict
        :param silent: silent mode
        """
        is_cmd = False
        force = False
        my_commands = []
        for item in cmds:
            if item["cmd"] in self.allowed_cmds:
                my_commands.append(item)
                is_cmd = True
                if "force" in item and item["force"]:
                    force = True  # call from tool

        if not is_cmd:
            return

        # set state: busy
        if not silent:
            self.cmd_prepare(ctx, my_commands)

        try:
            worker = Worker()
            worker.from_defaults(self)
            worker.cmds = my_commands
            worker.ctx = ctx

            # connect signals
            self.runner.attach_signals(worker.signals)

            if not self.is_async(ctx) and not force:
                worker.run()
                return
            worker.run_async()

        except Exception as e:
            self.error(e)
