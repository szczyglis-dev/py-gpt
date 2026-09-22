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

import os
import threading

from pygpt_net.core.sandbox import BuiltinSandboxRuntime
from ..ipython import BuiltinKernel

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
        return {
            "request": request,
            "result": self.PREPARING_MESSAGE,
            "context": self.PREPARING_MESSAGE,
            "builtin_sandbox_preparing": True,
        }

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
            return {"request": request, "result": "File not found"}

        runner.log(f"Executing Python file: {path}", sandbox=True)
        runner.send_interpreter_output_begin("stdout")
        try:
            stdout, stderr = self.runtime.run_python(path, ctx=ctx)
        except Exception as exc:
            runner.error(exc)
            stdout = None
            stderr = str(exc).encode("utf-8")
        result = runner.handle_result(stdout, stderr)
        runner.send_interpreter_output_end("stdout")
        return {
            "request": request,
            "result": str(result),
            "context": "PYTHON OUTPUT:\n--------------------------------\n" + runner.parse_result(result, ctx=ctx),
        }

    def python_exec(self, ctx, item: dict, request: dict, all: bool = False) -> dict:
        if self._must_defer():
            return self._preparing_response(request)
        runner = self.runner
        data = item["params"]["code"]
        if not all:
            path = self.plugin.window.tools.get("interpreter").file_current
            if "path" in item["params"]:
                path = item["params"]["path"]
            path = self.prepare_path(path, on_host=True, ctx=ctx)
            self.plugin.window.core.security.ensure_write(path, sandbox=True, ctx=ctx)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            runner.log(f"Saving temporary Python file: {path}", sandbox=True)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(data)
        else:
            path = self.prepare_path(
                self.plugin.window.tools.get("interpreter").file_input,
                on_host=True,
                ctx=ctx,
            )
            self.plugin.window.core.security.ensure_read(path, sandbox=True, ctx=ctx)

        runner.append_input(data, ctx=ctx)
        runner.send_interpreter_input(data)
        runner.log(f"Running built-in Python: {path}", sandbox=True)
        runner.send_interpreter_output_begin("stdout")
        try:
            stdout, stderr = self.runtime.run_python(path, ctx=ctx)
        except Exception as exc:
            runner.error(exc)
            stdout = None
            stderr = str(exc).encode("utf-8")
        result = runner.handle_result(stdout, stderr)
        runner.send_interpreter_output_end("stdout")
        return {
            "request": request,
            "result": str(result),
            "context": "PYTHON OUTPUT:\n--------------------------------\n" + runner.parse_result(result, ctx=ctx),
        }

    def python_sys_exec(self, ctx, item: dict, request: dict) -> dict:
        if self._must_defer():
            return self._preparing_response(request)
        runner = self.runner
        command = item["params"]["command"]
        self.plugin.window.core.security.ensure_command(command, sandbox=True)
        runner.send_interpreter_input(command)
        runner.log(f"Executing Python environment system command: {command}", sandbox=True, category="exec")
        runner.send_interpreter_output_begin("stdout")
        try:
            stdout, stderr = self.runtime.run_shell(command, ctx=ctx)
        except Exception as exc:
            runner.error(exc)
            stdout = None
            stderr = str(exc).encode("utf-8")
        result = runner.handle_result(stdout, stderr, log_category="exec")
        runner.send_interpreter_output_end("stdout")
        return {
            "request": request,
            "result": str(result),
            "context": "SYS OUTPUT:\n--------------------------------\n" + runner.parse_result(result, ctx=ctx),
        }

    def ipython_sys_exec(self, ctx, item: dict, request: dict) -> dict:
        if self._must_defer():
            return self._preparing_response(request)
        runner = self.runner
        command = item["params"]["command"]
        self.plugin.window.core.security.ensure_command(command, sandbox=True)
        runner.send_interpreter_input(command)
        runner.log(f"Executing Built-in IPython system command: {command}", sandbox=True, category="exec")
        runner.send_interpreter_output_begin("stdout")
        try:
            stdout, stderr = self.runtime.run_shell(command, ctx=ctx)
        except Exception as exc:
            runner.error(exc)
            stdout = None
            stderr = str(exc).encode("utf-8")
        result = runner.handle_result(stdout, stderr, log_category="exec")
        runner.send_interpreter_output_end("stdout")
        return {
            "request": request,
            "result": str(result),
            "context": "SYS OUTPUT:\n--------------------------------\n" + runner.parse_result(result, ctx=ctx),
        }

    def get_runtime_workdir(self, ctx=None) -> str:
        return self.runtime.get_data_dir(ctx=ctx)

    def map_host_path_to_runtime(self, path: str, ctx=None) -> str:
        # Unlike Docker there is no synthetic filesystem namespace; paths map
        # directly to the host filesystem.
        return self.runtime.resolve_data_path(path, ctx=ctx)

    def get_tool_instruction(self, cmd: str, data_dir: str) -> str:
        runtime_artifacts = self.plugin.window.core.filesystem.get_runtime_artifacts_dir(create=False)
        suffix = (
            f" Provider/tool generated or downloaded files are automatically copied under {runtime_artifacts}. "
            "If an exact host/runtime path was not returned, inspect that directory recursively before using the file."
        )
        if cmd in {"python_sys_exec", "ipython_sys_exec"}:
            return (
                "\nThe command runs in PyGPT's built-in uv-managed Python sandbox. "
                f"Its CWD is {data_dir}; the sandbox virtual environment is {self.runtime.venv_root}. "
                "Use pip or python -m pip from this environment for packages needed by executed code."
                + suffix
            )
        if cmd.startswith("ipython_"):
            return (
                "\nIPython runs as a persistent kernel inside PyGPT's built-in uv-managed sandbox. "
                f"Use {data_dir} as the working directory and save user files there. "
                "Kernel state is preserved between executions until the kernel is restarted."
                + suffix
            )
        if cmd.startswith("python_"):
            return (
                "\nPython runs as a separate process in PyGPT's built-in uv-managed sandbox. "
                f"Use {data_dir} as the working directory and save user files there."
                + suffix
            )
        return ""

    def get_filesystem_context(self, host_data_dir: str, use_ipython: bool) -> str:
        return self.runtime.filesystem_context(host_data_dir)
