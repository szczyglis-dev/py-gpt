#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.13 19:00:00                  #
# ================================================== #
import os.path
import subprocess
from datetime import datetime

from ..base_plugin import BasePlugin


class Plugin(BasePlugin):
    def __init__(self):
        super(Plugin, self).__init__()
        self.id = "cmd_code_interpreter"
        self.name = "Command: Code Interpreter"
        self.description = "Provides Python code execution"
        self.window = None
        self.order = 100
        self.allowed_cmds = ["code_execute", "code_execute_file", "sys_exec"]
        self.init_options()

    def init_options(self):
        """
        Initializes options
        """
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

    def setup(self):
        """
        Returns available config options

        :return: config options
        """
        return self.options

    def attach(self, window):
        """
        Attaches window

        :param window: Window
        """
        self.window = window

    def on_user_send(self, text):
        """
        Event: On user send text

        :param text: Text
        :return: Text
        """
        return text

    def on_ctx_begin(self, ctx):
        """
        Event: On new context begin

        :param ctx: Context
        :return: Context
        """
        return ctx

    def on_ctx_end(self, ctx):
        """
        Event: On context end

        :param ctx: Context
        :return: Context
        """
        return ctx

    def on_system_prompt(self, prompt):
        """
        Event: On prepare system prompt

        :param prompt: Prompt
        :return: Prompt
        """
        return prompt

    def on_ai_name(self, name):
        """
        Event: On set AI name

        :param name: Name
        :return: Name
        """
        return name

    def on_user_name(self, name):
        """
        Event: On set username

        :param name: Name
        :return: Name
        """
        return name

    def on_enable(self):
        """Event: On plugin enable"""
        pass

    def on_disable(self):
        """Event: On plugin disable"""
        pass

    def on_input_before(self, text):
        """
        Event: Before input

        :param text: Text
        """
        return text

    def on_ctx_before(self, ctx):
        """
        Event: Before ctx

        :param ctx: Text
        """
        return ctx

    def on_ctx_after(self, ctx):
        """
        Event: After ctx

        :param ctx: ctx
        """
        return ctx

    def is_cmd_allowed(self, cmd):
        """
        Checks if cmd is allowed

        :param cmd: Command
        :return: True if allowed
        """
        key = "cmd_" + cmd
        if key in self.options and self.options[key]["value"] is True:
            return True
        return False

    def cmd_syntax(self, syntax):
        """
        Event: On cmd syntax prepare

        :param syntax: Syntax
        :return: Syntax
        """
        syntax += '\n"code_execute": create and execute Python code, params: "filename", "code"'
        syntax += '\n"code_execute_file": execute Python code from existing file, params: "filename"'
        syntax += '\n"sys_exec": execute ANY system command, script or application in user\'s environment, ' \
                  'params: "command" '
        return syntax

    def cmd(self, ctx, cmds):
        """
        Execute command
        :param ctx: Context
        :param cmds: Commands list
        :return: Context
        """
        msg = None
        for item in cmds:
            try:
                if item["cmd"] in self.allowed_cmds:

                    # prepare request item for result
                    request_item = {"cmd": item["cmd"]}

                    if item["cmd"] == "code_execute_file" and self.is_cmd_allowed("code_execute_file"):
                        try:
                            msg = "Executing Python file: {}".format(item["params"]['filename'])
                            print(msg)
                            path = os.path.join(self.window.config.path, 'output', item["params"]['filename'])

                            # check if file exists
                            if not os.path.isfile(path):
                                msg = "File not found: {}".format(item["params"]['filename'])
                                ctx.results.append({"request": request_item, "result": "File not found"})
                                ctx.reply = True  # send result message
                                continue

                            # run code
                            cmd = self.options['python_cmd_tpl']['value'].format(filename=path)
                            print("Running command: {}".format(cmd))
                            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                                       stderr=subprocess.PIPE)
                            stdout, stderr = process.communicate()
                            result = None
                            if stdout:
                                result = stdout.decode("utf-8")
                            if stderr:
                                result = stderr.decode("utf-8")
                            if result is None:
                                result = "No result (STDOUT/STDERR empty)"
                            ctx.results.append({"request": request_item, "result": result})
                            print("Result (STDOUT): {}".format(result))
                            ctx.reply = True  # send result message
                        except Exception as e:
                            ctx.results.append({"request": request_item, "result": "Error {}".format(e)})
                            ctx.reply = True
                            print("Error: {}".format(e))

                    elif item["cmd"] == "code_execute" and self.is_cmd_allowed("code_execute"):
                        try:
                            msg = "Saving Python file: {}".format(item["params"]['filename'])
                            print(msg)
                            path = os.path.join(self.window.config.path, 'output', item["params"]['filename'])
                            data = item["params"]['code']
                            with open(path, 'w', encoding="utf-8") as file:
                                file.write(data)
                                file.close()

                            # run code
                            cmd = self.options['python_cmd_tpl']['value'].format(filename=path)
                            print("Running command: {}".format(cmd))
                            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                                       stderr=subprocess.PIPE)
                            stdout, stderr = process.communicate()
                            result = None
                            if stdout:
                                result = stdout.decode("utf-8")
                            if stderr:
                                result = stderr.decode("utf-8")
                            if result is None:
                                result = "No result (STDOUT/STDERR empty)"
                            ctx.results.append({"request": request_item, "result": result})
                            print("Result (STDOUT): {}".format(result))
                            ctx.reply = True  # send result message
                        except Exception as e:
                            ctx.results.append({"request": item, "result": "Error {}".format(e)})
                            ctx.reply = True
                            print("Error: {}".format(e))

                    elif item["cmd"] == "sys_exec" and self.is_cmd_allowed("sys_exec"):
                        try:
                            msg = "Executing system command: {}".format(item["params"]['command'])
                            print(msg)
                            print("Running command: {}".format(item["params"]['command']))
                            process = subprocess.Popen(item["params"]['command'], shell=True, stdout=subprocess.PIPE,
                                                       stderr=subprocess.PIPE)
                            stdout, stderr = process.communicate()
                            result = None
                            if stdout:
                                result = stdout.decode("utf-8")
                            if stderr:
                                result = stderr.decode("utf-8")
                            if result is None:
                                result = "No result (STDOUT/STDERR empty)"
                            ctx.results.append({"request": request_item, "result": result})
                            print("Result (STDOUT): {}".format(result))
                            ctx.reply = True  # send result message
                        except Exception as e:
                            ctx.results.append({"request": request_item, "result": "Error {}".format(e)})
                            ctx.reply = True
                            print("Error: {}".format(e))
            except Exception as e:
                ctx.results.append({"request": item, "result": "Error {}".format(e)})
                ctx.reply = True
                print("Error: {}".format(e))

        if msg is not None:
            self.window.statusChanged.emit(msg)
        return ctx
