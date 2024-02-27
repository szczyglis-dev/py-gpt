#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.27 18:00:00                  #
# ================================================== #

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
            "is_dir",
            "is_file",
            "file_exists",
            "file_size",
            "file_info",
            "send_file",
            "cwd",
            "file_index",
        ]
        self.use_locale = True
        self.init_options()

    def init_options(self):
        """Initialize options"""
        # cmd enable/disable
        self.add_option(
            "cmd_send_file",
            type="bool",
            value=True,
            label="Enable: Upload file as attachment",
            description="Allows `send_file` command execution",
        )
        self.add_option(
            "cmd_read_file",
            type="bool",
            value=True,
            label="Enable: Read file",
            description="Allows `read_file` command execution",
        )
        self.add_option(
            "cmd_save_file",
            type="bool",
            value=True,
            label="Enable: Save file",
            description="Allows `save_file` command execution",
        )
        self.add_option(
            "cmd_append_file",
            type="bool",
            value=True,
            label="Enable: Append to file",
            description="Allows `append_file` command execution",
        )
        self.add_option(
            "cmd_delete_file",
            type="bool",
            value=True,
            label="Enable: Delete file",
            description="Allows `delete_file` command execution",
        )
        self.add_option(
            "cmd_list_dir",
            type="bool",
            value=True,
            label="Enable: List files in directory (ls)",
            description="Allows `list_dir` command execution",
        )
        self.add_option(
            "cmd_mkdir",
            type="bool",
            value=True,
            label="Enable: Directory creation (mkdir)",
            description="Allows `mkdir` command execution",
        )
        self.add_option(
            "cmd_download_file",
            type="bool",
            value=True,
            label="Enable: Downloading files",
            description="Allows `download_file` command execution",
        )
        self.add_option(
            "cmd_rmdir",
            type="bool",
            value=True,
            label="Enable: Removing directories",
            description="Allows `rmdir` command execution",
        )
        self.add_option(
            "cmd_copy_file",
            type="bool",
            value=True,
            label="Enable: Copying files",
            description="Allows `copy` command execution",
        )
        self.add_option(
            "cmd_copy_dir",
            type="bool",
            value=True,
            label="Enable: Copying directories (recursive)",
            description="Allows `copy_dir` command execution",
        )
        self.add_option(
            "cmd_move",
            type="bool",
            value=True,
            label="Enable: Move files and directories (rename)",
            description="Allows `move` command execution",
        )
        self.add_option(
            "cmd_is_dir",
            type="bool",
            value=True,
            label="Enable: Check if path is directory",
            description="Allows `is_dir` command execution",
        )
        self.add_option(
            "cmd_is_file",
            type="bool",
            value=True,
            label="Enable: Check if path is file",
            description="Allows `is_file` command execution",
        )
        self.add_option(
            "cmd_file_exists",
            type="bool",
            value=True,
            label="Enable: Check if file or directory exists",
            description="Allows `file_exists` command execution",
        )
        self.add_option(
            "cmd_file_size",
            type="bool",
            value=True,
            label="Enable: Get file size",
            description="Allows `file_size` command execution",
        )
        self.add_option(
            "cmd_file_info",
            type="bool",
            value=True,
            label="Enable: Get file info",
            description="Allows `file_info` command execution",
        )
        self.add_option(
            "cmd_cwd",
            type="bool",
            value=True,
            label="Enable: Get current working directory (cwd)",
            description="Allows `cwd` command execution",
        )
        self.add_option(
            "cmd_file_index",
            type="bool",
            value=True,
            label="Enable: \"file_index\" command",
            description="If enabled, model will be able to index file or directory using Llama-index",
            tooltip="If enabled, model will be able to index file or directory using Llama-index",
        )
        self.add_option(
            "idx",
            type="text",
            value="base",
            label="Index to use when indexing files",
            description="ID of index to use for files indexing",
            tooltip="Index name",
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
        )
        self.add_option(
            "only_index",
            type="bool",
            value=False,
            label="Only index reading files",
            description="If enabled, file will be indexed without reading it",
        )

        # cmd syntax (prompt/instruction)
        self.add_option(
            "syntax_send_file",
            type="textarea",
            value='"send_file": sends file as attachment from my computer to you for analyze, params: "path"',
            label="Syntax: send_file",
            description="Syntax for send files as attachment",
            advanced=True,
        )
        self.add_option(
            "syntax_read_file",
            type="textarea",
            value='"read_file": read data from file, params: "filename"',
            label="Syntax: read_file",
            description="Syntax for reading files",
            advanced=True,
        )
        self.add_option(
            "syntax_save_file",
            type="textarea",
            value='"save_file": save data to file, params: "filename", "data"',
            label="Syntax: save_file",
            description="Syntax for saving files",
            advanced=True,
        )
        self.add_option(
            "syntax_append_file",
            type="textarea",
            value='"append_file": append data to file, params: "filename", "data"',
            label="Syntax: append_file",
            description="Syntax for appending to files",
            advanced=True,
        )
        self.add_option(
            "syntax_delete_file",
            type="textarea",
            value='"delete_file": delete file, params: "filename"',
            label="Syntax: delete_file",
            description="Syntax for deleting files",
            advanced=True,
        )
        self.add_option(
            "syntax_list_dir",
            type="textarea",
            value='"list_dir": list files and dirs in directory, params: "path"',
            label="Syntax: list_dir",
            description="Syntax for listing files",
            advanced=True,
        )
        self.add_option(
            "syntax_mkdir",
            type="textarea",
            value='"mkdir": create directory, params: "path"',
            label="Syntax: mkdir",
            description="Syntax for directory creation",
            advanced=True,
        )
        self.add_option(
            "syntax_download_file",
            type="textarea",
            value='"download_file": download file, params: "src", "dst"',
            label="Syntax: download_file",
            description="Syntax for downloading files",
            advanced=True,
        )
        self.add_option(
            "syntax_rmdir",
            type="textarea",
            value='"rmdir": remove directory, params: "path"',
            label="Syntax: rmdir",
            description="Syntax for removing directories",
            advanced=True,
        )
        self.add_option(
            "syntax_copy_file",
            type="textarea",
            value='"copy_file": copy file, params: "src", "dst"',
            label="Syntax: copy_file",
            description="Syntax for copying files",
            advanced=True,
        )
        self.add_option(
            "syntax_copy_dir",
            type="textarea",
            value='"copy_dir": recursive copy directory, params: "src", "dst"',
            label="Syntax: copy_dir",
            description="Syntax for recursive copying directories",
            advanced=True,
        )
        self.add_option(
            "syntax_move",
            type="textarea",
            value='"move": move file or directory, params: "src", "dst"',
            label="Syntax: move",
            description="Syntax for moving files and directories",
            advanced=True,
        )
        self.add_option(
            "syntax_is_dir",
            type="textarea",
            value='"is_dir": check if path is directory, params: "path"',
            label="Syntax: is_dir",
            description="Syntax for checking if path is directory",
            advanced=True,
        )
        self.add_option(
            "syntax_is_file",
            type="textarea",
            value='"is_file": check if path is file, params: "path"',
            label="Syntax: is_file",
            description="Syntax for checking if path is file",
            advanced=True,
        )
        self.add_option(
            "syntax_file_exists",
            type="textarea",
            value='"file_exists": check if file or directory exists, params: "path"',
            label="Syntax: file_exists",
            description="Syntax for checking if file or directory exists",
            advanced=True,
        )
        self.add_option(
            "syntax_file_size",
            type="textarea",
            value='"file_size": get file size, params: "path"',
            label="Syntax: file_size",
            description="Syntax for getting file size",
            advanced=True,
        )
        self.add_option(
            "syntax_file_info",
            type="textarea",
            value='"file_info": get file info, params: "path"',
            label="Syntax: file_info",
            description="Syntax for getting file info",
            advanced=True,
        )
        self.add_option(
            "syntax_cwd",
            type="textarea",
            value='"cwd": get current working directory (full system path)',
            label="Syntax: cwd",
            description="Syntax for getting current working directory",
            advanced=True,
        )
        self.add_option(
            "syntax_file_index",
            type="textarea",
            value='"file_index": use it to index (embed in Vector Store) a file or directory for future use, '
                  'params: "path"',
            label="Syntax: file_index",
            description="Syntax for file_index command",
            advanced=True,
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
            if self.is_cmd_allowed(option):
                key = "syntax_" + option
                if self.has_option(key):
                    data['syntax'].append(
                        str(self.get_option_value(key)),
                    )

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
            worker.signals.finished.connect(self.handle_finished)
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

    def is_cmd_allowed(self, cmd: str) -> bool:
        """
        Check if cmd is allowed

        :param cmd: command name
        :return: True if allowed
        """
        key = "cmd_" + cmd
        if self.has_option(key) and self.get_option_value(key) is True:
            return True
        return False

    def read_as_text(self, path: str, use_loaders: bool = True) -> str:
        """
        Read file and return content as text

        :param path: file path
        :param use_loaders: use Llama-index loader to read file
        :return: text content
        """
        if use_loaders:
            return str(self.window.core.idx.indexing.read_text_content(path))
        else:
            with open(path, 'r', encoding="utf-8") as file:
                data = file.read()
            return data

    def log(self, msg: str):
        """
        Log message to console

        :param msg: message to log
        """
        full_msg = '[CMD] ' + str(msg)
        self.debug(full_msg)
        self.window.ui.status(full_msg)
        if self.is_log():
            print(full_msg)
