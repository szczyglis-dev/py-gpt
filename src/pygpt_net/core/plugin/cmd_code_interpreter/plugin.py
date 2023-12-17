#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.17 22:00:00                  #
# ================================================== #
import os.path
import subprocess

from ..base_plugin import BasePlugin


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
        """
        return self.options

    def attach(self, window):
        """
        Attach window

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
        :return: Text
        """
        return text

    def on_ctx_before(self, ctx):
        """
        Event: Before ctx

        :param ctx: Context
        :return: Context

        """
        return ctx

    def on_ctx_after(self, ctx):
        """
        Event: After ctx

        :param ctx: Context
        :return: Context
        """
        return ctx

    def is_cmd_allowed(self, cmd):
        """
        Check if cmd is allowed

        :param cmd: Command
        :return: True if allowed
        """
        key = "cmd_" + cmd
        if self.has_option(key) and self.get_option_value(key) is True:
            return True
        return False

    def log(self, msg):
        """
        Log message to console

        :param msg: Message to log
        """
        self.window.log('[CMD] ' + str(msg))
        print('[CMD] ' + str(msg))

    def cmd_syntax(self, syntax):
        """
        Event: On cmd syntax prepare

        :param syntax: Syntax
        :return: Syntax
        """
        for item in self.allowed_cmds:
            if self.is_cmd_allowed(item):
                key = "syntax_" + item
                if self.has_option(key):
                    syntax += "\n" + str(self.get_option_value(key))
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
                    ctx.reply = True  # send result message
                    result = None

                    # code_execute (from existing file)
                    if item["cmd"] == "code_execute_file" and self.is_cmd_allowed("code_execute_file"):
                        try:
                            # execute code from file
                            msg = "Executing Python file: {}".format(item["params"]['filename'])
                            self.log(msg)
                            path = os.path.join(self.window.config.path, 'output', item["params"]['filename'])

                            # check if file exists
                            if not os.path.isfile(path):
                                msg = "File not found: {}".format(item["params"]['filename'])
                                ctx.results.append({"request": request_item, "result": "File not found"})
                                continue

                            # run code
                            cmd = self.get_option_value('python_cmd_tpl').format(filename=path)
                            self.log("Running command: {}".format(cmd))
                            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                                       stderr=subprocess.PIPE)
                            stdout, stderr = process.communicate()
                            if stdout:
                                result = stdout.decode("utf-8")
                                self.log("STDOUT: {}".format(result))
                            if stderr:
                                result = stderr.decode("utf-8")
                                self.log("STDERR: {}".format(result))
                            if result is None:
                                result = "No result (STDOUT/STDERR empty)"
                                self.log(result)
                            ctx.results.append({"request": request_item, "result": result})
                        except Exception as e:
                            ctx.results.append({"request": request_item, "result": "Error: {}".format(e)})
                            self.log("Error: {}".format(e))

                    # code_execute (generate and execute)
                    elif item["cmd"] == "code_execute" and self.is_cmd_allowed("code_execute"):
                        try:
                            # write code to file
                            msg = "Saving Python file: {}".format(item["params"]['filename'])
                            self.log(msg)
                            path = os.path.join(self.window.config.path, 'output', item["params"]['filename'])
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
                            if stdout:
                                result = stdout.decode("utf-8")
                                self.log("STDOUT: {}".format(result))
                            if stderr:
                                result = stderr.decode("utf-8")
                                self.log("STDERR: {}".format(result))
                            if result is None:
                                result = "No result (STDOUT/STDERR empty)"
                                self.log(result)
                            ctx.results.append({"request": request_item, "result": result})
                        except Exception as e:
                            ctx.results.append({"request": request_item, "result": "Error: {}".format(e)})
                            self.log("Error: {}".format(e))

                    # sys_exec
                    elif item["cmd"] == "sys_exec" and self.is_cmd_allowed("sys_exec"):
                        try:
                            # execute system command
                            msg = "Executing system command: {}".format(item["params"]['command'])
                            self.log(msg)
                            self.log("Running command: {}".format(item["params"]['command']))
                            process = subprocess.Popen(item["params"]['command'], shell=True, stdout=subprocess.PIPE,
                                                       stderr=subprocess.PIPE)
                            stdout, stderr = process.communicate()
                            if stdout:
                                result = stdout.decode("utf-8")
                                self.log("STDOUT: {}".format(result))
                            if stderr:
                                result = stderr.decode("utf-8")
                                self.log("STDERR: {}".format(result))
                            if result is None:
                                result = "No result (STDOUT/STDERR empty)"
                                self.log(result)
                            ctx.results.append({"request": request_item, "result": result})
                        except Exception as e:
                            ctx.results.append({"request": request_item, "result": "Error: {}".format(e)})
                            self.log("Error: {}".format(e))
            except Exception as e:
                ctx.results.append({"request": item, "result": "Error: {}".format(e)})
                ctx.reply = True  # send result message
                self.log("Error: {}".format(e))

        if msg is not None:
            self.window.statusChanged.emit(msg)
        return ctx
