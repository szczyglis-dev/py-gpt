#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.28 21:00:00                  #
# ================================================== #

import os.path
import subprocess
import docker


class Runner:
    def __init__(self, plugin=None):
        """
        Cmd Runner

        :param plugin: plugin
        """
        self.plugin = plugin
        self.signals = None

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

    def handle_result_docker(self, response):
        """
        Handle result from docker container

        :param response: response
        :return: result
        """
        result = response.decode('utf-8')
        self.log("Result: {}".format(result), sandbox=True)
        return result

    def is_sandbox(self):
        """
        Check if sandbox is enabled

        :return: true if sandbox is enabled
        :rtype: bool
        """
        return self.plugin.get_option_value('sandbox_docker')

    def get_docker(self):
        """
        Get docker client

        :return: docker client
        :rtype: docker.client.DockerClient
        """
        return docker.from_env()

    def get_docker_image(self):
        """
        Get docker image

        :return: docker image
        :rtype: str
        """
        return self.plugin.get_option_value('sandbox_docker_image')

    def get_volumes(self):
        """
        Get docker volumes

        :return: docker volumes
        :rtype: dict
        """
        path = os.path.join(self.plugin.window.core.config.path, 'output')
        mapping = {}
        mapping[path] = {
            "bind": "/data",
            "mode": "rw"
        }
        return mapping

    def run_docker(self, cmd):
        """
        Run docker container with command and return response

        :param cmd: command to run
        :return: response
        """
        client = self.get_docker()
        mapping = self.get_volumes()
        return client.containers.run(self.get_docker_image(), cmd,
                                     volumes=mapping, working_dir="/data", stdout=True, stderr=True)

    def code_execute_file_sandbox(self, ctx, item, request_item):
        """
        Execute code from file in sandbox (docker)

        :param ctx: CtxItem
        :param item: command item
        :param request_item: request item
        """
        msg = "Executing Python file: {}".format(item["params"]['filename'])
        self.log(msg, sandbox=True)
        cmd = self.plugin.get_option_value('python_cmd_tpl').format(filename=item["params"]['filename'])
        self.log("Running command: {}".format(cmd), sandbox=True)
        response = self.run_docker(cmd)
        result = self.handle_result_docker(response)
        return {"request": request_item, "result": result}

    def code_execute_sandbox(self, ctx, item, request_item):
        """
        Execute code in sandbox (docker)

        :param ctx: CtxItem
        :param item: command item
        :param request_item: request item
        """
        msg = "Saving Python file: {}".format(item["params"]['filename'])
        self.log(msg, sandbox=True)
        path = os.path.join(self.plugin.window.core.config.path, 'output', item["params"]['filename'])
        data = item["params"]['code']
        with open(path, 'w', encoding="utf-8") as file:
            file.write(data)
            file.close()

        # run code
        msg = "Executing Python code: {}".format(item["params"]['code'])
        self.log(msg, sandbox=True)
        cmd = self.plugin.get_option_value('python_cmd_tpl').format(filename=item["params"]['filename'])
        self.log("Running command: {}".format(cmd), sandbox=True)
        response = self.run_docker(cmd)
        result = self.handle_result_docker(response)
        return {"request": request_item, "result": result}

    def sys_exec_sandbox(self, ctx, item, request_item):
        """
        Execute system command in sandbox (docker)

        :param ctx: CtxItem
        :param item: command item
        :param request_item: request item
        """
        msg = "Executing system command: {}".format(item["params"]['command'])
        self.log(msg, sandbox=True)
        self.log("Running command: {}".format(item["params"]['command']), sandbox=True)
        response = self.run_docker(item["params"]['command'])
        result = self.handle_result_docker(response)
        return {"request": request_item, "result": result}

    def code_execute_file_host(self, ctx, item, request_item):
        """
        Execute code from file on host machine

        :param ctx: CtxItem
        :param item: command item
        :param request_item: request item
        """
        msg = "Executing Python file: {}".format(item["params"]['filename'])
        self.log(msg)
        path = os.path.join(self.plugin.window.core.config.path, 'output', item["params"]['filename'])

        # check if file exists
        if not os.path.isfile(path):
            msg = "File not found: {}".format(item["params"]['filename'])
            ctx.results.append({"request": request_item, "result": "File not found"})
            return

        # run code
        cmd = self.plugin.get_option_value('python_cmd_tpl').format(filename=path)
        self.log("Running command: {}".format(cmd))
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        result = self.handle_result(stdout, stderr)
        return {"request": request_item, "result": result}

    def code_execute_host(self, ctx, item, request_item):
        """
        Execute code on host machine

        :param ctx: CtxItem
        :param item: command item
        :param request_item: request item
        """
        # write code to file
        msg = "Saving Python file: {}".format(item["params"]['filename'])
        self.log(msg)
        path = os.path.join(self.plugin.window.core.config.path, 'output', item["params"]['filename'])
        data = item["params"]['code']
        with open(path, 'w', encoding="utf-8") as file:
            file.write(data)
            file.close()

        # run code
        cmd = self.plugin.get_option_value('python_cmd_tpl').format(filename=path)
        self.log("Running command: {}".format(cmd))
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        result = self.handle_result(stdout, stderr)
        return {"request": request_item, "result": result}

    def sys_exec_host(self, ctx, item, request_item):
        """
        Execute system command on host

        :param ctx: CtxItem
        :param item: command item
        :param request_item: request item
        """
        msg = "Executing system command: {}".format(item["params"]['command'])
        self.log(msg)
        self.log("Running command: {}".format(item["params"]['command']))
        process = subprocess.Popen(item["params"]['command'], shell=True, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        result = self.handle_result(stdout, stderr)
        return {"request": request_item, "result": result}

    def error(self, err):
        """
        Log error message

        :param err: exception
        """
        if self.signals is not None:
            self.signals.error.emit(err)

    def status(self, msg):
        """
        Send status message

        :param msg: status message
        """
        if self.signals is not None:
            self.signals.status.emit(msg)

    def debug(self, msg):
        """
        Log debug message

        :param msg: message to log
        """
        if self.signals is not None:
            self.signals.debug.emit(msg)

    def log(self, msg, sandbox=False):
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
