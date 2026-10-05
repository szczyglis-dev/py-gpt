#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.02 14:00:00                  #
# ================================================== #

import os
import threading

from pygpt_net.core.sandbox import BuiltinSandboxRuntime
from ..ipython import BuiltinKernel

from pygpt_net.plugin.base.execution import execution_response

from .base import ExecutionBackend
from ..sandbox import SandboxMode


class BuiltinBackend(ExecutionBackend):
    """Execute standard Python commands in the uv-managed built-in sandbox."""

    mode = SandboxMode.BUILTIN
    sandboxed = True
    log_prefix = "[BUILT-IN]"
    runtime_name = "Built-in sandbox"

    IPYTHON_COMMANDS = {
        "ipython_exec",
        "ipython_sys_exec",
        "ipython_kernel_restart",
    }

    PREPARING_MESSAGE = (
        "Venv is preparing. Stop execution for now and inform the user that the "
        "Built-in sandbox environment is being prepared. Ask the user to retry "
        "the command after preparation finishes."
    )

    def __init__(self, plugin=None):
        super().__init__(plugin)
        self.runtime = BuiltinSandboxRuntime(
            plugin.window,
            "python",
            packages_provider=plugin.get_builtin_packages,
        )
        self.ipython = BuiltinKernel(plugin, self.runtime)
        self._defer_lock = threading.RLock()
        self._defer_count = 0

    def prepare(self, commands: list[dict]) -> bool:
        """Start first-use provisioning but let the worker return a tool response."""
        if self.runtime.is_ready():
            return True
        if self.ipython.initialized:
            self.ipython.shutdown_kernel()
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
        response = execution_response(request, stdout=self.PREPARING_MESSAGE, context=self.PREPARING_MESSAGE)
        response['builtin_sandbox_preparing'] = True
        return response

    def supports_command(self, cmd: str) -> bool:
        return True

    def consume_preparing_response(self, request: dict):
        """Return the first-use response for runner-managed IPython commands."""
        if self._must_defer():
            return self._preparing_response(request)
        return None

    def get_ipython_interpreter(self):
        return self.ipython

    def execute_ipython(self, data: str, ctx=None, auto_init: bool = True):
        return self.ipython.execute(
            data,
            current=True,
            auto_init=auto_init,
            ctx=ctx,
        )

    def restart_ipython(self, ctx=None):
        return self.ipython.restart_kernel(ctx=ctx)

    def prepare_path(self, path: str, on_host: bool = True, ctx=None) -> str:
        if self.is_interpreter_temp_path(path):
            return self.runtime.temp_path(path)
        return self.runtime.resolve_data_path(path, ctx=ctx)

    def python_exec_file(self, ctx, item: dict, request: dict) -> dict | None:
        if self._must_defer():
            return self._preparing_response(request)
        runner = self.runner
        path = self.prepare_path(item["params"]["path"], on_host=True, ctx=ctx)
        self.plugin.window.core.security.ensure_read(path, sandbox=True, ctx=ctx)
        if not os.path.isfile(path):
            return execution_response(request, stderr="File not found")

        runner.log(f"Executing Python file: {path}", sandbox=True)
        runner.send_interpreter_output_begin("stdout")
        process_output = None
        try:
            process_output = self.runtime.run_python(path, ctx=ctx)
            stdout, stderr = process_output
        except Exception as exc:
            runner.error(exc)
            stdout = None
            stderr = str(exc).encode("utf-8")
        result = runner.handle_result(stdout, stderr)
        runner.send_interpreter_output_end("stdout")
        return execution_response(
            request, stdout, stderr, getattr(process_output, "return_code", None),
            context="PYTHON OUTPUT:\n--------------------------------\n" + runner.parse_result(result, ctx=ctx),
        )

    def python_exec(self, ctx, item: dict, request: dict, all: bool = False) -> dict:
        if self._must_defer():
            return self._preparing_response(request)
        runner = self.runner
        data = item["params"]["code"]
        if all:
            requested_path = self.plugin.window.tools.get("interpreter").file_input
        else:
            requested_path = item["params"].get(
                "path",
                self.plugin.window.tools.get("interpreter").file_current,
            )

        with self.plugin.reserve_interpreter_current_file(requested_path) as (path, fallback):
            host_path = self.prepare_path(path, on_host=True, ctx=ctx)
            if not all:
                self.plugin.window.core.security.ensure_write(host_path, sandbox=True, ctx=ctx)
                os.makedirs(os.path.dirname(host_path), exist_ok=True)
                if fallback:
                    runner.log(
                        f"Shared interpreter file busy; using isolated temporary Python file: {path}",
                        sandbox=True,
                    )
                runner.log(f"Saving temporary Python file: {host_path}", sandbox=True)
                with open(host_path, "w", encoding="utf-8") as handle:
                    handle.write(data)
            else:
                self.plugin.window.core.security.ensure_read(host_path, sandbox=True, ctx=ctx)

            runner.append_input(data, ctx=ctx)
            runner.send_interpreter_input(data)
            runner.log(f"Running built-in Python: {host_path}", sandbox=True)
            runner.send_interpreter_output_begin("stdout")
            process_output = None
            try:
                process_output = self.runtime.run_python(host_path, ctx=ctx)
                stdout, stderr = process_output
            except Exception as exc:
                runner.error(exc)
                stdout = None
                stderr = str(exc).encode("utf-8")
            result = runner.handle_result(stdout, stderr)
            runner.send_interpreter_output_end("stdout")

        return execution_response(
            request, stdout, stderr, getattr(process_output, "return_code", None),
            context="PYTHON OUTPUT:\n--------------------------------\n" + runner.parse_result(result, ctx=ctx),
        )

    def python_sys_exec(self, ctx, item: dict, request: dict) -> dict:
        if self._must_defer():
            return self._preparing_response(request)
        runner = self.runner
        command = item["params"]["command"]
        self.plugin.window.core.security.ensure_command(command, sandbox=True)
        runner.send_interpreter_input(command)
        runner.log(f"Executing Python environment system command: {command}", sandbox=True, category="exec")
        runner.send_interpreter_output_begin("stdout")
        process_output = None
        try:
            process_output = self.runtime.run_shell(command, ctx=ctx)
            stdout, stderr = process_output
        except Exception as exc:
            runner.error(exc)
            stdout = None
            stderr = str(exc).encode("utf-8")
        result = runner.handle_result(stdout, stderr, log_category="exec")
        runner.send_interpreter_output_end("stdout")
        return execution_response(
            request, stdout, stderr, getattr(process_output, "return_code", None),
            context="SYS OUTPUT:\n--------------------------------\n" + runner.parse_result(result, ctx=ctx),
        )

    def ipython_sys_exec(self, ctx, item: dict, request: dict) -> dict:
        if self._must_defer():
            return self._preparing_response(request)
        runner = self.runner
        command = item["params"]["command"]
        self.plugin.window.core.security.ensure_command(command, sandbox=True)
        runner.send_interpreter_input(command)
        runner.log(f"Executing Built-in IPython system command: {command}", sandbox=True, category="exec")
        runner.send_interpreter_output_begin("stdout")
        process_output = None
        try:
            process_output = self.runtime.run_shell(command, ctx=ctx)
            stdout, stderr = process_output
        except Exception as exc:
            runner.error(exc)
            stdout = None
            stderr = str(exc).encode("utf-8")
        result = runner.handle_result(stdout, stderr, log_category="exec")
        runner.send_interpreter_output_end("stdout")
        return execution_response(
            request, stdout, stderr, getattr(process_output, "return_code", None),
            context="SYS OUTPUT:\n--------------------------------\n" + runner.parse_result(result, ctx=ctx),
        )

    def get_runtime_workdir(self, ctx=None) -> str:
        return self.runtime.get_data_dir(ctx=ctx)

    def map_host_path_to_runtime(self, path: str, ctx=None) -> str:
        # Unlike Docker there is no synthetic filesystem namespace; paths map
        # directly to the host filesystem.
        return self.runtime.resolve_data_path(path, ctx=ctx)

    def get_tool_instruction(self, *args, **kwargs):
        """Runtime guidance is emitted once by the integrated plugin."""
        return ""

    def get_filesystem_context(self, *args, **kwargs):
        """Runtime guidance is emitted once by the integrated plugin."""
        return ""
