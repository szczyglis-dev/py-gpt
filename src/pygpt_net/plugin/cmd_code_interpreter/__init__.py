#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.16 16:00:00                  #
# ================================================== #

from pygpt_net.plugin.base import BasePlugin
from pygpt_net.core.dispatcher import Event
from pygpt_net.item.ctx import CtxItem

from .runner import Runner
from .worker import Worker


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "cmd_code_interpreter"
        self.name = "Command: Code Interpreter"
        self.description = "Provides Python code execution"
        self.order = 100
        self.allowed_cmds = [
            "code_execute",
            "code_execute_file",
            "sys_exec",
        ]
        self.use_locale = True
        self.init_options()
        self.runner = Runner(self)

    def init_options(self):
        """Initialize options"""
        # cmd enable/disable
        self.add_option(
            "python_cmd_tpl",
            type="text",
            value="python3 {filename}",
            label="Python command template",
            description="Python command template to execute, use {filename} for filename placeholder",
        )
        self.add_option(
            "cmd_code_execute",
            type="bool",
            value=True,
            label="Enable: Python Code Generate and Execute",
            description="Allows Python code execution (generate and execute from file)",
        )
        self.add_option(
            "cmd_code_execute_file",
            type="bool",
            value=True,
            label="Enable: Python Code Execute (File)",
            description="Allows Python code execution from existing file",
        )
        self.add_option(
            "cmd_sys_exec",
            type="bool",
            value=True,
            label="Enable: System Command Execute",
            description="Allows system commands execution",
        )
        self.add_option(
            "sandbox_docker",
            type="bool",
            value=False,
            label="Sandbox (docker container)",
            description="Executes commands in sandbox (docker container). "
                        "Docker must be installed and running.",
        )
        self.add_option(
            "sandbox_docker_image",
            type="text",
            value='python:3.8-alpine',
            label="Docker image",
            description="Docker image to use for sandbox",
        )

        # cmd syntax (prompt/instruction)
        self.add_option(
            "syntax_code_execute",
            type="textarea",
            value='"code_execute": create and execute Python code, params: "filename", "code"',
            label="Syntax: code_execute",
            description="Syntax for Python code execution (generate and execute from file)",
            advanced=True,
        )
        self.add_option(
            "syntax_code_execute_file",
            type="textarea",
            value='"code_execute_file": execute Python code from existing file, params: "filename"',
            label="Syntax: code_execute_file",
            description="Syntax for Python code execution from existing file",
            advanced=True,
        )
        self.add_option(
            "syntax_sys_exec",
            type="textarea",
            value='"sys_exec": execute ANY system command, script or application in user\'s '
                  'environment, params: "command"',
            label="Syntax: sys_exec",
            description="Syntax for system commands execution",
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
                data['commands'],
            )

    def cmd_syntax(self, data: dict):
        """
        Event: CMD_SYNTAX

        :param data: event data dict
        """
        # get current working directory
        cwd = self.window.core.config.get_user_dir('data')
        if self.get_option_value("sandbox_docker"):
            cwd = "/data (in docker sandbox)"

        for item in self.allowed_cmds:
            if self.is_cmd_allowed(item):
                key = "syntax_" + item
                if self.has_option(key):
                    value = self.get_option_value(key)
                    # append CWD to sys_exec syntax
                    if key == "syntax_sys_exec":
                        value += "\nIMPORTANT: ALWAYS use an absolute (not relative) paths when passing " \
                                 "ANY commands to \"command\" param, the current working directory is: {}".format(cwd)
                    data['syntax'].append(value)

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

            # connect signals
            self.runner.signals = worker.signals

            # INTERNAL MODE (sync)
            # if internal (autonomous) call then use synchronous call
            if ctx.internal:
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

    def log(self, msg):
        """
        Log message to console

        :param msg: message to log
        """
        full_msg = '[CMD] ' + str(msg)
        self.debug(full_msg)
        self.window.ui.status(full_msg)
        if self.is_log():
            print(full_msg)
