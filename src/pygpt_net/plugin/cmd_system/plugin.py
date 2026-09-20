#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.20 11:00:00                  #
# ================================================== #

import platform

from PySide6.QtCore import Slot

from pygpt_net.plugin.base.plugin import BasePlugin
from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem
from pygpt_net.core.sandbox import BuiltinSandboxPreparer

from .config import Config
from .docker import Docker
from .execution import ExecutionManager
from .output import Output
from .runner import Runner
from .sandbox import SandboxMode


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "cmd_system"
        self.is_common_plugin = True
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
        self.execution = ExecutionManager(self)
        self.builtin_preparer = BuiltinSandboxPreparer(self, "System / OS")

    def init_options(self):
        """Initialize options"""
        self.config.from_defaults(self)

    def get_sandbox_mode(self) -> SandboxMode:
        """Return the selected System/OS execution mode."""
        if hasattr(self, "execution"):
            return self.execution.get_mode()
        value = self.get_option_value("sandbox")
        if isinstance(value, bool):
            return SandboxMode.DOCKER if value else SandboxMode.DISABLED
        if value in (None, ""):
            return SandboxMode.DISABLED
        return SandboxMode(value)

    def get_execution_backend(self):
        """Return the backend responsible for sys_exec execution."""
        return self.execution.get_backend()

    def is_sandbox_mode(self, mode: str | SandboxMode) -> bool:
        """Return True when the requested sandbox mode is selected."""
        value = mode.value if isinstance(mode, SandboxMode) else str(mode)
        return self.get_sandbox_mode().value == value

    def is_docker_sandbox(self) -> bool:
        """Return True when the Docker execution backend is selected."""
        return self.is_sandbox_mode(SandboxMode.DOCKER)

    def is_builtin_sandbox(self) -> bool:
        """Return True when the uv-managed built-in sandbox is selected."""
        return self.is_sandbox_mode(SandboxMode.BUILTIN)

    def is_sandbox_enabled(self) -> bool:
        """Return True when sys_exec uses any isolated sandbox backend."""
        return self.get_execution_backend().sandboxed

    def get_runtime_workdir(self, ctx=None) -> str:
        """Return the working directory visible to sys_exec."""
        return self.get_execution_backend().get_runtime_workdir(ctx=ctx)

    def map_host_path_to_runtime(self, path: str, ctx=None) -> str:
        """Map a host path to the namespace visible to sys_exec."""
        return self.get_execution_backend().map_host_path_to_runtime(path, ctx=ctx)

    def get_filesystem_context(self, host_data_dir: str) -> str:
        """Return model-facing filesystem guidance for the active backend."""
        return self.get_execution_backend().get_filesystem_context(host_data_dir)

    def migrate_docker_defaults(self) -> bool:
        """Compatibility wrapper for Docker backend default migration."""
        backend = self.execution.get_backend(SandboxMode.DOCKER)
        return backend.migrate_defaults()

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
                # Input/output is already represented by the tool-chain and,
                # when enabled, forwarded to the interpreter view. Do not
                # duplicate the same payload in the message footer.
                data['html'] = ''

    def cmd_syntax(self, data: dict, ctx: CtxItem = None):
        """Expose System/OS tools with guidance for the active execution backend."""
        backend = self.get_execution_backend()
        is_windows = (platform.system() == "Windows")
        winapi_enabled = self.get_option_value("winapi_enabled")

        for item in self.allowed_cmds:
            # WinAPI always targets the host Windows desktop and is independent
            # from the sys_exec sandbox backend.
            if item in self.winapi_cmds:
                if not is_windows or not winapi_enabled:
                    continue

            if not self.has_cmd(item):
                continue

            cmd = self.get_cmd(item)
            if item == "sys_exec":
                if not backend.supports_command(item):
                    continue
                if self.get_option_value("auto_cwd"):
                    cmd["instruction"] += (
                        "\nIMPORTANT: ALWAYS use absolute (not relative) path when passing "
                        "ANY command to \"command\" param. Current workdir is: {cwd}. "
                        "Current OS is: {os}"
                    ).format(
                        cwd=backend.get_runtime_workdir(ctx=ctx),
                        os=backend.get_runtime_os_name(),
                    )
                cmd["instruction"] += backend.get_tool_instruction(ctx=ctx)

            data['cmd'].append(cmd)

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
            self.runner.attach_signals(worker.signals)

            if not self.is_async(ctx) and not force:
                worker.run()
                return
            worker.run_async()

        except Exception as e:
            self.error(e)

    @Slot(object, str)
    def handle_interpreter_output(self, data, type: str):
        """Forward sys_exec output to the Python interpreter window when enabled."""
        if not self.get_option_value("attach_output"):
            return
        self.window.tools.get("interpreter").append_output(data, type)

    @Slot(str)
    def handle_interpreter_output_begin(self, type: str):
        """Begin a forwarded sys_exec output block when enabled."""
        if not self.get_option_value("attach_output"):
            return
        self.window.tools.get("interpreter").output_begin(type)

    @Slot(str)
    def handle_interpreter_output_end(self, type: str):
        """End a forwarded sys_exec output block when enabled."""
        if not self.get_option_value("attach_output"):
            return
        self.window.tools.get("interpreter").output_end(type)
