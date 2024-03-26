#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.25 10:00:00                  #
# ================================================== #

from PySide6.QtCore import Slot

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
        self.type = [
            'interpreter',
        ]
        self.order = 100
        self.allowed_cmds = [
            "code_execute",
            "code_execute_file",
            "code_execute_all",
            "sys_exec",
            "get_python_output",
            "get_python_input",
            "clear_python_output",
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
        self.add_option(
            "auto_cwd",
            type="bool",
            value=True,
            label="Auto-append CWD to sys_exec",
            description="Automatically append current working directory to sys_exec command",
        )
        self.add_option(
            "attach_output",
            type="bool",
            value=True,
            label="Connect to the Python code interpreter window",
            description="Attach code input/output to the Python code interpreter window.",
        )

        # commands
        self.add_cmd(
            "code_execute",
            instruction="save generated Python code and execute it",
            params=[
                {
                    "name": "path",
                    "type": "str",
                    "description": "path to save",
                    "default": ".interpreter.current.py",
                    "required": True,
                },
                {
                    "name": "code",
                    "type": "str",
                    "description": "code",
                    "required": True,
                },
            ],
            enabled=True,
            description="Allows Python code execution (generate and execute from file)",
        )
        self.add_cmd(
            "code_execute_file",
            instruction="execute Python code from existing file",
            params=[
                {
                    "name": "path",
                    "type": "str",
                    "description": "file path",
                    "required": True,
                },
            ],
            enabled=True,
            description="Allows Python code execution from existing file",
        )
        # commands
        self.add_cmd(
            "code_execute_all",
            instruction="run all Python code from my interpreter",
            params=[
                {
                    "name": "code",
                    "type": "str",
                    "description": "code to append and execute",
                    "required": True,
                },
            ],
            enabled=True,
            description="Allows Python code execution (generate and execute from file)",
        )
        self.add_cmd(
            "sys_exec",
            instruction="execute ANY system command, script or app in user's environment",
            params=[
                {
                    "name": "command",
                    "type": "str",
                    "description": "system command",
                    "required": True,
                },
            ],
            enabled=True,
            description="Allows system commands execution",
        )
        self.add_cmd(
            "get_python_output",
            instruction="get output from my Python interpreter",
            params=[],
            enabled=True,
            description="Allows to get output from last executed code",
        )
        self.add_cmd(
            "get_python_input",
            instruction="get all input code from my Python interpreter",
            params=[],
            enabled=True,
            description="Allows to get input from Python interpreter",
        )
        self.add_cmd(
            "clear_python_output",
            instruction="clear output from my Python interpreter",
            params=[],
            enabled=True,
            description="Allows to clear output from last executed code",
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
            if self.has_cmd(item):
                cmd = self.get_cmd(item)
                if self.get_option_value("auto_cwd") and item == "sys_exec":
                    cmd["instruction"] += "\nIMPORTANT: ALWAYS use absolute (not relative) path when passing " \
                                          "ANY command to \"command\" param, current working directory: {}".format(cwd)
                data['cmd'].append(cmd)  # append command

    @Slot(object, str)
    def handle_interpreter_output(self, data, type):
        """
        Handle interpreter output

        :param data: output data
        :param type: output type
        """
        if not self.get_option_value("attach_output"):
            return
        self.window.tools.get("interpreter").append_output(data, type)

    @Slot()
    def handle_interpreter_clear(self):
        """Handle interpreter clear"""
        self.window.tools.get("interpreter").clear_all()

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
            worker.signals.output.connect(self.handle_interpreter_output)
            worker.signals.clear.connect(self.handle_interpreter_clear)

            # connect signals
            self.runner.signals = worker.signals

            # check if async allowed
            if not self.window.core.dispatcher.async_allowed(ctx):
                worker.run()
                return

            # start
            self.window.threadpool.start(worker)

        except Exception as e:
            self.error(e)

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
