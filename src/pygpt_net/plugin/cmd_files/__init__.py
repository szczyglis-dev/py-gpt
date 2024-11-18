#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.14 01:00:00                  #
# ================================================== #
import os

from pygpt_net.plugin.base import BasePlugin
from pygpt_net.core.dispatcher import Event
from pygpt_net.item.ctx import CtxItem

from .worker import Worker


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "cmd_files"
        self.name = "Command: Files I/O"
        self.description = "Provides commands to read and write files"
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
        self.init_options()

    def init_options(self):
        """Initialize options"""
        self.add_option(
            "model_tmp_query",
            type="combo",
            value="gpt-3.5-turbo",
            label="Model for query in-memory index",
            description="Model used for query in-memory index for `query_file` command, "
                        "default: gpt-3.5-turbo",
            tooltip="Query model",
            use="models",
            tab="indexing",
        )
        self.add_option(
            "idx",
            type="text",
            value="base",
            label="Index to use when indexing files",
            description="ID of index to use for files indexing",
            tooltip="Index name",
            tab="indexing",
        )
        self.add_option(
            "use_loaders",
            type="bool",
            value=True,
            label="Use data loaders",
            description="Use data loaders from Llama-index for file reading (read_file command)",
        )
        self.add_option(
            "auto_index",
            type="bool",
            value=False,
            label="Auto index reading files",
            description="If enabled, every time file is read, it will be automatically indexed",
            tab="indexing",
        )
        self.add_option(
            "only_index",
            type="bool",
            value=False,
            label="Only index reading files",
            description="If enabled, file will be indexed without reading it",
            tab="indexing",
        )

        # commands
        self.add_cmd(
            "send_file",
            instruction="send file as attachment from my computer to you for analyze",
            params=[
                {
                    "name": "path",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Upload file as attachment",
        )
        self.add_cmd(
            "read_file",
            instruction="read data from files",
            params=[
                {
                    "name": "path",
                    "type": "list",
                    "description": "path(s) to files",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Read file",
        )
        self.add_cmd(
            "query_file",
            instruction="read, index and quick query file for additional context",
            params=[
                {
                    "name": "path",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
                {
                    "name": "query",
                    "type": "str",
                    "description": "query",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Query file with Llama-index",
            tab="indexing",
        )
        self.add_cmd(
            "save_file",
            instruction="save data to file",
            params=[
                {
                    "name": "path",
                    "type": "str",
                    "description": "path to file",
                    "required": True,
                },
                {
                    "name": "data",
                    "type": "str",
                    "description": "text data",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Save file",
        )
        self.add_cmd(
            "append_file",
            instruction="append data to file",
            params=[
                {
                    "name": "path",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
                {
                    "name": "data",
                    "type": "str",
                    "description": "data",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Append to file",
        )
        self.add_cmd(
            "delete_file",
            instruction="delete file",
            params=[
                {
                    "name": "path",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Delete file",
        )
        self.add_cmd(
            "list_dir",
            instruction="list files and dirs",
            params=[
                {
                    "name": "path",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: List files in directory (ls)",
        )
        self.add_cmd(
            "tree",
            instruction="get directory tree",
            params=[
                {
                    "name": "path",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: get directory tree",
        )
        self.add_cmd(
            "mkdir",
            instruction="create directory",
            params=[
                {
                    "name": "path",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Directory creation (mkdir)",
        )
        self.add_cmd(
            "download_file",
            instruction="download file",
            params=[
                {
                    "name": "src",
                    "type": "str",
                    "description": "source URL",
                    "required": True,
                },
                {
                    "name": "dst",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Downloading files",
        )
        self.add_cmd(
            "rmdir",
            instruction="remove directory",
            params=[
                {
                    "name": "path",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Removing directories",
        )
        self.add_cmd(
            "copy_file",
            instruction="copy file",
            params=[
                {
                    "name": "src",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
                {
                    "name": "dst",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Copying files",
        )
        self.add_cmd(
            "copy_dir",
            instruction="recursive copy directory",
            params=[
                {
                    "name": "src",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
                {
                    "name": "dst",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Copying directories (recursive)",
        )
        self.add_cmd(
            "move",
            instruction="move file or directory",
            params=[
                {
                    "name": "src",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
                {
                    "name": "dst",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Move files and directories (rename)",
        )
        self.add_cmd(
            "is_dir",
            instruction="check if path is directory",
            params=[
                {
                    "name": "path",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Check if path is directory",
        )
        self.add_cmd(
            "is_file",
            instruction="check if path is file",
            params=[
                {
                    "name": "path",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Check if path is file",
        )
        self.add_cmd(
            "file_exists",
            instruction="check if file or directory exists",
            params=[
                {
                    "name": "path",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Check if file or directory exists",
        )
        self.add_cmd(
            "file_size",
            instruction="get file size",
            params=[
                {
                    "name": "path",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Get file size",
        )
        self.add_cmd(
            "file_info",
            instruction="get file info",
            params=[
                {
                    "name": "path",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Get file info",
        )
        self.add_cmd(
            "cwd",
            instruction="get current working directory (abs path)",
            params=[],
            enabled=True,
            description="Enable: Get current working directory (cwd)",
        )
        self.add_cmd(
            "file_index",
            instruction="index (embed as vectors in vector DB) file or directory",
            params=[
                {
                    "name": "path",
                    "type": "str",
                    "description": "path",
                    "required": True,
                },
            ],
            enabled=True,
            description="If enabled, model will be able to index file or directory using Llama-index",
        )
        self.add_cmd(
            "find",
            instruction="find file or directory, use empty path to search in current dir",
            params=[
                {
                    "name": "pattern",
                    "type": "str",
                    "description": "name pattern",
                    "required": True,
                },
                {
                    "name": "path",
                    "type": "str",
                    "description": "search directory",
                    "required": True,
                },
                {
                    "name": "recursive",
                    "type": "bool",
                    "description": "recursive search",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Find file or directory",
        )

    def setup(self) -> dict:
        """
        Return available config options

        :return: config options
        """
        return self.options

    def attach(self, window):
        """
        Attach window

        :param window: Window instance
        """
        self.window = window

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

        try:
            # worker
            worker = Worker()
            worker.plugin = self
            worker.cmds = my_commands
            worker.ctx = ctx

            # signals (base handlers)
            worker.signals.finished_more.connect(self.handle_finished_more)
            worker.signals.log.connect(self.handle_log)
            worker.signals.debug.connect(self.handle_debug)
            worker.signals.status.connect(self.handle_status)
            worker.signals.error.connect(self.handle_error)

            # check if async allowed
            if not self.window.core.dispatcher.async_allowed(ctx):
                worker.run()
                return

            # start
            self.window.threadpool.start(worker)

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
            return str(self.window.core.idx.indexing.read_text_content(path))
        else:
            data = ""
            if os.path.isfile(path):
                with open(path, 'r', encoding="utf-8") as file:
                    data = file.read()
            return data

    def log(self, msg: str):
        """
        Log message to console

        :param msg: message to log
        """
        if self.is_threaded():
            return
        full_msg = '[CMD] ' + str(msg)
        self.debug(full_msg)
        self.window.ui.status(full_msg)
        if self.is_log():
            print(full_msg)
