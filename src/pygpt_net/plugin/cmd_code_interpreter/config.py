#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.25 02:00:00                  #
# ================================================== #

from pygpt_net.plugin.base.config import BaseConfig, BasePlugin


class Config(BaseConfig):
    def __init__(self, plugin: BasePlugin = None, *args, **kwargs):
        super(Config, self).__init__(plugin)
        self.plugin = plugin

    def from_defaults(self, plugin: BasePlugin = None):
        """
        Set default options for plugin

        :param plugin: plugin instance
        """
        dockerfile = '''
        # Tip: After making changes to this Dockerfile, you must rebuild the image to apply the changes(Menu -> Tools -> Rebuild IPython Docker Image)

        FROM python:3.9

        # You can customize the packages installed by default here:
        # ========================================================
        RUN pip install jupyter ipykernel
        # ========================================================

        RUN mkdir /data

        # Expose the necessary ports for Jupyter kernel communication
        EXPOSE 5555 5556 5557 5558 5559

        # Data directory, bound as a volume to the local 'data' directory
        WORKDIR /data

        # Start the IPython kernel with specified ports and settings
        CMD ["ipython", "kernel", \
        "--ip=0.0.0.0", \
        "--transport=tcp", \
        "--shell=5555", \
        "--iopub=5556", \
        "--stdin=5557", \
        "--control=5558", \
        "--hb=5559", \
        "--Session.key=19749810-8febfa748186a01da2f7b28c", \
        "--Session.signature_scheme=hmac-sha256"]
        '''

        dockerfile_legacy = 'FROM python:3.9-alpine'
        dockerfile_legacy += '\n\n'
        dockerfile_legacy += 'RUN mkdir /data'
        dockerfile_legacy += '\n\n'
        dockerfile_legacy += '# Data directory, bound as a volume to the local \'data/\' directory'
        dockerfile_legacy += '\nWORKDIR /data'

        plugin.add_option(
            "sandbox_ipython",
            type="bool",
            value=False,
            label="Sandbox (docker container)",
            description="Executes commands in sandbox (docker container). "
                        "Docker must be installed and running.",
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
            "ipython_execute",
            instruction="execute Python code in IPython interpreter (in current kernel) and get output. "
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
        """
        plugin.add_cmd(
            "ipython_execute_new",
            instruction="execute Python code in the IPython interpreter in a new kernel and get the output. Use this option only if a kernel restart is required; otherwise, use `ipython_execute` to run the code in the current session",
            params=[
                {
                    "name": "code",
                    "type": "str",
                    "description": "code to execute in IPython interpreter, usage of !magic commands is allowed",
                    "required": True,
                },
            ],
            enabled=True,
            description="Allows Python code execution in IPython interpreter (in new kernel)",
            tab="ipython",
        )
        """

        volumes_keys = {
            "enabled": "bool",
            "docker": "text",
            "host": "text",
        }
        volumes_items = [
            {
                "enabled": True,
                "docker": "/data",
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
            instruction="restart IPython kernel",
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
            "sandbox_docker",
            type="bool",
            value=False,
            label="Sandbox (docker container)",
            description="Executes commands in sandbox (docker container). "
                        "Docker must be installed and running.",
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
            label="Connect to the Python code interpreter window",
            description="Attach code input/output to the Python code interpreter window.",
            tab="general",
        )

        # commands
        plugin.add_cmd(
            "code_execute",
            instruction="save generated Python code and execute it",
            params=[
                {
                    "name": "path",
                    "type": "str",
                    "description": "path to save",
                    "default": ".interpreter.current.py",
                    "required": True,
                },
                {
                    "name": "code",
                    "type": "str",
                    "description": "code",
                    "required": True,
                },
            ],
            enabled=False,
            description="Allows Python code execution (generate and execute from file)",
            tab="python_legacy",
        )
        plugin.add_cmd(
            "code_execute_file",
            instruction="execute Python code from existing file",
            params=[
                {
                    "name": "path",
                    "type": "str",
                    "description": "file path",
                    "required": True,
                },
            ],
            enabled=False,
            description="Allows Python code execution from existing file",
            tab="python_legacy",
        )
        plugin.add_cmd(
            "code_execute_all",
            instruction="run all Python code from my interpreter",
            params=[
                {
                    "name": "code",
                    "type": "str",
                    "description": "code to append and execute",
                    "required": True,
                },
            ],
            enabled=False,
            description="Allows Python code execution (generate and execute from file)",
            tab="python_legacy",
        )
        plugin.add_cmd(
            "get_python_output",
            instruction="get output from my Python interpreter",
            params=[],
            enabled=True,
            description="Allows to get output from last executed code",
            tab="general",
        )
        plugin.add_cmd(
            "get_python_input",
            instruction="get all input code from my Python interpreter",
            params=[],
            enabled=True,
            description="Allows to get input from Python interpreter",
            tab="general",
        )
        plugin.add_cmd(
            "clear_python_output",
            instruction="clear output from my Python interpreter",
            params=[],
            enabled=True,
            description="Allows to clear output from last executed code",
            tab="general",
        )
        plugin.add_cmd(
            "render_html_output",
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
            "get_html_output",
            instruction="get current output from HTML Canvas",
            params=[],
            enabled=True,
            description="Allows to get current output from HTML Canvas",
            tab="html_canvas",
        )