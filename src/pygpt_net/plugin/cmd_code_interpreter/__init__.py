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
from .runner import Runner
from .worker import Worker


class Plugin(BasePlugin):
    def __init__(self):
        super(Plugin, self).__init__()
        self.id = "cmd_code_interpreter"
        self.name = "Command: Code Interpreter"
        self.description = "Provides Python code execution"
        self.window = None
        self.order = 100
        self.allowed_cmds = [
            "code_execute",
            "code_execute_file",
            "sys_exec"
        ]
        self.use_locale = True
        self.init_options()
        self.runner = Runner(self)

    def init_options(self):
        """Initialize options"""
        # cmd enable/disable
        self.add_option("python_cmd_tpl", "text", 'python3 {filename}',
                        "Python command template",
                        "Python command template to execute, use {filename} for filename placeholder")
        self.add_option("cmd_code_execute", "bool", True,
                        "Enable: Python Code Generate and Execute",
                        "Allows Python code execution (generate and execute from file)")
        self.add_option("cmd_code_execute_file", "bool", True,
                        "Enable: Python Code Execute (File)",
                        "Allows Python code execution from existing file")
        self.add_option("cmd_sys_exec", "bool", True,
                        "Enable: System Command Execute",
                        "Allows system commands execution")
        self.add_option("sandbox_docker", "bool", False,
                        "Sandbox (docker container)",
                        "Executes commands in sandbox (docker container). Docker must be installed and running.")
        self.add_option("sandbox_docker_image", "text", 'python:3.8-alpine',
                        "Docker image",
                        "Docker image to use for sandbox")

        # cmd syntax (prompt/instruction)
        self.add_option("syntax_code_execute", "textarea", '"code_execute": create and execute Python code, params: '
                                                           '"filename", "code"',
                        "Syntax: code_execute",
                        "Syntax for Python code execution (generate and execute from file)", advanced=True)
        self.add_option("syntax_code_execute_file", "textarea", '"code_execute_file": execute Python code from '
                                                                'existing file, params: "filename"',
                        "Syntax: code_execute_file",
                        "Syntax for Python code execution from existing file", advanced=True)
        self.add_option("syntax_sys_exec", "textarea", '"sys_exec": execute ANY system command, script or application '
                                                       'in user\'s environment, params: "command"',
                        "Syntax: sys_exec",
                        "Syntax for system commands execution", advanced=True)

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

    def cmd_syntax(self, data):
        """
        Event: On cmd syntax prepare

        :param data: event data dict
        """
        for item in self.allowed_cmds:
            if self.is_cmd_allowed(item):
                key = "syntax_" + item
                if self.has_option(key):
                    data['syntax'].append(str(self.get_option_value(key)))

    def cmd(self, ctx, cmds):
        """
        Execute command

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

        # signals (base handlers)
        worker.signals.finished.connect(self.handle_finished)
        worker.signals.log.connect(self.handle_log)
        worker.signals.debug.connect(self.handle_debug)
        worker.signals.status.connect(self.handle_status)
        worker.signals.error.connect(self.handle_error)

        # connect signals
        self.runner.signals = worker.signals

        # start
        self.window.threadpool.start(worker)
