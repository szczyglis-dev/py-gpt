#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.20 10:15:00                  #
# ================================================== #

import os
import time
import uuid

from PySide6.QtCore import Slot

from pygpt_net.plugin.base.plugin import BasePlugin
from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem
from pygpt_net.core.sandbox import BuiltinSandboxPreparer

from .config import Config
from .sandbox import SandboxMode
from .execution import ExecutionManager
from .docker import Docker
from .builder import Builder
from .ipython import LocalKernel
from .ipython import DockerKernel
from .output import Output
from .runner import Runner



class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "cmd_code_interpreter"
        self.is_common_plugin = True
        self.name = "Python interpreter"
        self.description = "Provides Python/HTML/JS code execution"
        self.prefix = "Code"
        self.type = [
            'interpreter',
        ]
        self.order = 100
        self.allowed_cmds = [
            "ipython_exec",
            "ipython_sys_exec",
            "ipython_kernel_restart",
            "python_exec",
            "python_exec_file",
            "python_sys_exec",
            "html_render_output",
            "html_get_output",
        ]
        self.use_locale = True
        self.docker = Docker(self)
        self.runner = Runner(self)
        self.ipython_docker = DockerKernel(self)
        self.ipython_local = LocalKernel(self)
        self.builder = Builder(self)
        self.output = Output(self)
        self.worker = None
        self.config = Config(self)
        self.init_options()
        self.execution = ExecutionManager(self)
        self.builtin_preparer = BuiltinSandboxPreparer(self, "Python")

    def init_options(self):
        """Initialize options"""
        self.config.from_defaults(self)

    def is_ipython_enabled(self) -> bool:
        """Return True when the IPython interpreter option is enabled."""
        return bool(self.get_option_value("use_ipython"))

    def get_sandbox_mode(self) -> SandboxMode:
        """Return the selected execution/sandbox mode."""
        if hasattr(self, "execution"):
            return self.execution.get_mode()
        value = self.get_option_value("sandbox")
        try:
            return SandboxMode(value)
        except (TypeError, ValueError):
            return SandboxMode.DISABLED

    def get_execution_backend(self):
        """Return the backend responsible for the selected execution mode."""
        return self.execution.get_backend()

    def is_sandbox_mode(self, mode: str | SandboxMode) -> bool:
        """Return True when the requested sandbox mode is selected."""
        value = mode.value if isinstance(mode, SandboxMode) else str(mode)
        return self.get_sandbox_mode().value == value

    def is_docker_sandbox(self) -> bool:
        """Compatibility helper for Docker-specific UI/build code."""
        return self.is_sandbox_mode(SandboxMode.DOCKER)

    def is_builtin_sandbox(self) -> bool:
        """Return True when the uv-managed built-in sandbox is selected."""
        return self.is_sandbox_mode(SandboxMode.BUILTIN)

    def is_sandbox_enabled(self) -> bool:
        """Return True when commands run through any isolated sandbox backend."""
        return self.get_execution_backend().sandboxed

    def get_runtime_workdir(self, ctx=None) -> str:
        """Return the working directory visible to the active execution backend."""
        return self.get_execution_backend().get_runtime_workdir(ctx=ctx)

    def map_host_path_to_runtime(self, path: str, ctx=None) -> str:
        """Map a host path to the namespace visible to the active backend."""
        return self.get_execution_backend().map_host_path_to_runtime(path, ctx=ctx)

    def get_filesystem_context(self, host_data_dir: str) -> str:
        """Return model-facing filesystem guidance for the active backend."""
        return self.get_execution_backend().get_filesystem_context(
            host_data_dir,
            self.is_ipython_enabled(),
        )

    def is_command_active(self, cmd: str) -> bool:
        """Return whether a command belongs to the selected interpreter/backend."""
        ipython_commands = {"ipython_exec", "ipython_sys_exec", "ipython_kernel_restart"}
        python_commands = {"python_exec", "python_exec_file", "python_sys_exec"}
        if cmd in ipython_commands and not self.is_ipython_enabled():
            return False
        if cmd in python_commands and self.is_ipython_enabled():
            return False
        return self.get_execution_backend().supports_command(cmd)

    def migrate_docker_defaults(self) -> bool:
        """Compatibility wrapper for Docker backend default migration."""
        backend = self.execution.get_backend(SandboxMode.DOCKER)
        return backend.migrate_defaults()

    def make_temp_file_path(self, extension: str = "png"):
        """
        Make temporary file path for code execution

        :param extension: file extension
        :return: temporary file path
        """
        name = uuid.uuid4().hex + f".{extension}"
        tmp_dir = self.window.core.config.get_user_dir("tmp")
        return os.path.join(tmp_dir, name)

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
            self.cmd_syntax(data, ctx=ctx)

        elif name == Event.CMD_EXECUTE:
            self.cmd(
                ctx,
                data['commands'],
                silent,
            )

        elif name == Event.TOOL_OUTPUT_RENDER:
            if data['tool'] == self.id:
                # Input/output is already available in the dedicated Code
                # Interpreter view and in the tool chain. Do not duplicate it
                # in the message footer.
                data['html'] = ''

    def cmd_syntax(self, data: dict, ctx: CtxItem = None):
        """Expose only tools for the selected interpreter and execution backend."""
        data_dir = self.window.core.filesystem.get_data_dir(ctx=ctx)
        backend = self.get_execution_backend()
        use_ipython = self.is_ipython_enabled()

        ipython_commands = {
            "ipython_exec",
            "ipython_sys_exec",
            "ipython_kernel_restart",
        }
        python_commands = {
            "python_exec",
            "python_exec_file",
            "python_sys_exec",
        }

        for item in self.allowed_cmds:
            if not self.has_cmd(item):
                continue
            if item in ipython_commands and not use_ipython:
                continue
            if item in python_commands and use_ipython:
                continue
            if not backend.supports_command(item):
                continue

            cmd = self.get_cmd(item)
            if item in ipython_commands or item in python_commands:
                cmd["instruction"] += backend.get_tool_instruction(item, data_dir)
            data["cmd"].append(cmd)

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
            cmd = item.get("cmd")
            forced = bool(item.get("force"))
            if cmd in self.allowed_cmds and (forced or self.is_command_active(cmd)):
                my_commands.append(item)
                is_cmd = True
                if forced:
                    force = True  # call from tool

        if not is_cmd:
            return

        backend = self.get_execution_backend()
        if not backend.prepare(my_commands):
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
            worker.signals.output.connect(self.handle_interpreter_output)
            worker.signals.output_begin.connect(self.handle_interpreter_output_begin)
            worker.signals.output_end.connect(self.handle_interpreter_output_end)
            worker.signals.clear.connect(self.handle_interpreter_clear)
            worker.signals.html_output.connect(self.handle_html_output)
            worker.signals.ipython_output.connect(self.handle_ipython_output)
            # Runner/kernel signals are bound inside Worker.run() on the actual
            # worker thread. Keeping a single shared signal pointer here causes
            # races between overlapping tool calls and kernel restarts.

            if (not self.is_async(ctx) and not force) or ctx.async_disabled:
                worker.run()
                return
            worker.run_async()

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
        cleaned_data = self.get_interpreter().remove_ansi(data)
        self.window.tools.get("interpreter").append_output(cleaned_data)
        if self.window.tools.get("interpreter").is_opened():
            self.window.update_status("")

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

    @Slot(str)
    def handle_interpreter_output_begin(self, type: str):
        """
        Handle interpreter output begin

        :param type: output type
        """
        if not self.get_option_value("attach_output"):
            return
        self.window.tools.get("interpreter").output_begin(type)

    @Slot(str)
    def handle_interpreter_output_end(self, type: str):
        """
        Handle interpreter output end

        :param type: output type
        """
        if not self.get_option_value("attach_output"):
            return
        self.window.tools.get("interpreter").output_end(type)

    @Slot()
    def handle_interpreter_clear(self):
        """Handle interpreter clear"""
        if not self.get_option_value("attach_output"):
            return
        self.window.tools.get("interpreter").clear_output()

    @Slot(object)
    def handle_html_output(self, data):
        """
        Handle HTML/JS canvas output

        :param data: HTML/JS code
        """
        self.window.tools.get("html_canvas").set_output(data)
        self.window.tools.get("html_canvas").auto_open()

    @Slot(str)
    def handle_python_run(self, code: str):
        """
        Handle Python code run

        :param code: Python code to execute
        """
        cmd = "python_exec"
        if self.is_ipython_enabled():
            cmd = "ipython_exec"
            if self.get_option_value("fresh_kernel"):
                backend = self.get_execution_backend()
                # Built-in first-use provisioning must stay asynchronous under
                # the heavy-operation loader. Do not make a direct kernel
                # restart synchronously create the venv from the GUI thread.
                runtime = getattr(backend, "runtime", None)
                if runtime is None or runtime.is_ready():
                    backend.restart_ipython()
                    time.sleep(1)
        self.window.tools.get("interpreter").clear_output()
        commands = [
            {
                "cmd": cmd,
                "params": {
                    "code": code,
                    "path": ".interpreter.current.py",
                },
                "silent": True,
                "force": True,
            }
        ]
        event = Event(Event.CMD_EXECUTE, {
            'commands': commands,
            'silent': True,
        })
        event.ctx = CtxItem()  # tmp
        self.handle(event)
        self.window.tools.get("interpreter").auto_open()

    def get_interpreter(self):
        """Return the IPython kernel selected by the active execution backend."""
        if not self.is_ipython_enabled():
            return self.ipython_local
        return self.get_execution_backend().get_ipython_interpreter()
