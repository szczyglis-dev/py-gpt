#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.23 07:00:00                  #
# ================================================== #

import platform

from pygpt_net.plugin.base.plugin import BasePlugin
from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem

from .config import Config
from .docker import Docker
from .output import Output
from .runner import Runner

from pygpt_net.utils import trans


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "cmd_system"
        self.name = "System"
        self.description = "Provides integration with OS"
        self.prefix = "OS"
        self.type = [
            'os',
        ]
        self.order = 100

        # Core command(s)
        self.winapi_cmds = [
            # Windows window/query
            "win_list",
            "win_find",
            "win_children",
            "win_foreground",
            "win_rect",
            "win_get_state",
            # Window control
            "win_focus",
            "win_move_resize",
            "win_minimize",
            "win_maximize",
            "win_restore",
            "win_close",
            "win_show",
            "win_hide",
            "win_always_on_top",
            "win_set_opacity",
            # Screenshots
            "win_screenshot",
            "win_area_screenshot",
            # Clipboard / input / cursor / monitors
            "win_clipboard_get",
            "win_clipboard_set",
            "win_cursor_get",
            "win_cursor_set",
            "win_keys_text",
            "win_keys_send",
            "win_click",
            "win_drag",
            "win_monitors",
        ]
        self.allowed_cmds = [
            "sys_exec",
        ] + self.winapi_cmds

        self.use_locale = True
        self.docker = Docker(self)
        self.runner = Runner(self)
        self.output = Output(self)
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

        elif name == Event.TOOL_OUTPUT_RENDER:
            if data['tool'] == self.id:
                data['html'] = self.output.handle(ctx, data['content'])

    def cmd_syntax(self, data: dict):
        """
        Event: CMD_SYNTAX

        :param data: event data dict
        """
        # get current working directory
        os_name = self.window.core.platforms.get_as_string(env_suffix=False)
        cwd = self.window.core.config.get_user_dir('data')
        is_windows = (platform.system() == "Windows")
        winapi_enabled = self.get_option_value("winapi_enabled")

        for item in self.allowed_cmds:
            # Gate WinAPI commands to Windows platform (and enabled flag)
            if item in self.winapi_cmds:
                if not is_windows or not winapi_enabled:
                    continue

            if self.has_cmd(item):
                cmd = self.get_cmd(item)
                # Keep original sys_exec instruction enhancement
                if self.get_option_value("auto_cwd") and item == "sys_exec":
                    cmd["instruction"] += "\nIMPORTANT: ALWAYS use absolute (not relative) path when passing " \
                                          "ANY command to \"command\" param. Current workdir is: {cwd}. " \
                                          "Current OS is: {os}".format(
                        cwd=cwd,
                        os=os_name)
                data['cmd'].append(cmd)  # append command

    def cmd(self, ctx: CtxItem, cmds: list, silent: bool = False):
        """
        Event: CMD_EXECUTE

        :param ctx: CtxItem
        :param cmds: commands dict
        :param silent: silent mode
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
                    force = True  # call from tool

        if not is_cmd:
            return

        if self.get_option_value("sandbox_docker"):
            sandbox_commands = [
                "sys_exec",
            ]
            if any(x in [x["cmd"] for x in my_commands] for x in sandbox_commands):
                # check for Docker installed
                if not self.docker.is_docker_installed():
                    # snap version
                    if self.window.core.platforms.is_snap():
                        self.error(trans('docker.install.snap'))
                        self.window.update_status(trans('docker.install.snap'))
                    # other versions
                    else:
                        self.error(trans('docker.install'))
                        self.window.update_status(trans('docker.install'))
                    return
                # check if image exists
                if not self.docker.is_image():
                    self.error(trans('docker.image.build'))
                    self.window.update_status(trans('docker.build.start'))
                    self.docker.build()
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