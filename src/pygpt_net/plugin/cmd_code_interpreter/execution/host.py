#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.22 18:00:00                  #
# ================================================== #

import os.path
import subprocess

from .base import ExecutionBackend
from ..sandbox import SandboxMode


class HostBackend(ExecutionBackend):
    """Execute Code Interpreter commands directly on the host."""

    mode = SandboxMode.DISABLED
    sandboxed = False

    @staticmethod
    def _communicate_subprocess(command, **kwargs):
        """Run a subprocess without allowing an implicit interactive stdin."""
        input_data = kwargs.pop("input", None)
        has_input = input_data is not None

        if has_input:
            if "stdin" in kwargs:
                raise ValueError("stdin and input arguments may not both be used")
            kwargs["stdin"] = subprocess.PIPE
        elif "stdin" not in kwargs:
            kwargs["stdin"] = subprocess.DEVNULL

        process = subprocess.Popen(command, **kwargs)
        if has_input:
            return process.communicate(input=input_data)
        return process.communicate()

    def _run_system_command(self, ctx, command: str, request: dict, label: str) -> dict:
        runner = self.runner
        self.plugin.window.core.security.ensure_command(command, sandbox=False)
        runner.log("Executing {} system command: {}".format(label, command), category="exec")
        runner.log("Running command: {}".format(command), category="exec")
        runner.send_interpreter_input(command)
        try:
            runner.send_interpreter_output_begin("stdout")
            stdout, stderr = self._communicate_subprocess(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except Exception as e:
            runner.error(e)
            stdout = None
            stderr = str(e).encode("utf-8")
        result = runner.handle_result(stdout, stderr, log_category="exec")
        runner.send_interpreter_output_end("stdout")
        return {
            "request": request,
            "result": str(result),
            "context": "SYS OUTPUT:\n--------------------------------\n" + runner.parse_result(result, ctx=ctx),
        }

    def python_exec_file(self, ctx, item: dict, request: dict) -> dict | None:
        runner = self.runner
        runner.log("Executing Python file: {}".format(item["params"]["path"]))
        path = self.prepare_path(item["params"]["path"], on_host=True, ctx=ctx)
        self.plugin.window.core.security.ensure_read(path, sandbox=False, ctx=ctx)

        if not os.path.isfile(path):
            return {
                "request": request,
                "result": "File not found",
            }

        cmd = self.plugin.get_option_value("python_cmd_tpl").format(filename=path)
        self.plugin.window.core.security.ensure_command(cmd, sandbox=False)
        runner.log("Running command: {}".format(cmd))
        try:
            runner.send_interpreter_output_begin("stdout")
            stdout, stderr = self._communicate_subprocess(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except Exception as e:
            runner.error(e)
            stdout = None
            stderr = str(e).encode("utf-8")
        result = runner.handle_result(stdout, stderr)
        runner.send_interpreter_output_end("stdout")
        return {
            "request": request,
            "result": str(result),
            "context": "PYTHON OUTPUT:\n--------------------------------\n" + runner.parse_result(result, ctx=ctx),
        }

    def python_exec(self, ctx, item: dict, request: dict, all: bool = False) -> dict:
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
                self.plugin.window.core.security.ensure_write(host_path, sandbox=False, ctx=ctx)
                if fallback:
                    runner.log("Shared interpreter file busy; using isolated temporary Python file: {}".format(path))
                runner.log("Saving temporary Python file: {}".format(host_path))
                with open(host_path, "w", encoding="utf-8") as file:
                    file.write(data)
            else:
                self.plugin.window.core.security.ensure_read(host_path, sandbox=False, ctx=ctx)

            runner.append_input(data, ctx=ctx)
            runner.send_interpreter_input(data)

            cmd = self.plugin.get_option_value("python_cmd_tpl").format(filename=host_path)
            self.plugin.window.core.security.ensure_command(cmd, sandbox=False)
            runner.log("Running command: {}".format(cmd))
            try:
                runner.send_interpreter_output_begin("stdout")
                stdout, stderr = self._communicate_subprocess(
                    cmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            except Exception as e:
                runner.error(e)
                stdout = None
                stderr = str(e).encode("utf-8")
            result = runner.handle_result(stdout, stderr)
            runner.send_interpreter_output_end("stdout")

        return {
            "request": request,
            "result": str(result),
            "context": "PYTHON OUTPUT:\n--------------------------------\n" + runner.parse_result(result, ctx=ctx),
        }

    def ipython_sys_exec(self, ctx, item: dict, request: dict) -> dict:
        return self._run_system_command(
            ctx,
            item["params"]["command"],
            request,
            "IPython",
        )

    def python_sys_exec(self, ctx, item: dict, request: dict) -> dict:
        return self._run_system_command(
            ctx,
            item["params"]["command"],
            request,
            "legacy Python",
        )

    def get_tool_instruction(self, cmd: str, data_dir: str) -> str:
        runtime_artifacts = self.plugin.window.core.filesystem.get_runtime_artifacts_dir(create=False)
        suffix = (
            f" Provider/tool generated or downloaded files are automatically copied under {runtime_artifacts}. "
            "If an exact path was not returned, inspect that directory recursively before using the file."
        )
        if cmd == "ipython_sys_exec":
            return (
                "\nThe command runs on the host system, in the same host environment used by the "
                "local IPython interpreter. The application data directory is: {}".format(data_dir)
                + suffix
            )
        if cmd.startswith("ipython_"):
            return (
                "\nIPython works in the local environment. Directory {} is the workdir; "
                "use it by default to save files.".format(data_dir)
                + suffix
            )
        if cmd == "python_sys_exec":
            return (
                "\nThe command runs on the host system, in the same host environment used by the "
                "standard Python interpreter. The application data directory is: {}".format(data_dir)
                + suffix
            )
        if cmd.startswith("python_"):
            return (
                "\nPython works in the local environment. Directory {} is the workdir; "
                "use it by default to save files.".format(data_dir)
                + suffix
            )
        return ""
