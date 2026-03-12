#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : PYGPT Contributors                   #
# Updated Date: 2026.03.11 00:00:00                  #
# ================================================== #

from pygpt_net.plugin.base.plugin import BasePlugin
from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem

from .config import Config


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "cmd_app_launcher"
        self.name = "App Launcher"
        self.type = [
            "cmd",
        ]
        self.description = (
            "Launch, close, and control applications on your system using voice "
            "or text commands. Includes media playback controls and volume management."
        )
        self.prefix = "AppLauncher"
        self.allowed_cmds = [
            "app_launch",
            "app_close",
            "app_list_running",
            "app_open_url",
            "app_list_installed",
            "media_play_pause",
            "media_next_track",
            "media_prev_track",
            "volume_set",
            "volume_mute_toggle",
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

        if name == Event.CMD_SYNTAX:
            self.cmd_syntax(data)

        elif name == Event.CMD_EXECUTE:
            self.cmd(
                ctx,
                data["commands"],
            )

    def cmd_syntax(self, data: dict):
        """
        Event: CMD_SYNTAX

        :param data: event data dict
        """
        for item in self.allowed_cmds:
            if self.has_cmd(item):
                cmd = self.get_cmd(item)
                data["cmd"].append(cmd)

    def cmd(self, ctx: CtxItem, cmds: list):
        """
        Event: CMD_EXECUTE

        :param ctx: CtxItem
        :param cmds: commands dict
        """
        from .worker import Worker

        is_cmd = False
        force = False
        my_commands = []
        for item in cmds:
            if item["cmd"] in self.allowed_cmds:
                my_commands.append(item)
                is_cmd = True
                if "force" in item and item["force"]:
                    force = True

        if not is_cmd:
            return

        # set state: busy
        self.cmd_prepare(ctx, my_commands)

        try:
            worker = Worker()
            worker.from_defaults(self)
            worker.cmds = my_commands
            worker.ctx = ctx

            if not self.is_async(ctx) and not force:
                worker.run()
                return
            worker.run_async()

        except Exception as e:
            self.error(e)
