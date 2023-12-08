#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.08 18:00:00                  #
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
        self.options["cmd_read_file"] = {
            "type": "bool",
            "slider": False,
            "label": "Enable: Read file",
            "description": "Allows `read_file` command execution",
            "tooltip": "",
            "value": True,
            "min": None,
            "max": None,
            "multiplier": None,
            "step": None,
        }
        self.options["cmd_append_file"] = {
            "type": "bool",
            "slider": False,
            "label": "Enable: Append to file",
            "description": "Allows `append_file` command execution",
            "tooltip": "",
            "value": True,
            "min": None,
            "max": None,
            "multiplier": None,
            "step": None,
        }
        self.options["cmd_save_file"] = {
            "type": "bool",
            "slider": False,
            "label": "Enable: Save file",
            "description": "Allows `save_file` command execution",
            "tooltip": "",
            "value": True,
            "min": None,
            "max": None,
            "multiplier": None,
            "step": None,
        }
        self.options["cmd_delete_file"] = {
            "type": "bool",
            "slider": False,
            "label": "Enable: Delete file",
            "description": "Allows `delete_file` command execution",
            "tooltip": "",
            "value": True,
            "min": None,
            "max": None,
            "multiplier": None,
            "step": None,
        }
        self.options["cmd_list_files"] = {
            "type": "bool",
            "slider": False,
            "label": "Enable: List files (ls)",
            "description": "Allows `list_files` command execution",
            "tooltip": "",
            "value": True,
            "min": None,
            "max": None,
            "multiplier": None,
            "step": None,
        }
        self.options["cmd_list_dirs"] = {
            "type": "bool",
            "slider": False,
            "label": "Enable: List directories (ls)",
            "description": "Allows `list_dirs` command execution",
            "tooltip": "",
            "value": True,
            "min": None,
            "max": None,
            "multiplier": None,
            "step": None,
        }
        self.options["cmd_mkdir"] = {
            "type": "bool",
            "slider": False,
            "label": "Enable: Directory creation (mkdir)",
            "description": "Allows `mkdir` command execution",
            "tooltip": "",
            "value": True,
            "min": None,
            "max": None,
            "multiplier": None,
            "step": None,
        }
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

    def is_cmd_allowed(self, cmd):
        """Checks if cmd is allowed"""
        key = "cmd_" + cmd
        if key in self.options and self.options[key]["value"] is True:
            return True
        return False

    def cmd_syntax(self, syntax):
        """Event: On cmd syntax prepare"""
        if self.is_cmd_allowed("read_file"):
            syntax += '\n"read_file": read data from file, params: "filename"'
        if self.is_cmd_allowed("append_file"):
            syntax += '\n"append_file": append data to file, params: "filename", "data"'
        if self.is_cmd_allowed("save_file"):
            syntax += '\n"save_file": save data to file, params: "filename", "data"'
        if self.is_cmd_allowed("delete_file"):
            syntax += '\n"delete_file": delete file, params: "filename"'
        if self.is_cmd_allowed("list_files"):
            syntax += '\n"list_files": list files in directory, params: "path"'
        if self.is_cmd_allowed("list_dirs"):
            syntax += '\n"list_dirs": list directories in directory, params: "path"'
        if self.is_cmd_allowed("mkdir"):
            syntax += '\n"mkdir": create directory, params: "path"'
        return syntax

    def cmd(self, ctx, cmds):
        msg = None
        for item in cmds:
            try:
                if item["cmd"] in self.allowed_cmds and self.is_cmd_allowed(item["cmd"]):
                    if item["cmd"] == "save_file":
                        msg = "Saving file: {}".format(item["params"]['filename'])
                        print(msg)
                        path = os.path.join(self.window.config.path, 'output', item["params"]['filename'])
                        data = item["params"]['data']
                        with open(path, 'w', encoding="utf-8") as file:
                            file.write(data)
                            file.close()
                            ctx.results.append({"request": item, "result": "OK"})
                            ctx.reply = True
                            print("File saved: {}".format(path))
                    elif item["cmd"] == "append_file" and self.is_cmd_allowed("append_file"):
                        msg = "Appending file: {}".format(item["params"]['filename'])
                        print(msg)
                        path = os.path.join(self.window.config.path, 'output', item["params"]['filename'])
                        data = item["params"]['data']
                        with open(path, 'a', encoding="utf-8") as file:
                            file.write(data)
                            file.close()
                            ctx.results.append({"request": item, "result": "OK"})
                            ctx.reply = True
                            print("File appended: {}".format(path))
                    elif item["cmd"] == "read_file" and self.is_cmd_allowed("read_file"):
                        msg = "Reading file: {}".format(item["params"]['filename'])
                        print(msg)
                        path = os.path.join(self.window.config.path, 'output', item["params"]['filename'])
                        if os.path.exists(path):
                            with open(path, 'r', encoding="utf-8") as file:
                                data = file.read()
                                ctx.results.append({"request": item, "result": data})
                                ctx.reply = True  # send result message
                                file.close()
                                print("File read: {}".format(path))
                        else:
                            ctx.results.append({"request": item, "result": "File not found"})
                            ctx.reply = True
                            print("File not found: {}".format(path))
                    elif item["cmd"] == "delete_file" and self.is_cmd_allowed("delete_file"):
                        msg = "Deleting file: {}".format(item["params"]['filename'])
                        print(msg)
                        path = os.path.join(self.window.config.path, 'output', item["params"]['filename'])
                        if os.path.exists(path):
                            os.remove(path)
                            ctx.results.append({"request": item, "result": "OK"})
                            ctx.reply = True
                            print("File deleted: {}".format(path))
                        else:
                            ctx.results.append({"request": item, "result": "File not found"})
                            ctx.reply = True
                            print("File not found: {}".format(path))
                    elif item["cmd"] == "list_files" and self.is_cmd_allowed("list_files"):
                        msg = "Listing files: {}".format(item["params"]['path'])
                        print(msg)
                        path = os.path.join(self.window.config.path, 'output', item["params"]['path'])
                        if os.path.exists(path):
                            files = os.listdir(path)
                            ctx.results.append({"request": item, "result": files})
                            ctx.reply = True
                            print("Files listed: {}".format(path))
                            print("Result: {}".format(files))
                        else:
                            ctx.results.append({"request": item, "result": "Directory not found"})
                            ctx.reply = True
                            print("Directory not found: {}".format(path))
                    elif item["cmd"] == "list_dirs" and self.is_cmd_allowed("list_dirs"):
                        msg = "Listing directories: {}".format(item["params"]['path'])
                        print(msg)
                        path = os.path.join(self.window.config.path, 'output', item["params"]['path'])
                        if os.path.exists(path):
                            dirs = os.listdir(path)
                            ctx.results.append({"request": item, "result": dirs})
                            ctx.reply = True
                            print("Directories listed: {}".format(path))
                            print("Result: {}".format(dirs))
                        else:
                            ctx.results.append({"request": item, "result": "Directory not found"})
                            ctx.reply = True
                            print("Directory not found: {}".format(path))
                    elif item["cmd"] == "mkdir" and self.is_cmd_allowed("mkdir"):
                        msg = "Creating directory: {}".format(item["params"]['path'])
                        print(msg)
                        path = os.path.join(self.window.config.path, 'output', item["params"]['path'])
                        if not os.path.exists(path):
                            os.makedirs(path)
                            ctx.results.append({"request": item, "result": "OK"})
                            ctx.reply = True
                            print("Directory created: {}".format(path))
                        else:
                            ctx.results.append({"request": item, "result": "Directory already exists"})
                            ctx.reply = True
                            print("Directory already exists: {}".format(path))
            except Exception as e:
                ctx.results.append({"request": item, "result": "Error {}".format(e)})
                ctx.reply = True
                print("Error: {}".format(e))

        if msg is not None:
            self.window.statusChanged.emit(msg)
        return ctx

