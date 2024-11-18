#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.16 05:00:00                  #
# ================================================== #
import os

from PySide6.QtCore import Slot

from pygpt_net.plugin.base import BasePlugin
from pygpt_net.core.dispatcher import Event
from pygpt_net.item.ctx import CtxItem

from .builder import Builder
from .ipython import IPythonInterpreter
from .runner import Runner
from .worker import Worker
from pygpt_net.utils import trans


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "cmd_code_interpreter"
        self.name = "Command: Code Interpreter (v2)"
        self.description = "Provides Python/HTML/JS code execution"
        self.type = [
            'interpreter',
        ]
        self.order = 100
        self.allowed_cmds = [
            "ipython_execute_new",
            "ipython_execute",
            "ipython_kernel_restart",
            "code_execute",
            "code_execute_file",
            "code_execute_all",
            "sys_exec",
            "get_python_output",
            "get_python_input",
            "clear_python_output",
            "render_html_output",
            "get_html_output",
        ]
        self.use_locale = True
        self.runner = Runner(self)
        self.ipython = IPythonInterpreter(self)
        self.builder = Builder(self)
        self.worker = None
        self.init_options()


    def init_options(self):
        """Initialize options"""
        dockerfile = '# Tip: After making changes to this Dockerfile, you must rebuild the image to apply the changes'
        dockerfile += '(Menu -> Tools -> Rebuild IPython Docker Image)'
        dockerfile += '\n\n'
        dockerfile += 'FROM python:3.9'
        dockerfile += '\n\n'
        dockerfile += '# You can customize the packages installed by default here:'
        dockerfile += '\n# ========================================================'
        dockerfile += '\nRUN pip install jupyter ipykernel'
        dockerfile += '\n# ========================================================'
        dockerfile += '\n\n'
        dockerfile += 'RUN mkdir /data'
        dockerfile += '\n\n'
        dockerfile += '# Expose the necessary ports for Jupyter kernel communication'
        dockerfile += '\nEXPOSE 5555 5556 5557 5558 5559'
        dockerfile += '\n\n'
        dockerfile += '# Data directory, bound as a volume to the local \'data/ipython\' directory'
        dockerfile += '\nWORKDIR /data'
        dockerfile += '\n\n'
        dockerfile += '# Start the IPython kernel with specified ports and settings'
        dockerfile += '\nCMD ["ipython", "kernel", \\'
        dockerfile += '\n--ip=0.0.0.0, \\'
        dockerfile += '\n--transport=tcp, \\'
        dockerfile += '\n--shell=5555, \\'
        dockerfile += '\n--iopub=5556, \\'
        dockerfile += '\n--stdin=5557, \\'
        dockerfile += '\n--control=5558, \\'
        dockerfile += '\n--hb=5559, \\'
        dockerfile += '\n--Session.key=19749810-8febfa748186a01da2f7b28c, \\'
        dockerfile += '\n--Session.signature_scheme=hmac-sha256]'

        # cmd enable/disable
        self.add_option(
            "ipython_dockerfile",
            type="textarea",
            value=dockerfile,
            label="Dockerfile for IPython kernel",
            description="Dockerfile used to build IPython kernel container image",
            tooltip="Dockerfile",
            tab="ipython",
        )
        self.add_option(
            "ipython_image_name",
            type="text",
            value='pygpt_ipython_kernel',
            label="Docker image name",
            tab="ipython",
        )
        self.add_option(
            "ipython_container_name",
            type="text",
            value='pygpt_ipython_kernel_container',
            label="Docker container name",
            tab="ipython",
        )
        self.add_option(
            "ipython_session_key",
            type="text",
            value='19749810-8febfa748186a01da2f7b28c',
            label="Session Key",
            tab="ipython",
        )
        self.add_option(
            "ipython_conn_addr",
            type="text",
            value='127.0.0.1',
            label="Connection Address",
            tab="ipython",
        )
        self.add_cmd(
            "ipython_execute",
            instruction="execute Python code in IPython interpreter (in current kernel) and get output.",
            params=[
                {
                    "name": "code",
                    "type": "str",
                    "description": "code to execute in IPython interpreter, usage of !magic commands is allowed",
                    "required": True,
                },
            ],
            enabled=True,
            description="Allows Python code execution in IPython interpreter (in current kernel)",
            tab="ipython",
        )
        self.add_cmd(
            "ipython_execute_new",
            instruction="execute Python code in IPython interpreter (in new kernel) and get output.",
            params=[
                {
                    "name": "code",
                    "type": "str",
                    "description": "code to execute in IPython interpreter, usage of !magic commands is allowed",
                    "required": True,
                },
            ],
            enabled=True,
            description="Allows Python code execution in IPython interpreter (in new kernel)",
            tab="ipython",
        )
        self.add_cmd(
            "ipython_kernel_restart",
            instruction="restart IPython kernel",
            params=[],
            enabled=True,
            description="Allows to restart IPython kernel",
            tab="ipython",
        )
        self.add_option(
            "ipython_port_shell",
            type="int",
            value=5555,
            label="Port: shell",
            tab="ipython",
            advanced=True,
        )
        self.add_option(
            "ipython_port_iopub",
            type="int",
            value=5556,
            label="Port: iopub",
            tab="ipython",
            advanced=True,
        )
        self.add_option(
            "ipython_port_stdin",
            type="int",
            value=5557,
            label="Port: stdin",
            tab="ipython",
            advanced=True,
        )
        self.add_option(
            "ipython_port_control",
            type="int",
            value=5558,
            label="Port: control",
            tab="ipython",
            advanced=True,
        )
        self.add_option(
            "ipython_port_hb",
            type="int",
            value=5559,
            label="Port: hb",
            tab="ipython",
            advanced=True,
        )

        self.add_option(
            "python_cmd_tpl",
            type="text",
            value="python3 {filename}",
            label="Python command template",
            description="Python command template to execute, use {filename} for filename placeholder",
            tab="python_legacy",
        )
        self.add_option(
            "sandbox_docker",
            type="bool",
            value=False,
            label="Sandbox (docker container)",
            description="Executes commands in sandbox (docker container). "
                        "Docker must be installed and running.",
            tab="python_legacy",
        )
        self.add_option(
            "sandbox_docker_image",
            type="text",
            value='python:3.8-alpine',
            label="Docker image",
            description="Docker image to use for sandbox",
            tab="python_legacy",
        )
        self.add_option(
            "auto_cwd",
            type="bool",
            value=True,
            label="Auto-append CWD to sys_exec",
            description="Automatically append current working directory to sys_exec command",
            tab="general",
        )
        self.add_option(
            "attach_output",
            type="bool",
            value=True,
            label="Connect to the Python code interpreter window",
            description="Attach code input/output to the Python code interpreter window.",
            tab="general",
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
            enabled=False,
            description="Allows Python code execution (generate and execute from file)",
            tab="python_legacy",
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
            enabled=False,
            description="Allows Python code execution from existing file",
            tab="python_legacy",
        )
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
            enabled=False,
            description="Allows Python code execution (generate and execute from file)",
            tab="python_legacy",
        )
        self.add_cmd(
            "sys_exec",
            instruction="execute ANY system command, script or app in user's environment. Do not use this command to install Python libraries, use IPython environment and IPython commands instead.",
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
            tab="general",
        )
        self.add_cmd(
            "get_python_output",
            instruction="get output from my Python interpreter",
            params=[],
            enabled=True,
            description="Allows to get output from last executed code",
            tab="general",
        )
        self.add_cmd(
            "get_python_input",
            instruction="get all input code from my Python interpreter",
            params=[],
            enabled=True,
            description="Allows to get input from Python interpreter",
            tab="general",
        )
        self.add_cmd(
            "clear_python_output",
            instruction="clear output from my Python interpreter",
            params=[],
            enabled=True,
            description="Allows to clear output from last executed code",
            tab="general",
        )
        self.add_cmd(
            "render_html_output",
            instruction="send HTML/JS code to HTML built-in browser (HTML Canvas) and render it",
            params=[
                {
                    "name": "html",
                    "type": "str",
                    "description": "HTML/JS code",
                    "required": True,
                },
            ],
            enabled=True,
            description="Allows to render HTML/JS code in HTML Canvas",
            tab="html_canvas",
        )
        self.add_cmd(
            "get_html_output",
            instruction="get current output from HTML Canvas",
            params=[],
            enabled=True,
            description="Allows to get current output from HTML Canvas",
            tab="html_canvas",
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
        ipython_data = os.path.join(cwd, 'ipython')
        if self.get_option_value("sandbox_docker"):
            cwd = "/data (in docker sandbox)"

        for item in self.allowed_cmds:
            if self.has_cmd(item):
                cmd = self.get_cmd(item)
                if self.get_option_value("auto_cwd") and item == "sys_exec":
                    cmd["instruction"] += "\nIMPORTANT: ALWAYS use absolute (not relative) path when passing " \
                                          "ANY command to \"command\" param, current workdir is: {}".format(cwd)
                if item == "ipython_execute" or item == "ipython_execute_new":
                    cmd["instruction"] += ("\nIPython works in Docker container. Directory /data is the container's workdir - "
                                           "directory is bound in host machine to: {}").format(ipython_data)
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

    @Slot(object)
    def handle_html_output(self, data):
        """
        Handle HTML/JS canvas output

        :param data: HTML/JS code
        """
        self.window.tools.get("html_canvas").set_output(data)
        self.window.tools.get("html_canvas").open()

    def cmd(self, ctx: CtxItem, cmds: list):
        """
        Event: CMD_EXECUTE

        :param ctx: CtxItem
        :param cmds: commands dict
        """
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

        ipython_commands = [
            "ipython_execute_new",
            "ipython_execute",
            "ipython_kernel_restart",
        ]
        if any(x in [x["cmd"] for x in my_commands] for x in ipython_commands):
            # check for Docker installed
            if not self.ipython.is_docker_installed():
                # snap version
                if self.window.core.platforms.is_snap():
                    self.error(trans('ipython.docker.install.snap'))
                    self.window.ui.status(trans('ipython.docker.install.snap'))
                # other versions
                else:
                    self.error(trans('ipython.docker.install'))
                    self.window.ui.status(trans('ipython.docker.install'))
                return
            # check if image exists
            if not self.ipython.is_image():
                self.error(trans('ipython.image.build'))
                self.window.ui.status(trans('ipython.docker.build.start'))
                self.builder.build_image()
                return

        try:
            # worker
            self.worker = Worker()
            self.worker.plugin = self
            self.worker.cmds = my_commands
            self.worker.ctx = ctx

            # signals (base handlers)
            self.worker.signals.finished_more.connect(self.handle_finished_more)
            self.worker.signals.log.connect(self.handle_log)
            self.worker.signals.debug.connect(self.handle_debug)
            self.worker.signals.status.connect(self.handle_status)
            self.worker.signals.error.connect(self.handle_error)
            self.worker.signals.output.connect(self.handle_interpreter_output)
            self.worker.signals.clear.connect(self.handle_interpreter_clear)
            self.worker.signals.html_output.connect(self.handle_html_output)

            # connect signals
            self.worker.signals.ipython_output.connect(self.handle_ipython_output)
            self.ipython.attach_signals(self.worker.signals)
            self.runner.attach_signals(self.worker.signals)

            # check if async allowed
            if not self.window.core.dispatcher.async_allowed(ctx) and not force:
                self.worker.run()
                return

            # start
            self.window.threadpool.start(self.worker)
        except Exception as e:
            self.error(e)

    @Slot(object)
    def handle_ipython_output(self, data):
        """
        Handle IPython output

        :param data: output data
        """
        if not self.get_option_value("attach_output"):
            return
        # if self.is_threaded():
            # return
        # print(data)
        cleaned_data = self.ipython.remove_ansi(data)
        self.window.tools.get("interpreter").append_output(cleaned_data)
        self.window.ui.status("")

    def log(self, msg):
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
