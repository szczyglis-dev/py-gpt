#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.21 22:00:00                  #
# ================================================== #

import os.path
import re
import subprocess
import docker

from pygpt_net.item.ctx import CtxItem


class Runner:
    def __init__(self, plugin=None):
        """
        Cmd Runner

        :param plugin: plugin
        """
        self.plugin = plugin
        self.signals = None

    def attach_signals(self, signals):
        """
        Attach signals

        :param signals: signals
        """
        self.signals = signals

    def handle_result(self, stdout, stderr):
        """
        Handle result from subprocess

        :param stdout: stdout
        :param stderr: stderr
        :return: result
        """
        result = None
        if stdout:
            result = stdout.decode("utf-8")
            self.log("STDOUT: {}".format(result))
        if stderr:
            result = stderr.decode("utf-8")
            self.log("STDERR: {}".format(result))
        if result is None:
            result = "No result (STDOUT/STDERR empty)"
            self.log(result)
        return result

    def handle_result_docker(self, response) -> str:
        """
        Handle result from docker container

        :param response: response
        :return: result
        """
        result = None
        if response:
            result = response.decode('utf-8')
        self.log(
            "Result: {}".format(result),
            sandbox=True,
        )
        return result

    def is_sandbox(self) -> bool:
        """
        Check if sandbox is enabled

        :return: True if sandbox is enabled
        """
        return self.plugin.get_option_value('sandbox_docker')

    def get_docker(self) -> docker.client.DockerClient:
        """
        Get docker client

        :return: docker client instance
        """
        return docker.from_env()

    def get_volumes(self) -> dict:
        """
        Get docker volumes

        :return: docker volumes
        """
        path = self.plugin.window.core.config.get_user_dir('data')
        mapping = {}
        mapping[path] = {
            "bind": "/data",
            "mode": "rw",
        }
        return mapping

    def run_docker(self, cmd: str) -> bytes or None:
        """
        Run docker container with command and return response

        :param cmd: command to run
        :return: response
        """
        client = self.get_docker()
        mapping = self.get_volumes()
        try:
            response = self.plugin.docker.execute(cmd)
        except Exception as e:
            # self.error(e)
            response = str(e).encode("utf-8")
        return response

    def sys_exec_host(self, ctx: CtxItem, item: dict, request: dict) -> dict:
        """
        Execute system command on host

        :param ctx: CtxItem
        :param item: command item
        :param request: request item
        :return: response dict
        """
        msg = "Executing system command: {}".format(item["params"]['command'])
        self.log(msg)
        self.log("Running command: {}".format(item["params"]['command']))
        try:
            process = subprocess.Popen(
                item["params"]['command'],
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = process.communicate()
        except Exception as e:
            self.error(e)
            stdout = None
            stderr = str(e).encode("utf-8")
        result = self.handle_result(stdout, stderr)
        return {
            "request": request,
            "result": str(result),
            "context": "SYS OUTPUT:\n--------------------------------\n" + self.parse_result(result),
        }

    def sys_exec_sandbox(self, ctx: CtxItem, item: dict, request: dict) -> dict:
        """
        Execute system command in sandbox (docker)

        :param ctx: CtxItem
        :param item: command item
        :param request: request item
        :return: response dict
        """
        msg = "Executing system command: {}".format(item["params"]['command'])
        self.log(msg, sandbox=True)
        self.log(
            "Running command: {}".format(item["params"]['command']),
            sandbox=True,
        )
        response = self.run_docker(item["params"]['command'])
        result = self.handle_result_docker(response)
        return {
            "request": request,
            "result": str(result),
            "context": "SYS OUTPUT:\n--------------------------------\n" + self.parse_result(result),
        }

    def parse_result(self, result):
        """
        Parse result

        :param result: result
        :return: parsed result
        """
        if result is None:
            return ""
        img_ext = ["png", "jpg", "jpeg", "gif", "bmp", "tiff"]
        if result.strip().split(".")[-1].lower() in img_ext:
            path = self.prepare_path(result.strip().replace("file://", ""), on_host=True)
            if os.path.isfile(path):
                return "![Image](file://{})".format(path)
        return str(result)

    def is_absolute_path(self, path: str) -> bool:
        """
        Check if path is absolute

        :param path: path to check
        :return: True if absolute
        """
        return os.path.isabs(path)

    def prepare_path(self, path: str, on_host: bool = True) -> str:
        """
        Prepare path

        :param path: path to prepare
        :param on_host: is on host
        :return: prepared path
        """
        if self.is_absolute_path(path):
            return path
        else:
            if not self.is_sandbox() or on_host:
                return os.path.join(
                    self.plugin.window.core.config.get_user_dir('data'),
                    path,
                )
            else:
                return path

    def error(self, err: any):
        """
        Log error message

        :param err: exception or error message
        """
        if self.signals is not None:
            self.signals.error.emit(err)

    def status(self, msg: str):
        """
        Send status message

        :param msg: status message
        """
        if self.signals is not None:
            self.signals.status.emit(msg)

    def debug(self, msg: any):
        """
        Log debug message

        :param msg: message to log
        """
        if self.signals is not None:
            self.signals.debug.emit(msg)

    def log(self, msg, sandbox: bool = False):
        """
        Log message to console

        :param msg: message to log
        :param sandbox: is sandbox mode
        """
        prefix = ''
        if sandbox:
            prefix += '[DOCKER]'
        full_msg = prefix + ' ' + str(msg)

        if self.signals is not None:
            self.signals.log.emit(full_msg)
