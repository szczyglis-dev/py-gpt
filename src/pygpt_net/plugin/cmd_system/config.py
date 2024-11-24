#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.24 06:00:00                  #
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
        dockerfile = 'FROM python:3.9-alpine'
        dockerfile += '\n\n'
        dockerfile += 'RUN mkdir /data'
        dockerfile += '\n\n'
        dockerfile += '# Data directory, bound as a volume to the local \'data/\' directory'
        dockerfile += '\nWORKDIR /data'

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

        plugin.add_option(
            "sandbox_docker",
            type="bool",
            value=False,
            label="Sandbox (docker container)",
            description="Executes commands in sandbox (docker container). "
                        "Docker must be installed and running.",
            tab="sandbox",
        )
        plugin.add_option(
            "dockerfile",
            type="textarea",
            value=dockerfile,
            label="Dockerfile",
            description="Dockerfile",
            tooltip="Dockerfile",
            tab="sandbox",
        )
        plugin.add_option(
            "image_name",
            type="text",
            value='pygpt_system',
            label="Docker image name",
            tab="sandbox",
        )
        plugin.add_option(
            "container_name",
            type="text",
            value='pygpt_system_container',
            label="Docker container name",
            tab="sandbox",
        )
        plugin.add_option(
            "docker_entrypoint",
            type="text",
            value='tail -f /dev/null',
            label="Docker run command",
            tab="sandbox",
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
            tab="sandbox",
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
            tab="sandbox",
            advanced=True,
        )
        plugin.add_option(
            "auto_cwd",
            type="bool",
            value=True,
            label="Auto-append CWD to sys_exec",
            description="Automatically append current working directory to sys_exec command",
            tab="general",
        )
        plugin.add_cmd(
            "sys_exec",
            instruction="execute ANY system command, script or app in user's environment. "
                        "Do not use this command to install Python libraries, use IPython environment and IPython commands instead.",
            params=[
                {
                    "name": "command",
                    "type": "str",
                    "description": "system command",
                    "required": True,
                },
            ],
            enabled=True,
            description="Allows system commands execution",
            tab="general",
        )