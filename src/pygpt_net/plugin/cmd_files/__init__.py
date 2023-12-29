#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.28 21:00:00                  #
# ================================================== #


from PySide6.QtCore import Slot

from pygpt_net.plugin.base import BasePlugin
from .worker import Worker


class Plugin(BasePlugin):
    def __init__(self):
        super(Plugin, self).__init__()
        self.id = "cmd_files"
        self.name = "Command: Files I/O"
        self.description = "Provides commands to read and write files"
        self.window = None
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
        ]
        self.use_locale = True
        self.init_options()

    def init_options(self):
        """
        Initialize options
        """
        # cmd enable/disable
        self.add_option("cmd_read_file", "bool", True,
                        "Enable: Read file", "Allows `read_file` command execution")
        self.add_option("cmd_save_file", "bool", True,
                        "Enable: Save file", "Allows `save_file` command execution")
        self.add_option("cmd_append_file", "bool", True,
                        "Enable: Append to file", "Allows `append_file` command execution")
        self.add_option("cmd_delete_file", "bool", True,
                        "Enable: Delete file", "Allows `delete_file` command execution")
        self.add_option("cmd_list_dir", "bool", True,
                        "Enable: List files in directory (ls)", "Allows `list_dir` command execution")
        self.add_option("cmd_mkdir", "bool", True,
                        "Enable: Directory creation (mkdir)", "Allows `mkdir` command execution")
        self.add_option("cmd_download_file", "bool", True,
                        "Enable: Downloading files", "Allows `download_file` command execution")
        self.add_option("cmd_rmdir", "bool", True,
                        "Enable: Removing directories", "Allows `rmdir` command execution")
        self.add_option("cmd_copy_file", "bool", True,
                        "Enable: Copying files", "Allows `copy` command execution")
        self.add_option("cmd_copy_dir", "bool", True,
                        "Enable: Copying directories (recursive)", "Allows `copy_dir` command execution")
        self.add_option("cmd_move", "bool", True,
                        "Enable: Move files and directories (rename)", "Allows `move` command execution")
        self.add_option("cmd_is_dir", "bool", True,
                        "Enable: Check if path is directory", "Allows `is_dir` command execution")
        self.add_option("cmd_is_file", "bool", True,
                        "Enable: Check if path is file", "Allows `is_file` command execution")
        self.add_option("cmd_file_exists", "bool", True,
                        "Enable: Check if file or directory exists", "Allows `file_exists` command execution")
        self.add_option("cmd_file_size", "bool", True,
                        "Enable: Get file size", "Allows `file_size` command execution")
        self.add_option("cmd_file_info", "bool", True,
                        "Enable: Get file info", "Allows `file_info` command execution")

        # cmd syntax (prompt/instruction)
        self.add_option("syntax_read_file", "textarea", '"read_file": read data from file, params: "filename"',
                        "Syntax: read_file",
                        "Syntax for reading files", advanced=True)
        self.add_option("syntax_save_file", "textarea", '"save_file": save data to file, params: "filename", "data"',
                        "Syntax: save_file",
                        "Syntax for saving files", advanced=True)
        self.add_option("syntax_append_file", "textarea",
                        '"append_file": append data to file, params: "filename", "data"',
                        "Syntax: append_file",
                        "Syntax for appending to files", advanced=True)
        self.add_option("syntax_delete_file", "textarea", '"delete_file": delete file, params: "filename"',
                        "Syntax: delete_file",
                        "Syntax for deleting files", advanced=True)
        self.add_option("syntax_list_dir", "textarea", '"list_dir": list files and dirs in directory, params: "path"',
                        "Syntax: list_dir",
                        "Syntax for listing files", advanced=True)
        self.add_option("syntax_mkdir", "textarea", '"mkdir": create directory, params: "path"',
                        "Syntax: mkdir",
                        "Syntax for directory creation", advanced=True)
        self.add_option("syntax_download_file", "textarea", '"download_file": download file, params: "src", "dst"',
                        "Syntax: download_file",
                        "Syntax for downloading files", advanced=True)
        self.add_option("syntax_rmdir", "textarea", '"rmdir": remove directory, params: "path"',
                        "Syntax: rmdir",
                        "Syntax for removing directories", advanced=True)
        self.add_option("syntax_copy_file", "textarea", '"copy_file": copy file, params: "src", "dst"',
                        "Syntax: copy_file",
                        "Syntax for copying files", advanced=True)
        self.add_option("syntax_copy_dir", "textarea", '"copy_dir": recursive copy directory, params: "src", "dst"',
                        "Syntax: copy_dir",
                        "Syntax for recursive copying directories", advanced=True)
        self.add_option("syntax_move", "textarea", '"move": move file or directory, params: "src", "dst"',
                        "Syntax: move",
                        "Syntax for moving files and directories", advanced=True)
        self.add_option("syntax_is_dir", "textarea", '"is_dir": check if path is directory, params: "path"',
                        "Syntax: is_dir",
                        "Syntax for checking if path is directory", advanced=True)
        self.add_option("syntax_is_file", "textarea", '"is_file": check if path is file, params: "path"',
                        "Syntax: is_file",
                        "Syntax for checking if path is file", advanced=True)
        self.add_option("syntax_file_exists", "textarea", '"file_exists": check if file or directory exists, params: '
                                                          '"path"',
                        "Syntax: file_exists",
                        "Syntax for checking if file or directory exists", advanced=True)
        self.add_option("syntax_file_size", "textarea", '"file_size": get file size, params: "path"',
                        "Syntax: file_size",
                        "Syntax for getting file size", advanced=True)
        self.add_option("syntax_file_info", "textarea", '"file_info": get file info, params: "path"',
                        "Syntax: file_info",
                        "Syntax for getting file info", advanced=True)

    def setup(self):
        """
        Return available config options

        :return: config options
        :rtype: dict
        """
        return self.options

    def attach(self, window):
        """
        Attach window

        :param window: Window instance
        """
        self.window = window

    def handle(self, event, *args, **kwargs):
        """
        Handle dispatched event

        :param event: event object
        """
        name = event.name
        data = event.data
        ctx = event.ctx

        if name == 'cmd.syntax':
            self.cmd_syntax(data)
        elif name == 'cmd.execute':
            self.cmd(ctx, data['commands'])

    def is_cmd_allowed(self, cmd):
        """
        Check if cmd is allowed

        :param cmd: command name
        :return: true if allowed
        :rtype: bool
        """
        key = "cmd_" + cmd
        if self.has_option(key) and self.get_option_value(key) is True:
            return True
        return False

    def log(self, msg):
        """
        Log message to console

        :param msg: message to log
        """
        full_msg = '[CMD] ' + str(msg)
        self.debug(full_msg)
        self.window.set_status(full_msg)
        print(full_msg)

    @Slot(object)
    def handle_finished(self, ctx, response):
        """
        Handle finished response
        :param ctx: context
        :param response: response
        """
        # dispatcher handle late response
        ctx.results.append(response)
        ctx.reply = True
        self.window.core.dispatcher.reply(ctx)

    @Slot(object)
    def handle_status(self, data):
        """
        Handle thread status msg
        :param data: status message
        """
        self.window.set_status(str(data))

    @Slot(object)
    def handle_error(self, err):
        """
        Handle thread error
        :param err: error object
        """
        self.window.core.debug.log(err)
        self.window.ui.dialogs.alert("Code Interpreter Error: " + str(err))

    @Slot(object)
    def handle_debug(self, msg):
        """
        Handle debug message
        :param msg: message
        """
        self.debug(msg)

    @Slot(object)
    def handle_log(self, msg):
        """
        Handle log message
        :param msg: message
        """
        self.log(msg)

    def cmd_syntax(self, data):
        """
        Event: On cmd syntax prepare

        :param data: event data dict
        """
        for option in self.allowed_cmds:
            if self.is_cmd_allowed(option):
                key = "syntax_" + option
                if self.has_option(key):
                    data['syntax'].append(str(self.get_option_value(key)))

    def cmd(self, ctx, cmds):
        """
        Event: On cmd

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

        # worker
        worker = Worker()
        worker.plugin = self
        worker.cmds = my_commands
        worker.ctx = ctx

        # signals
        worker.signals.finished.connect(self.handle_finished)
        worker.signals.log.connect(self.handle_log)
        worker.signals.debug.connect(self.handle_debug)
        worker.signals.status.connect(self.handle_status)
        worker.signals.error.connect(self.handle_error)

        # start
        self.window.threadpool.start(worker)
