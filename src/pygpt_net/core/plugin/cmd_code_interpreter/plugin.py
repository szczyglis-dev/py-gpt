#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.23 22:00:00                  #
# ================================================== #

import os.path
import subprocess
import docker

from pygpt_net.core.plugin.base_plugin import BasePlugin


class Plugin(BasePlugin):
    def __init__(self):
        super(Plugin, self).__init__()
        self.id = "cmd_code_interpreter"
        self.name = "Command: Code Interpreter"
        self.description = "Provides Python code execution"
        self.window = None
        self.order = 100
        self.allowed_cmds = [
            "code_execute",
            "code_execute_file",
            "sys_exec"
        ]
        self.use_locale = True
        self.init_options()

    def init_options(self):
        """
        Initialize options
        """
        # cmd enable/disable
        self.add_option("python_cmd_tpl", "text", 'python3 {filename}',
                        "Python command template",
                        "Python command template to execute, use {filename} for filename placeholder")
        self.add_option("cmd_code_execute", "bool", True,
                        "Enable: Python Code Generate and Execute",
                        "Allows Python code execution (generate and execute from file)")
        self.add_option("cmd_code_execute_file", "bool", True,
                        "Enable: Python Code Execute (File)",
                        "Allows Python code execution from existing file")
        self.add_option("cmd_sys_exec", "bool", True,
                        "Enable: System Command Execute",
                        "Allows system commands execution")
        self.add_option("sandbox_docker", "bool", False,
                        "Sandbox (docker container)",
                        "Executes commands in sandbox (docker container). Docker must be installed and running.")
        self.add_option("sandbox_docker_image", "text", 'python:3.8-alpine',
                        "Docker image",
                        "Docker image to use for sandbox")

        # cmd syntax (prompt/instruction)
        self.add_option("syntax_code_execute", "textarea", '"code_execute": create and execute Python code, params: '
                                                           '"filename", "code"',
                        "Syntax: code_execute",
                        "Syntax for Python code execution (generate and execute from file)", advanced=True)
        self.add_option("syntax_code_execute_file", "textarea", '"code_execute_file": execute Python code from '
                                                                'existing file, params: "filename"',
                        "Syntax: code_execute_file",
                        "Syntax for Python code execution from existing file", advanced=True)
        self.add_option("syntax_sys_exec", "textarea", '"sys_exec": execute ANY system command, script or application '
                                                       'in user\'s environment, params: "command"',
                        "Syntax: sys_exec",
                        "Syntax for system commands execution", advanced=True)

    def setup(self):
        """
        Return available config options

        :return: config options
        :rtype: dict
        """
        return self.options

    def attach(self, window):
        """
        Attach window

        :param window: Window instance
        """
        self.window = window

    def handle(self, event, *args, **kwargs):
        """
        Handle dispatched event

        :param event: event object
        """
        name = event.name
        data = event.data
        ctx = event.ctx

        if name == 'cmd.syntax':
            self.cmd_syntax(data)
        elif name == 'cmd.execute':
            self.cmd(ctx, data['commands'])

    def is_cmd_allowed(self, cmd):
        """
        Check if cmd is allowed

        :param cmd: command name
        :return: true if allowed
        :rtype: bool
        """
        key = "cmd_" + cmd
        if self.has_option(key) and self.get_option_value(key) is True:
            return True
        return False

    def log(self, msg, sandbox=False):
        """
        Log message to console

        :param msg: message to log
        """
        prefix = '[CMD]'
        if sandbox:
            prefix += '[DOCKER]'
        self.debug(prefix + ' ' + str(msg))
        print(prefix + ' ' + str(msg))

    def cmd_syntax(self, data):
        """
        Event: On cmd syntax prepare

        :param data: event data dict
        """
        for item in self.allowed_cmds:
            if self.is_cmd_allowed(item):
                key = "syntax_" + item
                if self.has_option(key):
                    data['syntax'].append(str(self.get_option_value(key)))

    def run_cmd_host(self, ctx, item, request_item):
        """
        Run command on host machine

        :param ctx: CtxItem
        :param item: command item
        :param request_item: request item
        :return: result
        """
        path = os.path.join(self.window.app.config.path, 'output', item["params"]['filename'])
        # check if file exists
        if not os.path.isfile(path):
            msg = "File not found: {}".format(item["params"]['filename'])
            ctx.results.append({"request": request_item, "result": "File not found"})
            return

        # run code
        cmd = self.get_option_value('python_cmd_tpl').format(filename=path)
        self.log("Running command: {}".format(cmd))
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        result = self.handle_result(stdout, stderr)
        ctx.results.append({"request": request_item, "result": result})
        return result

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
        return self.get_option_value('sandbox_docker')

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
        return self.get_option_value('sandbox_docker_image')

    def get_volumes(self):
        """
        Get docker volumes

        :return: docker volumes
        :rtype: dict
        """
        path = os.path.join(self.window.app.config.path, 'output')
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
        cmd = self.get_option_value('python_cmd_tpl').format(filename=item["params"]['filename'])
        self.log("Running command: {}".format(cmd), sandbox=True)
        response = self.run_docker(cmd)
        result = self.handle_result_docker(response)
        ctx.results.append({"request": request_item, "result": result})

    def code_execute_sandbox(self, ctx, item, request_item):
        """
        Execute code in sandbox (docker)

        :param ctx: CtxItem
        :param item: command item
        :param request_item: request item
        """
        msg = "Saving Python file: {}".format(item["params"]['filename'])
        self.log(msg, sandbox=True)
        path = os.path.join(self.window.app.config.path, 'output', item["params"]['filename'])
        data = item["params"]['code']
        with open(path, 'w', encoding="utf-8") as file:
            file.write(data)
            file.close()
        # run code
        msg = "Executing Python code: {}".format(item["params"]['code'])
        self.log(msg, sandbox=True)
        cmd = self.get_option_value('python_cmd_tpl').format(filename=item["params"]['filename'])
        self.log("Running command: {}".format(cmd), sandbox=True)
        response = self.run_docker(cmd)
        result = self.handle_result_docker(response)
        ctx.results.append({"request": request_item, "result": result})

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
        ctx.results.append({"request": request_item, "result": result})

    def code_execute_file_host(self, ctx, item, request_item):
        """
        Execute code from file on host machine

        :param ctx: CtxItem
        :param item: command item
        :param request_item: request item
        """
        msg = "Executing Python file: {}".format(item["params"]['filename'])
        self.log(msg)
        path = os.path.join(self.window.app.config.path, 'output', item["params"]['filename'])

        # check if file exists
        if not os.path.isfile(path):
            msg = "File not found: {}".format(item["params"]['filename'])
            ctx.results.append({"request": request_item, "result": "File not found"})
            return

        # run code
        cmd = self.get_option_value('python_cmd_tpl').format(filename=path)
        self.log("Running command: {}".format(cmd))
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        result = self.handle_result(stdout, stderr)
        ctx.results.append({"request": request_item, "result": result})

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
        path = os.path.join(self.window.app.config.path, 'output', item["params"]['filename'])
        data = item["params"]['code']
        with open(path, 'w', encoding="utf-8") as file:
            file.write(data)
            file.close()
        # run code
        cmd = self.get_option_value('python_cmd_tpl').format(filename=path)
        self.log("Running command: {}".format(cmd))
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        result = self.handle_result(stdout, stderr)
        ctx.results.append({"request": request_item, "result": result})

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
        ctx.results.append({"request": request_item, "result": result})

    def cmd(self, ctx, cmds):
        """
        Execute command

        :param ctx: CtxItem
        :param cmds: commands dict
        """
        msg = None
        for item in cmds:
            try:
                if item["cmd"] in self.allowed_cmds:
                    # prepare request item for result
                    request_item = {"cmd": item["cmd"]}
                    ctx.reply = True  # send result message

                    # code_execute (from existing file)
                    if item["cmd"] == "code_execute_file" and self.is_cmd_allowed("code_execute_file"):
                        try:
                            if not self.is_sandbox():
                                self.code_execute_file_host(ctx, item, request_item)
                            else:
                                self.code_execute_file_sandbox(ctx, item, request_item)
                        except Exception as e:
                            ctx.results.append({"request": request_item, "result": "Error: {}".format(e)})
                            self.log("Error: {}".format(e))
                            self.window.app.debug.log(e)

                    # code_execute (generate and execute)
                    elif item["cmd"] == "code_execute" and self.is_cmd_allowed("code_execute"):
                        try:
                            if not self.is_sandbox():
                                self.code_execute_host(ctx, item, request_item)
                            else:
                                self.code_execute_sandbox(ctx, item, request_item)
                        except Exception as e:
                            ctx.results.append({"request": request_item, "result": "Error: {}".format(e)})
                            self.log("Error: {}".format(e))
                            self.window.app.debug.log(e)

                    # sys_exec
                    elif item["cmd"] == "sys_exec" and self.is_cmd_allowed("sys_exec"):
                        try:
                            if not self.is_sandbox():
                                self.sys_exec_host(ctx, item, request_item)
                            else:
                                self.sys_exec_sandbox(ctx, item, request_item)
                        except Exception as e:
                            ctx.results.append({"request": request_item, "result": "Error: {}".format(e)})
                            self.log("Error: {}".format(e))
                            self.window.app.debug.log(e)
            except Exception as e:
                ctx.results.append({"request": item, "result": "Error: {}".format(e)})
                ctx.reply = True  # send result message
                self.log("Error: {}".format(e))

        if msg is not None:
            self.window.set_status(msg)
