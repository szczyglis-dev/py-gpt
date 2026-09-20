#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.20 10:35:00                  #
# ================================================== #

from pygpt_net.plugin.base.config import BaseConfig, BasePlugin


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
            value=SandboxMode.DISABLED.value,
            label="Sandbox",
            description="Disabled runs Python/IPython directly on the host (unsafe). Built-in sandbox runs a uv-managed built-in CPython/IPython environment with OS-level isolation where available (moderate security). Docker requires Docker to be installed and running and provides the strongest isolation; it is the safest option.",
            keys=SandboxMode.options(),
            tab="general",
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
        plugin.add_cmd(
            "ipython_exec",
            instruction="execute Python code in IPython interpreter (in current kernel) and get output. "
                        "Execution is non-interactive: never use input(), getpass(), or code that waits for stdin; "
                        "provide required values directly in code. Shell commands invoked with ! are also "
                        "non-interactive. Kernel failure is recovered automatically once; do not call "
                        "ipython_kernel_restart repeatedly. "
                        "Tip: when generating plots or other image data always print path to generated image at "
                        "the end and provide local path (prefixed with file://, not sandbox:) to the user.",
            params=[
                {
                    "name": "code",
                    "type": "str",
                    "description": "code to execute in IPython interpreter, usage of !magic commands is allowed",
                    "required": True,
                },
            ],
            enabled=True,
            description="Allows Python code execution in IPython interpreter (in current kernel)",
            tab="ipython",
        )
        plugin.add_cmd(
            "ipython_sys_exec",
            instruction="execute a system/shell command in the IPython interpreter environment. "
                        "When a sandbox is selected, execute the command inside the selected sandbox runtime; "
                        "when sandboxing is disabled, execute it on the host. Use this for operating-system "
                        "commands and command-line tools; use ipython_exec "
                        "for Python code. Execution is non-interactive: do not run commands that prompt or wait "
                        "for stdin; pass all required answers/options in the command itself.",
            params=[
                {
                    "name": "command",
                    "type": "str",
                    "description": "system/shell command to execute",
                    "required": True,
                },
            ],
            enabled=True,
            description="Allows system commands execution in the IPython environment",
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

        plugin.add_cmd(
            "ipython_kernel_restart",
            instruction="manually restart IPython kernel only after a real kernel failure when automatic recovery "
                        "did not recover it. Never call this command repeatedly or in a retry loop",
            params=[],
            enabled=True,
            description="Allows to restart IPython kernel",
            tab="ipython",
        )
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
            value=10,
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
        plugin.add_cmd(
            "python_exec_file",
            instruction="execute Python code from existing file. Execution is non-interactive; files that wait for "
                        "stdin will receive EOF instead of blocking the tool call.",
            params=[
                {
                    "name": "path",
                    "type": "str",
                    "description": "file path",
                    "required": True,
                },
            ],
            enabled=True,
            description="Allows Python code execution from existing file",
            tab="python_legacy",
        )
        plugin.add_cmd(
            "python_sys_exec",
            instruction="execute a system/shell command in the standard Python interpreter environment. "
                        "When a sandbox is selected, execute the command inside the selected sandbox runtime; "
                        "when sandboxing is disabled, execute it on the host. Use this for operating-system "
                        "commands and command-line tools; use python_exec/python_exec_file "
                        "for Python code. Execution is non-interactive: do not run commands that prompt or wait "
                        "for stdin; pass all required answers/options in the command itself.",
            params=[
                {
                    "name": "command",
                    "type": "str",
                    "description": "system/shell command to execute",
                    "required": True,
                },
            ],
            enabled=True,
            description="Allows system commands execution in the standard Python environment",
            tab="python_legacy",
        )
        plugin.add_cmd(
            "html_render_output",
            instruction="send HTML/JS code to HTML built-in browser (HTML Canvas) and render it",
            params=[
                {
                    "name": "html",
                    "type": "str",
                    "description": "HTML/JS code",
                    "required": True,
                },
            ],
            enabled=True,
            description="Allows to render HTML/JS code in HTML Canvas",
            tab="html_canvas",
        )
        plugin.add_cmd(
            "html_get_output",
            instruction="get current output from HTML Canvas",
            params=[],
            enabled=True,
            description="Allows to get current output from HTML Canvas",
            tab="html_canvas",
        )