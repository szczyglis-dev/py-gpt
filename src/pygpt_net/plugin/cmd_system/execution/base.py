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

from __future__ import annotations

import os

from ..sandbox import SandboxMode


class ExecutionBackend:
    """Base execution backend used by the System/OS plugin."""

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
        return cmd == "sys_exec"

    def sys_exec(self, ctx, item: dict, request: dict) -> dict:
        """Execute a system command using this backend."""
        raise NotImplementedError

    def get_runtime_workdir(self, ctx=None) -> str:
        """Return the working directory visible to commands in this backend."""
        return self.plugin.window.core.filesystem.get_data_dir(ctx=ctx)

    def get_runtime_os_name(self) -> str:
        """Return a model-facing description of the runtime operating system."""
        return self.plugin.window.core.platforms.get_as_string(env_suffix=False)

    def map_host_path_to_runtime(self, path: str, ctx=None) -> str:
        """Map a host path to the namespace visible to this backend."""
        return os.path.realpath(path)

    def prepare_path(self, path: str, on_host: bool = True, ctx=None) -> str:
        """Translate a tool/runtime path for this backend."""
        if not path:
            return path
        if os.path.isabs(path):
            return path
        return os.path.join(
            self.plugin.window.core.filesystem.get_data_dir(ctx=ctx),
            path,
        )

    def get_tool_instruction(self, ctx=None) -> str:
        """Return optional backend-specific guidance appended to sys_exec."""
        return ""

    def get_filesystem_context(self, host_data_dir: str) -> str:
        """Return optional model guidance for this backend's filesystem namespace."""
        return ""
