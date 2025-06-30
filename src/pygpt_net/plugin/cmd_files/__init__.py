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

import os

from pygpt_net.plugin.base.plugin import BasePlugin
from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem

from .config import Config
from .output import Output
from .worker import Worker


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "cmd_files"
        self.name = "Files I/O"
        self.description = "Provides commands to read and write files"
        self.prefix = "I/O"
        self.order = 100
        self.allowed_cmds = [
            "read_file",
            "query_file",
            "save_file",
            "append_file",
            "delete_file",
            "list_dir",
            "mkdir",
            "download_file",
            "rmdir",
            "copy_file",
            "copy_dir",
            "move",
            "find",
            "is_dir",
            "is_file",
            "tree",
            "file_exists",
            "file_size",
            "file_info",
            "send_file",
            "cwd",
            "file_index",
        ]
        self.use_locale = True
        self.worker = None
        self.output = Output(self)
        self.config = Config(self)
        self.init_options()

    def init_options(self):
        """Initialize options"""
        self.config.from_defaults(self)

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

        if name == Event.CMD_SYNTAX:
            self.cmd_syntax(data)

        elif name == Event.CMD_EXECUTE:
            self.cmd(
                ctx,
                data['commands'],
            )

        elif name == Event.TOOL_OUTPUT_RENDER:
            if data['tool'] == self.id:
                data['html'] = self.output.handle(ctx, data['content'])

        elif name == Event.MODELS_CHANGED:
            # update models list
            self.refresh_option("model_tmp_query")

    def cmd_syntax(self, data: dict):
        """
        Event: CMD_SYNTAX

        :param data: event data dict
        """
        for option in self.allowed_cmds:
            if self.has_cmd(option):
                data['cmd'].append(self.get_cmd(option))  # append command

    def cmd(self, ctx: CtxItem, cmds: list):
        """
        Event: CMD_EXECUTE

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

        # set state: busy
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

    def read_as_text(self, path: str, use_loaders: bool = True) -> str:
        """
        Read file and return content as text

        :param path: file path
        :param use_loaders: use Llama-index loader to read file
        :return: text content
        """
        # use_loaders = False
        if use_loaders:
            content, docs = self.window.core.idx.indexing.read_text_content(path)
            return content
        else:
            data = ""
            if os.path.isfile(path):
                with open(path, 'r', encoding="utf-8") as file:
                    data = file.read()
            return data
