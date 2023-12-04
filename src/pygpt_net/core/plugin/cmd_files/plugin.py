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
from datetime import datetime

from ..base_plugin import BasePlugin


class Plugin(BasePlugin):
    def __init__(self):
        super(Plugin, self).__init__()
        self.id = "cmd_files"
        self.name = "Command: Files I/O"
        self.description = "Provides commands to read and write files"
        self.options = {}
        self.window = None
        self.order = 100
        self.allowed_cmds = ["save_file", "read_file", "append_file", "delete_file", "list_files", "list_dirs", "mkdir"]

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
        syntax += '\n"save_file": save data to file, params: "filename", "data"'
        syntax += '\n"read_file": read data from file, params: "filename"'
        syntax += '\n"append_file": append data to file, params: "filename", "data"'
        syntax += '\n"delete_file": delete file, params: "filename"'
        syntax += '\n"list_files": list files in directory, params: "path"'
        syntax += '\n"list_dirs": list directories in directory, params: "path"'
        syntax += '\n"mkdir": create directory, params: "path"'
        return syntax

    def cmd(self, ctx, cmds):
        msg = None
        for item in cmds:
            try:
                if item["cmd"] in self.allowed_cmds:
                    if item["cmd"] == "save_file":
                        msg = "Saving file: {}".format(item["params"]['filename'])
                        path = os.path.join(self.window.config.path, 'output', item["params"]['filename'])
                        data = item["params"]['data']
                        with open(path, 'w', encoding="utf-8") as file:
                            file.write(data)
                            file.close()
                            ctx.results.append({"request": item, "result": "OK"})
                    elif item["cmd"] == "append_file":
                        msg = "Appending file: {}".format(item["params"]['filename'])
                        path = os.path.join(self.window.config.path, 'output', item["params"]['filename'])
                        data = item["params"]['data']
                        with open(path, 'a', encoding="utf-8") as file:
                            file.write(data)
                            file.close()
                            ctx.results.append({"request": item, "result": "OK"})
                    elif item["cmd"] == "read_file":
                        msg = "Reading file: {}".format(item["params"]['filename'])
                        path = os.path.join(self.window.config.path, 'output', item["params"]['filename'])
                        if os.path.exists(path):
                            with open(path, 'r', encoding="utf-8") as file:
                                data = file.read()
                                ctx.results.append({"request": item, "result": data})
                                ctx.reply = True  # send result message
                                file.close()
                    elif item["cmd"] == "delete_file":
                        msg = "Deleting file: {}".format(item["params"]['filename'])
                        path = os.path.join(self.window.config.path, 'output', item["params"]['filename'])
                        if os.path.exists(path):
                            os.remove(path)
                            ctx.results.append({"request": item, "result": "OK"})
                    elif item["cmd"] == "list_files":
                        msg = "Listing files: {}".format(item["params"]['path'])
                        path = os.path.join(self.window.config.path, 'output', item["params"]['path'])
                        if os.path.exists(path):
                            files = os.listdir(path)
                            ctx.results.append({"request": item, "result": files})
                            ctx.reply = True
                    elif item["cmd"] == "list_dirs":
                        msg = "Listing directories: {}".format(item["params"]['path'])
                        path = os.path.join(self.window.config.path, 'output', item["params"]['path'])
                        if os.path.exists(path):
                            dirs = os.listdir(path)
                            ctx.results.append({"request": item, "result": dirs})
                            ctx.reply = True
                    elif item["cmd"] == "mkdir":
                        msg = "Creating directory: {}".format(item["params"]['path'])
                        path = os.path.join(self.window.config.path, 'output', item["params"]['path'])
                        if not os.path.exists(path):
                            os.makedirs(path)
                            ctx.results.append({"request": item, "result": "OK"})
            except Exception as e:
                print("Error: {}".format(e))

        if msg is not None:
            print(msg)
            self.window.statusChanged.emit(msg)
        return ctx

