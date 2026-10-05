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

from pygpt_net.plugin.base.config import BaseConfig, BasePlugin
from pygpt_net.core.sandbox import BUILTIN_PYTHON_PACKAGES, builtin_packages_to_text


from .dockerfile import IPYTHON_DOCKERFILE, PYTHON_LEGACY_DOCKERFILE
from .sandbox import SandboxMode


class Config(BaseConfig):
    def __init__(self, plugin: BasePlugin = None, *args, **kwargs):
        super(Config, self).__init__(plugin)
        self.plugin = plugin

    def from_defaults(self, plugin: BasePlugin = None):
        """
        Set default options for plugin

        :param plugin: plugin instance
        """
        dockerfile = IPYTHON_DOCKERFILE
        dockerfile_legacy = PYTHON_LEGACY_DOCKERFILE

        plugin.add_option(
            "use_ipython",
            type="bool",
            value=True,
            label="Use IPython",
            description="Use the IPython interpreter. When disabled, use the standard Python interpreter.",
            tab="general",
        )
        plugin.add_option(
            "sandbox",
            type="combo",
            value=SandboxMode.BUILTIN.value,
            label="Sandbox",
            description="Disabled runs Python/IPython directly on the host (unsafe). Built-in runs a dedicated uv-managed CPython/IPython environment in a separate process, but does not restrict access to the host filesystem. Docker requires Docker to be installed and running and provides the strongest isolation; it is the safest option. System-command whitelist/blacklist rules apply to the dedicated system-command tools in every execution mode.",
            keys=SandboxMode.options(),
            tab="general",
        )
        plugin.add_option(
            "builtin_packages",
            type="textarea",
            value=builtin_packages_to_text(BUILTIN_PYTHON_PACKAGES),
            label="Packages to install",
            description="Python package requirements installed in the Built-in sandbox. Enter one package specification per line. Re-create the Built-in venv to apply changes immediately; otherwise it will be recreated automatically on the next Built-in sandbox use.",
            tab="builtin_sandbox",
        )
        plugin.add_option(
            "ipython_run_as_root",
            type="bool",
            value=False,
            label="Run as root",
            description="Run the IPython Docker sandbox as root. When disabled, the stock sandbox image runs as "
                        "the unprivileged 'pygpt' user and passwordless sudo can be used for commands that require "
                        "root privileges.",
            tab="ipython",
        )
        plugin.add_option(
            "ipython_dockerfile",
            type="textarea",
            value=dockerfile,
            label="Dockerfile for IPython kernel",
            description="Dockerfile used to build IPython kernel container image",
            tooltip="Dockerfile",
            tab="ipython",
        )
        plugin.add_option(
            "ipython_image_name",
            type="text",
            value='pygpt_ipython_kernel',
            label="Docker image name",
            tab="ipython",
        )
        plugin.add_option(
            "ipython_container_name",
            type="text",
            value='pygpt_ipython_kernel_container',
            label="Docker container name",
            tab="ipython",
        )
        plugin.add_option(
            "ipython_session_key",
            type="text",
            value='19749810-8febfa748186a01da2f7b28c',
            label="Session Key",
            tab="ipython",
        )
        plugin.add_option(
            "ipython_conn_addr",
            type="text",
            value='127.0.0.1',
            label="Connection Address",
            tab="ipython",
        )

        volumes_keys = {
            "enabled": "bool",
            "docker": "text",
            "host": "text",
        }
        volumes_items = [
            {
                "enabled": True,
                "docker": "/mnt/data",
                "host": "{workdir}",
            },
        ]
        ports_keys = {
            "enabled": "bool",
            "docker": "text",
            "host": "int",
        }
        ports_items = []

        plugin.add_option(
            "ipython_port_shell",
            type="int",
            value=5555,
            label="Port: shell",
            tab="ipython",
            advanced=True,
        )
        plugin.add_option(
            "ipython_port_iopub",
            type="int",
            value=5556,
            label="Port: iopub",
            tab="ipython",
            advanced=True,
        )
        plugin.add_option(
            "ipython_port_stdin",
            type="int",
            value=5557,
            label="Port: stdin",
            tab="ipython",
            advanced=True,
        )
        plugin.add_option(
            "ipython_port_control",
            type="int",
            value=5558,
            label="Port: control",
            tab="ipython",
            advanced=True,
        )
        plugin.add_option(
            "ipython_port_hb",
            type="int",
            value=5559,
            label="Port: hb",
            tab="ipython",
            advanced=True,
        )
        plugin.add_option(
            "docker_run_as_root",
            type="bool",
            value=False,
            label="Run as root",
            description="Run the Python Docker sandbox as root. When disabled, the stock sandbox image runs as "
                        "the unprivileged 'pygpt' user and passwordless sudo can be used for commands that require "
                        "root privileges.",
            tab="python_legacy",
        )
        plugin.add_option(
            "python_cmd_tpl",
            type="text",
            value="python3 {filename}",
            label="Python command template",
            description="Python command template to execute, use {filename} for filename placeholder",
            tab="python_legacy",
        )
        plugin.add_option(
            "dockerfile",
            type="textarea",
            value=dockerfile_legacy,
            label="Dockerfile",
            description="Dockerfile",
            tooltip="Dockerfile",
            tab="python_legacy",
        )
        plugin.add_option(
            "image_name",
            type="text",
            value='pygpt_python_legacy',
            label="Docker image name",
            tab="python_legacy",
        )
        plugin.add_option(
            "container_name",
            type="text",
            value='pygpt_python_legacy_container',
            label="Docker container name",
            tab="python_legacy",
        )
        plugin.add_option(
            "docker_entrypoint",
            type="text",
            value='tail -f /dev/null',
            label="Docker run command",
            tab="python_legacy",
            advanced=True,
        )
        plugin.add_option(
            "docker_volumes",
            type="dict",
            value=volumes_items,
            label="Docker volumes",
            description="Docker volumes mapping",
            tooltip="Docker volumes mapping",
            keys=volumes_keys,
            tab="python_legacy",
            advanced=True,
        )
        plugin.add_option(
            "docker_ports",
            type="dict",
            value=ports_items,
            label="Docker ports",
            description="Docker ports mapping",
            tooltip="Docker ports mapping",
            keys=ports_keys,
            tab="python_legacy",
            advanced=True,
        )
        plugin.add_option(
            "attach_output",
            type="bool",
            value=True,
            label="Connect to the Python interpreter window",
            description="Attach code input/output to the Python interpreter window.",
            tab="general",
        )
        plugin.add_option(
            "output_max_entries",
            type="int",
            value=15,
            min=0,
            max=10000,
            label="Max interpreter window entries",
            description="Maximum number of input/output blocks kept in the Python interpreter window. Set to 0 for no limit.",
            tab="general",
        )
        plugin.add_option(
            "fresh_kernel",
            type="bool",
            value=False,
            label="Always run code in a fresh kernel",
            description="Always run code using Run in a fresh kernel.",
            tab="general",
        )

        # commands
        plugin.add_cmd(
            "python_exec",
            instruction="execute Python code. "
                        "Execution is non-interactive: never use input(), getpass(), or code that waits for "
                        "stdin; provide required values directly in code.",
            params=[
                {
                    "name": "code",
                    "type": "str",
                    "description": "Python code to execute",
                    "required": True,
                },
            ],
            enabled=True,
            description="Allows direct Python code execution",
            tab="python_legacy",
        )
