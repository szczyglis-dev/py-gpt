#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.18 00:37:10                  #
# ================================================== #

from pygpt_net.plugin.base.plugin import BasePlugin
from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem

from .config import Config


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "osm"
        self.name = "OpenStreetMap"
        self.description = "Search, geocode, plan routes, and generate static maps using OpenStreetMap services (Nominatim, OSRM, staticmap)."
        self.prefix = "API"
        self.order = 90
        self.allowed_cmds = [
            "osm_geocode",
            "osm_reverse",
            "osm_search",
            "osm_route",
            "osm_staticmap",
            "osm_bbox_map",
            "osm_show_url",
            "osm_route_url",
            "osm_tile",
        ]
        self.use_locale = False
        self.worker = None
        self.config = Config(self)
        self.init_options()

    def init_options(self):
        self.config.from_defaults(self)

    def handle(self, event: Event, *args, **kwargs):
        name = event.name
        data = event.data
        ctx = event.ctx

        if name == Event.CMD_SYNTAX:
            self.cmd_syntax(data)
        elif name == Event.CMD_EXECUTE:
            self.cmd(ctx, data['commands'])

    def cmd_syntax(self, data: dict):
        for option in self.allowed_cmds:
            if self.has_cmd(option):
                data['cmd'].append(self.get_cmd(option))

    def cmd(self, ctx: CtxItem, cmds: list):
        from .worker import Worker

        is_cmd = False
        my_commands = []
        for item in cmds:
            if item["cmd"] in self.allowed_cmds:
                my_commands.append(item)
                is_cmd = True

        if not is_cmd:
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