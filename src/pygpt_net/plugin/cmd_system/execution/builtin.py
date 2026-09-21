#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.20 12:00:00                  #
# ================================================== #

import platform
import threading

from pygpt_net.core.sandbox import BuiltinSandboxRuntime

from .base import ExecutionBackend
from ..sandbox import SandboxMode


class BuiltinBackend(ExecutionBackend):
    """Execute System/OS commands in a dedicated uv-managed environment."""

    mode = SandboxMode.BUILTIN
    sandboxed = True
    log_prefix = "[BUILT-IN]"
    runtime_name = "Built-in sandbox"

    PREPARING_MESSAGE = (
        "Venv is preparing. Stop execution for now and inform the user that the "
        "Built-in sandbox environment is being prepared. Ask the user to retry "
        "the command after preparation finishes."
    )

    def __init__(self, plugin=None):
        super().__init__(plugin)
        self.runtime = BuiltinSandboxRuntime(
            plugin.window,
            "os",
            packages_provider=plugin.get_builtin_packages,
        )
        self._defer_lock = threading.RLock()
        self._defer_count = 0

    def prepare(self, commands: list[dict]) -> bool:
        if self.runtime.is_ready():
            return True
        with self._defer_lock:
            self._defer_count += len(commands)
        self.plugin.builtin_preparer.prepare(self.runtime)
        return True

    def _must_defer(self) -> bool:
        with self._defer_lock:
            if self._defer_count > 0:
                self._defer_count -= 1
                return True
        return not self.runtime.is_ready()

    def _preparing_response(self, request: dict) -> dict:
        self.plugin.builtin_preparer.prepare(self.runtime)
        return {
            "request": request,
            "result": self.PREPARING_MESSAGE,
            "context": self.PREPARING_MESSAGE,
            "builtin_sandbox_preparing": True,
        }

    def sys_exec(self, ctx, item: dict, request: dict) -> dict:
        if self._must_defer():
            return self._preparing_response(request)
        runner = self.runner
        command = item["params"]["command"]
        self.plugin.window.core.security.ensure_command(command, sandbox=True)
        runner.send_interpreter_input(command)
        runner.log(f"Executing system command: {command}", prefix=self.log_prefix)
        runner.log(f"Running command: {command}", prefix=self.log_prefix)
        runner.send_interpreter_output_begin("stdout")
        try:
            stdout, stderr = self.runtime.run_shell(command, ctx=ctx)
        except Exception as exc:
            runner.error(exc)
            stdout = None
            stderr = str(exc).encode("utf-8")
        result = runner.handle_result(stdout, stderr)
        runner.send_interpreter_output_end("stdout")
        return {
            "request": request,
            "result": str(result),
            "context": "SYS OUTPUT:\n--------------------------------\n" + runner.parse_result(result, ctx=ctx),
        }

    def get_runtime_workdir(self, ctx=None) -> str:
        return self.runtime.get_data_dir(ctx=ctx)

    def get_runtime_os_name(self) -> str:
        return f"{platform.system()} (PyGPT built-in sandbox)"

    def map_host_path_to_runtime(self, path: str, ctx=None) -> str:
        return self.runtime.resolve_data_path(path, ctx=ctx)

    def prepare_path(self, path: str, on_host: bool = True, ctx=None) -> str:
        if not path:
            return path
        return self.runtime.resolve_data_path(path, ctx=ctx)

    def get_tool_instruction(self, ctx=None) -> str:
        data_dir = self.runtime.get_data_dir(ctx=ctx)
        return (
            "\nThe command is executed as a separate process in PyGPT's built-in sandbox. "
            f"Its CWD is {data_dir}; its dedicated virtual environment is {self.runtime.venv_root}. "
            f"Isolation: {self.runtime.isolation_name()}."
        )

    def get_filesystem_context(self, host_data_dir: str) -> str:
        return self.runtime.filesystem_context(host_data_dir)
