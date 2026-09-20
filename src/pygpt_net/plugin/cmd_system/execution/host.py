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

import subprocess

from .base import ExecutionBackend
from ..sandbox import SandboxMode


class HostBackend(ExecutionBackend):
    """Execute System/OS commands directly on the host."""

    mode = SandboxMode.DISABLED
    sandboxed = False
    runtime_name = "Host"

    def sys_exec(self, ctx, item: dict, request: dict) -> dict:
        runner = self.runner
        command = item["params"]["command"]

        self.plugin.window.core.security.ensure_command(command, sandbox=False)
        runner.send_interpreter_input(command)
        runner.log("Executing system command: {}".format(command))
        runner.log("Running command: {}".format(command))
        runner.send_interpreter_output_begin("stdout")
        try:
            stdout, stderr = runner._communicate_subprocess(
                command,
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
            "context": "SYS OUTPUT:\n--------------------------------\n" + runner.parse_result(result, ctx=ctx),
        }

    def get_tool_instruction(self, ctx=None) -> str:
        return "\nThe command is executed directly on the host system."
