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

from __future__ import annotations

import os

from ..sandbox import SandboxMode


class ExecutionBackend:
    """Base execution backend used by the Code Interpreter plugin."""

    mode = SandboxMode.DISABLED
    sandboxed = False
    log_prefix = ""
    runtime_name = "Host"
    sandbox_workdir = None

    def __init__(self, plugin=None):
        self.plugin = plugin

    @property
    def runner(self):
        return self.plugin.runner

    def prepare(self, commands: list[dict]) -> bool:
        """Prepare backend before command execution. Return False to abort."""
        return True

    def supports_command(self, cmd: str) -> bool:
        """Return whether this backend supports the requested command."""
        return True

    def consume_preparing_response(self, request: dict):
        """Return a first-use preparation response, or None when ready."""
        return None

    def get_ipython_interpreter(self):
        """Return the IPython kernel implementation for this backend."""
        return self.plugin.ipython_local

    def execute_ipython(self, data: str, ctx=None, auto_init: bool = True):
        """Execute code using this backend's IPython kernel."""
        return self.get_ipython_interpreter().execute(
            data,
            current=True,
            auto_init=auto_init,
        )

    def restart_ipython(self, ctx=None):
        """Restart this backend's IPython kernel."""
        return self.get_ipython_interpreter().restart_kernel()

    def python_exec(self, ctx, item: dict, request: dict, all: bool = False) -> dict:
        raise NotImplementedError

    def python_exec_file(self, ctx, item: dict, request: dict) -> dict | None:
        raise NotImplementedError

    def python_sys_exec(self, ctx, item: dict, request: dict) -> dict:
        raise NotImplementedError

    def ipython_sys_exec(self, ctx, item: dict, request: dict) -> dict:
        raise NotImplementedError

    def get_runtime_workdir(self, ctx=None) -> str:
        """Return the workdir visible to commands executed by this backend."""
        return self.plugin.window.core.filesystem.get_data_dir(ctx=ctx)

    def map_host_path_to_runtime(self, path: str, ctx=None) -> str:
        """Map a host path to the namespace visible to this backend."""
        return os.path.realpath(path)

    def get_filesystem_context(self, host_data_dir: str, use_ipython: bool) -> str:
        """Return optional model guidance for this backend's filesystem namespace."""
        return ""

    def get_tool_instruction(self, cmd: str, data_dir: str) -> str:
        """Return backend-specific runtime guidance appended to a tool description."""
        return ""

    def prepare_path(self, path: str, on_host: bool = True, ctx=None) -> str:
        """Translate a tool/runtime path for this backend."""
        if self.is_absolute_path(path):
            return path

        if self.is_interpreter_temp_path(path):
            return os.path.join(
                self.plugin.window.core.config.get_user_dir("tmp"),
                path,
            )

        return os.path.join(
            self.plugin.window.core.filesystem.get_data_dir(ctx=ctx),
            path,
        )

    @staticmethod
    def is_absolute_path(path: str) -> bool:
        return os.path.isabs(path)

    def is_interpreter_temp_path(self, path: str) -> bool:
        """Check whether path is one of the interpreter's internal temporary files."""
        if not path or self.is_absolute_path(path):
            return False
        name = os.path.normpath(path).replace("\\", "/")
        interpreter = self.plugin.window.tools.get("interpreter")
        return name in {
            interpreter.file_current,
            interpreter.file_input,
            interpreter.file_output,
            interpreter.file_output_json,
        }
