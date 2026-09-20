#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.20 14:35:00                  #
# ================================================== #

import os

from pygpt_net.core.docker.docker import migrate_default_dockerfile
from pygpt_net.utils import trans

from .base import ExecutionBackend
from ..dockerfile import SYSTEM_DOCKERFILE, SYSTEM_DOCKERFILE_39
from ..sandbox import SandboxMode


class DockerBackend(ExecutionBackend):
    """Execute System/OS commands inside the Docker sandbox."""

    mode = SandboxMode.DOCKER
    sandboxed = True
    log_prefix = "[DOCKER]"
    runtime_name = "Docker"
    sandbox_workdir = "/mnt/data"

    def migrate_defaults(self) -> bool:
        """Upgrade unchanged stock Dockerfiles without overwriting custom values."""
        migrated = migrate_default_dockerfile(
            self.plugin,
            "dockerfile",
            SYSTEM_DOCKERFILE.replace("/mnt/data", "/data"),
            SYSTEM_DOCKERFILE,
        )
        if not migrated:
            migrated = migrate_default_dockerfile(
                self.plugin,
                "dockerfile",
                SYSTEM_DOCKERFILE_39,
                SYSTEM_DOCKERFILE,
            )
        return migrated

    def prepare(self, commands: list[dict]) -> bool:
        """Ensure Docker and the configured System sandbox image are ready."""
        if not any(item.get("cmd") == "sys_exec" for item in commands):
            return True

        docker = self.plugin.docker
        if not docker.is_docker_installed():
            if self.plugin.window.core.platforms.is_snap():
                message = trans("docker.install.snap")
            else:
                message = trans("docker.install")
            self.plugin.error(message)
            self.plugin.window.update_status(message)
            return False

        if not docker.is_image():
            self.plugin.error(trans("docker.image.build"))
            self.plugin.window.update_status(trans("docker.build.start"))
            docker.build()
            return False

        return True

    def sys_exec(self, ctx, item: dict, request: dict) -> dict:
        runner = self.runner
        command = item["params"]["command"]
        self.plugin.window.core.security.ensure_command(command, sandbox=True, os_id="linux")

        runner.send_interpreter_input(command)
        runner.log("Executing system command: {}".format(command), prefix=self.log_prefix)
        runner.log("Running command: {}".format(command), prefix=self.log_prefix)
        runner.send_interpreter_output_begin("stdout")
        try:
            response = self.plugin.docker.execute(command, ctx=ctx)
        except Exception as e:
            response = str(e).encode("utf-8")

        result = runner.handle_result_sandbox(response, prefix=self.log_prefix)
        runner.send_interpreter_output_end("stdout")
        return {
            "request": request,
            "result": str(result),
            "context": "SYS OUTPUT:\n--------------------------------\n" + runner.parse_result(result, ctx=ctx),
        }

    def get_runtime_workdir(self, ctx=None) -> str:
        return self.sandbox_workdir

    def get_runtime_os_name(self) -> str:
        return "Linux (Docker container)"

    def map_host_path_to_runtime(self, path: str, ctx=None) -> str:
        data_dir = os.path.realpath(self.plugin.window.core.filesystem.get_data_dir(ctx=ctx))
        real = os.path.realpath(path)
        try:
            rel = os.path.relpath(real, data_dir)
        except ValueError:
            return path
        if rel == os.pardir or rel.startswith(os.pardir + os.sep):
            return path
        rel = rel.replace(os.sep, "/")
        return self.sandbox_workdir if rel == "." else f"{self.sandbox_workdir}/{rel}"

    def prepare_path(self, path: str, on_host: bool = True, ctx=None) -> str:
        if not path:
            return path

        if on_host:
            mapped = self.plugin.window.core.filesystem.from_sandbox_data_path(path, ctx=ctx)
            if mapped != path:
                return mapped
            if os.path.isabs(path):
                return path
            return os.path.join(
                self.plugin.window.core.filesystem.get_data_dir(ctx=ctx),
                path,
            )

        if path == self.sandbox_workdir or path.startswith(self.sandbox_workdir + "/"):
            return path
        if os.path.isabs(path):
            return path
        return f"{self.sandbox_workdir}/{path.lstrip('/')}"

    def get_tool_instruction(self, ctx=None) -> str:
        message = (
            "\nThe command is executed inside the Docker sandbox. "
            f"Use {self.sandbox_workdir} as the sandbox working directory; it is mapped to the current host data directory."
        )
        if self.plugin.get_option_value("docker_run_as_root"):
            message += " The Docker sandbox is configured to run as root; sudo is not required."
        else:
            message += (
                " The Docker sandbox normally runs as the unprivileged 'pygpt' user. "
                "Use sudo only for commands that require root privileges; sudo is passwordless."
            )
        return message

    def get_filesystem_context(self, host_data_dir: str) -> str:
        return (
            "The System/OS Docker sandbox has a separate filesystem namespace. "
            f"Use {self.sandbox_workdir} as the working directory inside the sandbox. "
            f"It is mapped to the host directory: {host_data_dir}"
        )
