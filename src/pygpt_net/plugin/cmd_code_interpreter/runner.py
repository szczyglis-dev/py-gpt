#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.17 19:00:00                  #
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

    def send_interpreter_input(self, data: str):
        """
        Send input to subprocess

        :param data: input text
        """
        type = "stdin"
        if self.signals is not None:
            self.send_interpreter_output_begin(type)
            self.signals.output.emit(data, type)
            self.send_interpreter_output_end(type)

    def send_interpreter_output(self, data: str, type: str):
        """
        Send output to interpreter

        :param data: output text
        :param type: output type (stdout/stderr)
        """
        if self.signals is not None:
            self.signals.output.emit(data, type)

    def send_interpreter_output_begin(self, type: str):
        """
        Send output begin to interpreter

        :param type: output type (stdout/stderr)
        """
        if self.signals is not None:
            self.signals.output_begin.emit(type)

    def send_interpreter_output_end(self, type: str):
        """
        Send output end to interpreter

        :param type: output type (stdout/stderr)
        """
        if self.signals is not None:
            self.signals.output_end.emit(type)

    def send_html_output(self, data: str):
        """
        Send HTML output to canvas

        :param data: HTML code
        """
        if self.signals is not None:
            self.signals.html_output.emit(data)

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
            self.send_interpreter_output(result, "stdout")
            self.log("STDOUT: {}".format(result))
        if stderr:
            result = stderr.decode("utf-8")
            self.send_interpreter_output(result, "stderr")
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
        self.send_interpreter_output(result, "stdout")
        self.log(
            "Result: {}".format(result),
            sandbox=True,
        )
        return result

    def handle_result_ipython(self, ctx: CtxItem, response) -> str:
        """
        Handle result from ipython container, check for files and images

        :param ctx: CtxItem
        :param response: response
        :return: result
        """
        paths = self.plugin.window.core.filesystem.parser.extract_data_files(ctx, response)
        if len(paths) == 0:
            self.plugin.window.core.filesystem.parser.extract_data_files(ctx, ctx.input)
        return response

    def is_sandbox(self) -> bool:
        """
        Check if sandbox is enabled

        :return: True if sandbox is enabled
        """
        return self.plugin.get_option_value('sandbox_docker')

    def is_sandbox_ipython(self) -> bool:
        """
        Check if sandbox is enabled for IPython

        :return: True if sandbox is enabled
        """
        return self.plugin.get_option_value('sandbox_ipython')

    def get_docker(self) -> docker.client.DockerClient:
        """
        Get docker client

        :return: docker client instance
        """
        return docker.from_env()

    def get_docker_image(self) -> str:
        """
        Get docker image name

        :return: docker image
        """
        return self.plugin.get_option_value('sandbox_docker_image')

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
        try:
            response = self.plugin.docker.execute(cmd)
        except Exception as e:
            # self.error(e)
            response = str(e).encode("utf-8")
        return response


    def code_execute_file_host(self, ctx, item: dict, request: dict) -> dict or None:
        """
        Execute code from file on host machine

        :param ctx: CtxItem
        :param item: command item
        :param request: request item
        :return: response dict
        """
        msg = "Executing Python file: {}".format(item["params"]['path'])
        self.log(msg)
        path = self.prepare_path(item["params"]['path'], on_host=True)

        # check if file exists
        if not os.path.isfile(path):
            return {
                "request": request,
                "result": "File not found",
            }

        """
        # send input to interpreter
        with open(path, 'r', encoding="utf-8") as file:
            code = file.read()
            self.append_input(code)
            self.send_interpreter_input(code)  # send input to interpreter
        """

        # run code
        cmd = self.plugin.get_option_value('python_cmd_tpl').format(filename=path)
        self.log("Running command: {}".format(cmd))
        try:
            self.send_interpreter_output_begin("stdout")
            process = subprocess.Popen(
                cmd,
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
        self.send_interpreter_output_end("stdout")
        return {
            "request": request,
            "result": str(result),
            "context": "PYTHON OUTPUT:\n--------------------------------\n" + self.parse_result(result),
        }

    def code_execute_file_sandbox(self, ctx: CtxItem, item: dict, request: dict) -> dict:
        """
        Execute code from file in sandbox (docker)

        :param ctx: CtxItem
        :param item: command item
        :param request: request item
        :return: response dict
        """
        path = item["params"]['path']
        msg = "Executing Python file: {}".format(path)
        self.log(msg, sandbox=True)
        cmd = self.plugin.get_option_value('python_cmd_tpl').format(
            filename=path,
        )

        """
        # send input to interpreter
        with open(self.prepare_path(path, on_host=True), 'r', encoding="utf-8") as file:
            code = file.read()
            self.append_input(code)
            self.send_interpreter_input(code)  # send input to interpreter
        """

        self.log("Running command: {}".format(cmd), sandbox=True)
        self.send_interpreter_output_begin("stdout")
        response = self.run_docker(cmd)
        result = self.handle_result_docker(response)
        self.send_interpreter_output_end("stdout")
        return {
            "request": request,
            "result": str(result),
            "context": "PYTHON OUTPUT:\n--------------------------------\n" + self.parse_result(result),
        }

    def code_execute_host(self, ctx: CtxItem, item: dict, request: dict, all: bool = False) -> dict:
        """
        Execute code on host machine

        :param ctx: CtxItem
        :param item: command item
        :param request: request item
        :param all: execute all
        :return: response dict
        """
        # write code to file
        data = item["params"]['code']
        if not all:
            path = self.plugin.window.tools.get("interpreter").file_current
            if "path" in item["params"]:
                path = item["params"]['path']
            path = self.prepare_path(path, on_host=True)
            msg = "Saving Python file: {}".format(path)
            self.log(msg)
            with open(path, 'w', encoding="utf-8") as file:
                file.write(data)
        else:
            path = self.prepare_path(self.plugin.window.tools.get("interpreter").file_input, on_host=True)

        self.append_input(data)
        self.send_interpreter_input(data)  # send input to interpreter

        # run code
        cmd = self.plugin.get_option_value('python_cmd_tpl').format(filename=path)
        self.log("Running command: {}".format(cmd))
        try:
            self.send_interpreter_output_begin("stdout")
            process = subprocess.Popen(
                cmd,
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
        self.send_interpreter_output_end("stdout")
        return {
            "request": request,
            "result": str(result),
            "context": "PYTHON OUTPUT:\n--------------------------------\n" + self.parse_result(result),
        }

    def code_execute_sandbox(self, ctx, item: dict, request: dict, all: bool = False) -> dict:
        """
        Execute code in sandbox (docker)

        :param ctx: CtxItem
        :param item: command item
        :param request: request item
        :param all: execute all
        :return: response dict
        """
        data = item["params"]['code']
        if not all:
            path = self.plugin.window.tools.get("interpreter").file_current
            if "path" in item["params"]:
                path = item["params"]['path']
            msg = "Saving Python file: {}".format(path)
            self.log(msg, sandbox=True)
            with open(self.prepare_path(path, on_host=True), 'w', encoding="utf-8") as file:
                file.write(data)
        else:
            path = self.plugin.window.tools.get("interpreter").file_input

        self.append_input(data)
        self.send_interpreter_input(data)  # send input to interpreter

        # run code
        path = self.prepare_path(path, on_host=False)
        msg = "Executing Python code: {}".format(item["params"]['code'])
        self.log(msg, sandbox=True)
        cmd = self.plugin.get_option_value('python_cmd_tpl').format(
            filename=path,
        )
        self.log("Running command: {}".format(cmd), sandbox=True)
        self.send_interpreter_output_begin("stdout")
        response = self.run_docker(cmd)
        result = self.handle_result_docker(response)
        self.send_interpreter_output_end("stdout")
        return {
            "request": request,
            "result": str(result),
            "context": "PYTHON OUTPUT:\n--------------------------------\n" + self.parse_result(result),
        }

    def ipython_execute_new(self, ctx, item: dict, request: dict, all: bool = False) -> dict:
        """
        Execute code in IPython interpreter (new kernel)

        :param ctx: CtxItem
        :param item: command item
        :param request: request item
        :param all: execute all
        :return: response dict
        """
        sandbox = self.is_sandbox_ipython()
        data = item["params"]['code']
        if not all:
            path = self.plugin.window.tools.get("interpreter").file_current
            if "path" in item["params"]:
                path = item["params"]['path']
            msg = "Saving Python file: {}".format(path)
            self.log(msg, sandbox=sandbox)
            with open(self.prepare_path(path, on_host=True), 'w', encoding="utf-8") as file:
                file.write(data)
        else:
            path = self.plugin.window.tools.get("interpreter").file_input

        with open(self.prepare_path(path, on_host=True), 'r', encoding="utf-8") as file:
            data = file.read()

        self.append_input(data)
        self.send_interpreter_input(data)  # send input to interpreter tool

        # run code in IPython interpreter
        msg = "Executing Python code: {}".format(item["params"]['code'])
        self.log(msg, sandbox=sandbox)
        self.log("Connecting to IPython interpreter...", sandbox=sandbox)
        try:
            self.log("Please wait...", sandbox=sandbox)
            self.send_interpreter_output_begin("stdout")
            result = self.plugin.get_interpreter().execute(data, current=False)
            result = self.handle_result_ipython(ctx, result)
            self.log("Python Code Executed.", sandbox=sandbox)
        except Exception as e:
            self.error(e)
            result = str(e)
        self.send_interpreter_output_end("stdout")
        return {
            "request": request,
            "result": str(result),
            "context": "IPYTHON OUTPUT:\n--------------------------------\n" + self.parse_result(result),
        }

    def ipython_execute(self, ctx, item: dict, request: dict, all: bool = False) -> dict:
        """
        Execute code in IPython interpreter (current kernel)

        :param ctx: CtxItem
        :param item: command item
        :param request: request item
        :param all: execute all
        :return: response dict
        """
        sandbox = self.is_sandbox_ipython()
        data = item["params"]['code']

        # auto-init after error (enable only for manual call)
        auto_init = False
        if "auto_init" in item["params"]:
            auto_init = item["params"]['auto_init']

        # check if command is to restart the kernel
        if data.strip().startswith("/restart"):
            return self.ipython_kernel_restart(ctx, item, request, all)

        if not all:
            path = self.plugin.window.tools.get("interpreter").file_current
            if "path" in item["params"]:
                path = item["params"]['path']
            msg = "Saving Python file: {}".format(path)
            self.log(msg, sandbox=sandbox)
            with open(self.prepare_path(path, on_host=True), 'w', encoding="utf-8") as file:
                file.write(data)
        else:
            path = self.plugin.window.tools.get("interpreter").file_input

        with open(self.prepare_path(path, on_host=True), 'r', encoding="utf-8") as file:
            data = file.read()

        self.append_input(data)
        self.send_interpreter_input(data)  # send input to interpreter tool

        # run code in IPython interpreter
        msg = "Executing Python code: {}".format(item["params"]['code'])
        self.log(msg, sandbox=sandbox)
        self.log("Connecting to IPython interpreter...", sandbox=sandbox)
        try:
            self.log("Please wait...", sandbox=sandbox)
            self.send_interpreter_output_begin("stdout")
            result = self.plugin.get_interpreter().execute(
                data,
                current=True,
                auto_init=auto_init,  # auto initialize after error
            )
            result = self.handle_result_ipython(ctx, result)
            self.log("Python Code Executed.", sandbox=sandbox)
        except Exception as e:
            self.error(e)
            result = str(e)
        self.send_interpreter_output_end("stdout")
        return {
            "request": request,
            "result": str(result),
            "context": "IPYTHON OUTPUT:\n--------------------------------\n" + self.parse_result(result),
        }

    def ipython_kernel_restart(self, ctx, item: dict, request: dict, all: bool = False) -> dict:
        """
        Execute code in IPython interpreter (current kernel)

        :param ctx: CtxItem
        :param item: command item
        :param request: request item
        :param all: execute all
        :return: response dict
        """
        sandbox = self.is_sandbox_ipython()
        self.append_input("")
        self.send_interpreter_input("")  # send input to interpreter tool

        # restart IPython interpreter
        self.log("Connecting to IPython interpreter...", sandbox=sandbox)
        try:
            self.log("Restarting IPython kernel...", sandbox=sandbox)
            response = self.plugin.get_interpreter().restart_kernel()
        except Exception as e:
            self.error(e)
            response = False
        if response:
            result = "Kernel restarted"
        else:
            result = "Kernel not restarted"
        self.log(result, sandbox=sandbox)
        return {
            "request": request,
            "result": str(result),
            "context": "IPYTHON OUTPUT:\n--------------------------------\n" + self.parse_result(result),
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

    def append_input(self, data: str):
        """
        Append input to interpreter input file

        :param data: input data
        """
        if not self.plugin.get_option_value("attach_output"):
            return

        content = ""
        path = self.prepare_path(self.plugin.window.tools.get("interpreter").file_input, on_host=True)
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        with open(path, "a", encoding="utf-8") as f:
            nl = ""
            if content != "":
                nl = "\n"
            if data != "":
                f.write(nl + data)
            else:
                f.write("")

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
