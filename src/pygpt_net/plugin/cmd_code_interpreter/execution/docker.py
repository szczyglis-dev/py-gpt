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

from pygpt_net.utils import trans
from pygpt_net.core.docker.docker import migrate_default_dockerfile

from ..dockerfile import (
    IPYTHON_DOCKERFILE,
    IPYTHON_DOCKERFILE_LEGACY,
    IPYTHON_DOCKERFILE_PRE_BUNDLED,
    IPYTHON_DOCKERFILE_PRE_NODEJS,
    PYTHON_LEGACY_DOCKERFILE,
    PYTHON_LEGACY_DOCKERFILE_39,
    PYTHON_LEGACY_DOCKERFILE_PRE_BUNDLED,
)

from .base import ExecutionBackend
from ..sandbox import SandboxMode


class DockerBackend(ExecutionBackend):
    """Execute Code Interpreter commands inside the Docker sandbox."""

    mode = SandboxMode.DOCKER
    sandboxed = True
    log_prefix = "[DOCKER]"
    runtime_name = "Docker"
    sandbox_workdir = "/mnt/data"

    PYTHON_COMMANDS = {
        "python_exec",
        "python_exec_file",
        "python_sys_exec",
    }
    IPYTHON_COMMANDS = {
        "ipython_exec",
        "ipython_sys_exec",
        "ipython_kernel_restart",
    }

    def migrate_defaults(self) -> bool:
        """Upgrade unchanged stock Dockerfiles without overwriting custom values."""
        migrated_ipython = migrate_default_dockerfile(
            self.plugin,
            "ipython_dockerfile",
            IPYTHON_DOCKERFILE.replace("/mnt/data", "/data"),
            IPYTHON_DOCKERFILE,
        )
        if not migrated_ipython:
            migrated_ipython = migrate_default_dockerfile(
                self.plugin,
                "ipython_dockerfile",
                IPYTHON_DOCKERFILE_LEGACY,
                IPYTHON_DOCKERFILE,
            )
        if not migrated_ipython:
            migrated_ipython = migrate_default_dockerfile(
                self.plugin,
                "ipython_dockerfile",
                IPYTHON_DOCKERFILE_PRE_BUNDLED,
                IPYTHON_DOCKERFILE,
            )
        if not migrated_ipython:
            migrated_ipython = migrate_default_dockerfile(
                self.plugin,
                "ipython_dockerfile",
                IPYTHON_DOCKERFILE_PRE_NODEJS,
                IPYTHON_DOCKERFILE,
            )

        migrated_python = migrate_default_dockerfile(
            self.plugin,
            "dockerfile",
            PYTHON_LEGACY_DOCKERFILE.replace("/mnt/data", "/data"),
            PYTHON_LEGACY_DOCKERFILE,
        )
        if not migrated_python:
            migrated_python = migrate_default_dockerfile(
                self.plugin,
                "dockerfile",
                PYTHON_LEGACY_DOCKERFILE_39,
                PYTHON_LEGACY_DOCKERFILE,
            )
        if not migrated_python:
            migrated_python = migrate_default_dockerfile(
                self.plugin,
                "dockerfile",
                PYTHON_LEGACY_DOCKERFILE_PRE_BUNDLED,
                PYTHON_LEGACY_DOCKERFILE,
            )

        return migrated_ipython or migrated_python

    def prepare(self, commands: list[dict]) -> bool:
        names = {item.get("cmd") for item in commands}

        if self.plugin.is_ipython_enabled():
            if not names.intersection(self.IPYTHON_COMMANDS):
                return True
            interpreter = self.plugin.ipython_docker
            if not interpreter.is_docker_installed():
                if self.plugin.window.core.platforms.is_snap():
                    message = trans("ipython.docker.install.snap")
                else:
                    message = trans("ipython.docker.install")
                self.plugin.error(message)
                self.plugin.window.update_status(message)
                return False
            if not interpreter.is_image():
                self.plugin.error(trans("ipython.image.build"))
                self.plugin.window.update_status(trans("ipython.docker.build.start"))
                self.plugin.builder.build_image()
                return False
            return True

        if not names.intersection(self.PYTHON_COMMANDS):
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

    def get_ipython_interpreter(self):
        return self.plugin.ipython_docker

    def execute_ipython(self, data: str, ctx=None, auto_init: bool = True):
        return self.get_ipython_interpreter().execute(
            data,
            current=True,
            auto_init=auto_init,
            ctx=ctx,
        )

    def restart_ipython(self, ctx=None):
        return self.get_ipython_interpreter().restart_kernel(ctx=ctx)

    def _run(self, command: str, ctx=None) -> bytes | None:
        try:
            return self.plugin.docker.execute(command, ctx=ctx)
        except Exception as e:
            return str(e).encode("utf-8")

    def python_exec_file(self, ctx, item: dict, request: dict) -> dict:
        runner = self.runner
        path = item["params"]["path"]
        runner.log("Executing Python file: {}".format(path), sandbox=True)
        path = self.prepare_path(path, on_host=False, ctx=ctx)
        cmd = self.plugin.get_option_value("python_cmd_tpl").format(filename=path)

        runner.log("Running command: {}".format(cmd), sandbox=True)
        runner.send_interpreter_output_begin("stdout")
        response = self._run(cmd, ctx=ctx)
        result = runner.handle_result_sandbox(response)
        runner.send_interpreter_output_end("stdout")
        return {
            "request": request,
            "result": str(result),
            "context": "PYTHON OUTPUT:\n--------------------------------\n" + runner.parse_result(result, ctx=ctx),
        }

    def python_exec(self, ctx, item: dict, request: dict, all: bool = False) -> dict:
        runner = self.runner
        data = item["params"]["code"]
        if not all:
            path = self.plugin.window.tools.get("interpreter").file_current
            if "path" in item["params"]:
                path = item["params"]["path"]
            runner.log("Saving temporary Python file: {}".format(path), sandbox=True)
            with open(self.prepare_path(path, on_host=True, ctx=ctx), "w", encoding="utf-8") as file:
                file.write(data)
        else:
            path = self.plugin.window.tools.get("interpreter").file_input

        runner.append_input(data, ctx=ctx)
        runner.send_interpreter_input(data)

        path = self.prepare_path(path, on_host=False, ctx=ctx)
        runner.log("Executing Python code: {}".format(item["params"]["code"]), sandbox=True)
        cmd = self.plugin.get_option_value("python_cmd_tpl").format(filename=path)
        runner.log("Running command: {}".format(cmd), sandbox=True)
        runner.send_interpreter_output_begin("stdout")
        response = self._run(cmd, ctx=ctx)
        result = runner.handle_result_sandbox(response)
        runner.send_interpreter_output_end("stdout")
        return {
            "request": request,
            "result": str(result),
            "context": "PYTHON OUTPUT:\n--------------------------------\n" + runner.parse_result(result, ctx=ctx),
        }

    def ipython_sys_exec(self, ctx, item: dict, request: dict) -> dict:
        runner = self.runner
        command = item["params"]["command"]
        self.plugin.window.core.security.ensure_command(command, sandbox=True, os_id="linux")
        runner.log("Executing IPython system command: {}".format(command), sandbox=True, category="exec")
        runner.log("Running command: {}".format(command), sandbox=True, category="exec")
        runner.send_interpreter_input(command)
        runner.send_interpreter_output_begin("stdout")
        response = self.plugin.ipython_docker.execute_system(command, ctx=ctx)
        result = runner.handle_result_sandbox(response, log_category="exec")
        runner.send_interpreter_output_end("stdout")
        return {
            "request": request,
            "result": str(result),
            "context": "SYS OUTPUT:\n--------------------------------\n" + runner.parse_result(result, ctx=ctx),
        }

    def python_sys_exec(self, ctx, item: dict, request: dict) -> dict:
        runner = self.runner
        command = item["params"]["command"]
        self.plugin.window.core.security.ensure_command(command, sandbox=True, os_id="linux")
        runner.log("Executing legacy Python system command: {}".format(command), sandbox=True, category="exec")
        runner.log("Running command: {}".format(command), sandbox=True, category="exec")
        runner.send_interpreter_input(command)
        runner.send_interpreter_output_begin("stdout")
        response = self.plugin.docker.execute(command, ctx=ctx)
        result = runner.handle_result_sandbox(response, log_category="exec")
        runner.send_interpreter_output_end("stdout")
        return {
            "request": request,
            "result": str(result),
            "context": "SYS OUTPUT:\n--------------------------------\n" + runner.parse_result(result, ctx=ctx),
        }

    def get_runtime_workdir(self, ctx=None) -> str:
        return self.sandbox_workdir

    def map_host_path_to_runtime(self, path: str, ctx=None) -> str:
        real = os.path.realpath(path)

        # The profile tmp directory is mounted independently of the active
        # project/data directory so ephemeral artifacts remain available even
        # when img/video/download storage lives outside /mnt/data.
        tmp_dir = os.path.realpath(self.plugin.window.core.config.get_user_dir("tmp"))
        try:
            rel = os.path.relpath(real, tmp_dir)
        except ValueError:
            rel = None
        if rel is not None and rel != os.pardir and not rel.startswith(os.pardir + os.sep):
            rel = rel.replace(os.sep, "/")
            return "/mnt/tmp" if rel == "." else f"/mnt/tmp/{rel}"

        data_dir = os.path.realpath(self.plugin.window.core.filesystem.get_data_dir(ctx=ctx))
        try:
            rel = os.path.relpath(real, data_dir)
        except ValueError:
            return real.replace(os.sep, "/")
        if rel == os.pardir or rel.startswith(os.pardir + os.sep):
            return real.replace(os.sep, "/")
        rel = rel.replace(os.sep, "/")
        return self.sandbox_workdir if rel == "." else f"{self.sandbox_workdir}/{rel}"

    def get_filesystem_context(self, host_data_dir: str, use_ipython: bool) -> str:
        interpreter = "IPython" if use_ipython else "standard Python"
        tools = (
            "ipython_exec, IPython shell or magic commands, and ipython_sys_exec"
            if use_ipython
            else "python_exec/python_exec_file and python_sys_exec"
        )
        return (
            "IMPORTANT FILESYSTEM CONTEXT: "
            "The CURRENT WORKING DIRECTORY shown above is a path on the HOST filesystem. "
            "Use this host path only with host-side Files I/O tools (for example read_file, "
            "save_file, append_file, list_dir, mkdir, file_* and other Files I/O operations). "
            "The Docker Code Interpreter sandbox has a separate filesystem namespace. Never use "
            "the host CURRENT WORKING DIRECTORY path directly inside sandboxed Python, IPython "
            "or sandbox shell/system commands. "
            f"For the {interpreter} Docker sandbox, use {self.sandbox_workdir} as the working directory "
            f"inside {tools}. "
            f"The sandbox path {self.sandbox_workdir} is mapped to the same host directory: {host_data_dir}. "
            "PyGPT temporary runtime artifacts are available inside Docker below /mnt/tmp/runtime_artifacts; "
            "when a tool returns a sandbox_path for an artifact, use that path inside Docker. If no exact path "
            "was returned, inspect /mnt/tmp/runtime_artifacts recursively before using the artifact."
        )

    def get_tool_instruction(self, cmd: str, data_dir: str) -> str:
        if cmd == "ipython_sys_exec":
            message = (
                "\nThe command runs inside the same Docker container as the current IPython kernel. "
                "Directory {} is the container's workdir and is mapped on the host to: {}"
            ).format(self.sandbox_workdir, data_dir)
        elif cmd.startswith("ipython_"):
            message = (
                "\nIPython works in a Docker container. Directory {} is the container's workdir "
                "and is mapped on the host to: {}"
            ).format(self.sandbox_workdir, data_dir)
        elif cmd == "python_sys_exec":
            message = (
                "\nThe command runs inside the same Docker container as the standard Python interpreter. "
                "Directory {} is the container's workdir and is mapped on the host to: {}"
            ).format(self.sandbox_workdir, data_dir)
        elif cmd.startswith("python_"):
            message = (
                "\nPython works in a Docker container. Directory {} is the container's workdir "
                "and is mapped on the host to: {}"
            ).format(self.sandbox_workdir, data_dir)
        else:
            return ""

        message += (
            "\nProvider/tool generated or downloaded files are automatically copied below "
            "/mnt/tmp/runtime_artifacts. If an exact sandbox_path was not returned, inspect that directory "
            "recursively and use the matching file from there."
        )

        if cmd.startswith("ipython_"):
            if self.plugin.get_option_value("ipython_run_as_root"):
                message += "\nThe IPython Docker sandbox is configured to run as root. sudo is not required."
            else:
                message += (
                    "\nThe IPython Docker sandbox normally runs as the unprivileged 'pygpt' user. "
                    "Ordinary pip installs do not require root; use passwordless sudo only for operations "
                    "that require root privileges."
                )
        elif cmd.startswith("python_"):
            if self.plugin.get_option_value("docker_run_as_root"):
                message += "\nThe Python Docker sandbox is configured to run as root. sudo is not required."
            else:
                message += (
                    "\nThe Python Docker sandbox normally runs as the unprivileged 'pygpt' user. "
                    "Ordinary pip installs do not require root; use passwordless sudo only for operations "
                    "that require root privileges."
                )
        return message

    def prepare_path(self, path: str, on_host: bool = True, ctx=None) -> str:
        if on_host:
            normalized = str(path).replace("\\", "/")
            if normalized == "/mnt/tmp" or normalized.startswith("/mnt/tmp/"):
                return self.plugin.window.core.filesystem.resolve_sandbox_path(
                    "sandbox:" + normalized,
                    ctx=ctx,
                )
            mapped = self.plugin.window.core.filesystem.from_sandbox_data_path(path, ctx=ctx)
            if mapped != path:
                return mapped

        if self.is_absolute_path(path):
            return path

        if self.is_interpreter_temp_path(path):
            if on_host:
                return os.path.join(
                    self.plugin.window.core.config.get_user_dir("tmp"),
                    path,
                )
            return "/mnt/tmp/{}".format(path.replace("\\", "/"))

        if on_host:
            return os.path.join(
                self.plugin.window.core.filesystem.get_data_dir(ctx=ctx),
                path,
            )
        return path
