#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.04 10:00:00                  #
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
        self.options = {}
        self.window = None
        self.order = 100
        self.allowed_cmds = ["code_execute", "sys_exec"]

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
        """Event: On user send text"""
        return text

    def on_ctx_begin(self, ctx):
        """Event: On new context begin"""
        return ctx

    def on_ctx_end(self, ctx):
        """Event: On context end"""
        return ctx

    def on_system_prompt(self, prompt):
        """Event: On prepare system prompt"""
        return prompt

    def on_ai_name(self, name):
        """Event: On set AI name"""
        return name

    def on_user_name(self, name):
        """Event: On set username"""
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

    def cmd_syntax(self, syntax):
        """Event: On cmd syntax prepare"""
        syntax += '\n"code_execute": create and execute Python code, params: "filename", "code"'
        syntax += '\n"sys_exec": execute system command, params: "command"'
        return syntax

    def cmd(self, ctx, cmds):
        msg = None
        for item in cmds:
            try:
                if item["cmd"] in self.allowed_cmds:
                    if item["cmd"] == "code_execute":
                        msg = "Saving Python file: {}".format(item["params"]['filename'])
                        path = os.path.join(self.window.config.path, 'output', item["params"]['filename'])
                        data = item["params"]['code']
                        with open(path, 'w', encoding="utf-8") as file:
                            file.write(data)
                            file.close()

                        # run code
                        process = subprocess.Popen("python3 {}".format(path), shell=True, stdout=subprocess.PIPE,
                                                    stderr=subprocess.PIPE)
                        stdout, stderr = process.communicate()
                        if stdout:
                            ctx.results.append({"request": item, "result": stdout.decode("utf-8")})
                        if stderr:
                            ctx.results.append({"request": item, "result": stderr.decode("utf-8")})
                        ctx.reply = True  # send result message

                    elif item["cmd"] == "sys_exec":
                        msg = "Executing system command: {}".format(item["params"]['command'])
                        process = subprocess.Popen(item["params"]['command'], shell=True, stdout=subprocess.PIPE,
                                                   stderr=subprocess.PIPE)
                        stdout, stderr = process.communicate()
                        if stdout:
                            ctx.results.append({"request": item, "result": stdout.decode("utf-8")})
                        if stderr:
                            ctx.results.append({"request": item, "result": stderr.decode("utf-8")})
                        ctx.reply = True  # send result message
            except Exception as e:
                print("Error: {}".format(e))

        if msg is not None:
            print(msg)
            self.window.statusChanged.emit(msg)
        return ctx

