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
import shutil
import ssl
from urllib.request import Request, urlopen

from ..base_plugin import BasePlugin


class Plugin(BasePlugin):
    def __init__(self):
        super(Plugin, self).__init__()
        self.id = "cmd_files"
        self.name = "Command: Files I/O"
        self.description = "Provides commands to read and write files"
        self.window = None
        self.order = 100
        self.allowed_cmds = [
            "save_file",
            "read_file",
            "append_file",
            "delete_file",
            "list_files",
            "list_dirs",
            "mkdir",
            "download_file",
            "rmdir",
            "copy_file",
            "copy_dir",
            "move",
        ]
        self.init_options()

    def init_options(self):
        """
        Initializes options
        """
        self.add_option("cmd_read_file", "bool", True,
                        "Enable: Read file", "Allows `read_file` command execution")
        self.add_option("cmd_append_file", "bool", True,
                        "Enable: Append to file", "Allows `append_file` command execution")
        self.add_option("cmd_save_file", "bool", True,
                        "Enable: Save file", "Allows `save_file` command execution")
        self.add_option("cmd_delete_file", "bool", True,
                        "Enable: Delete file", "Allows `delete_file` command execution")
        self.add_option("cmd_list_files", "bool", True,
                        "Enable: List files (ls)", "Allows `list_files` command execution")
        self.add_option("cmd_list_dirs", "bool", True,
                        "Enable: List directories (ls)", "Allows `list_dirs` command execution")
        self.add_option("cmd_mkdir", "bool", True,
                        "Enable: Directory creation (mkdir)", "Allows `mkdir` command execution")
        self.add_option("cmd_download_file", "bool", True,
                        "Enable: Downloading files", "Allows `download_file` command execution")
        self.add_option("cmd_rmdir", "bool", True,
                        "Enable: Removing directories", "Allows `rmdir` command execution")
        self.add_option("cmd_copy_file", "bool", True,
                        "Enable: Copying files", "Allows `copy` command execution")
        self.add_option("cmd_copy_dir", "bool", True,
                        "Enable: Copying directories (recursive)", "Allows `copy_dir` command execution")
        self.add_option("cmd_move", "bool", True,
                        "Enable: Move files and directories (rename)", "Allows `move` command execution")

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
        if self.is_cmd_allowed("download_file"):
            syntax += '\n"download_file": download file, params: "src", "dst"'
        if self.is_cmd_allowed("rmdir"):
            syntax += '\n"rmdir": remove directory, params: "path"'
        if self.is_cmd_allowed("copy_file"):
            syntax += '\n"copy_file": copy file, params: "src", "dst"'
        if self.is_cmd_allowed("copy_dir"):
            syntax += '\n"copy_dir": recursive copy directory, params: "src", "dst"'
        if self.is_cmd_allowed("move"):
            syntax += '\n"move": move file or directory, params: "src", "dst"'
        return syntax

    def cmd(self, ctx, cmds):
        """
        Event: On cmd
        :param ctx: Context
        :param cmds: Commands
        :return: Context
        """
        msg = None
        for item in cmds:
            try:
                if item["cmd"] in self.allowed_cmds and self.is_cmd_allowed(item["cmd"]):

                    # prepare request item for result
                    request_item = {"cmd": item["cmd"]}

                    if item["cmd"] == "save_file":
                        try:
                            msg = "Saving file: {}".format(item["params"]['filename'])
                            print(msg)
                            path = os.path.join(self.window.config.path, 'output', item["params"]['filename'])
                            data = item["params"]['data']
                            with open(path, 'w', encoding="utf-8") as file:
                                file.write(data)
                                file.close()
                                ctx.results.append({"request": request_item, "result": "OK"})
                                ctx.reply = True
                                print("File saved: {}".format(path))
                        except Exception as e:
                            ctx.results.append({"request": request_item, "result": "Error {}".format(e)})
                            ctx.reply = True
                            print("Error: {}".format(e))
                    elif item["cmd"] == "append_file" and self.is_cmd_allowed("append_file"):
                        try:
                            msg = "Appending file: {}".format(item["params"]['filename'])
                            print(msg)
                            path = os.path.join(self.window.config.path, 'output', item["params"]['filename'])
                            data = item["params"]['data']
                            with open(path, 'a', encoding="utf-8") as file:
                                file.write(data)
                                file.close()
                                ctx.results.append({"request": request_item, "result": "OK"})
                                ctx.reply = True
                                print("File appended: {}".format(path))
                        except Exception as e:
                            ctx.results.append({"request": request_item, "result": "Error {}".format(e)})
                            ctx.reply = True
                            print("Error: {}".format(e))
                    elif item["cmd"] == "read_file" and self.is_cmd_allowed("read_file"):
                        try:
                            msg = "Reading file: {}".format(item["params"]['filename'])
                            print(msg)
                            path = os.path.join(self.window.config.path, 'output', item["params"]['filename'])
                            if os.path.exists(path):
                                with open(path, 'r', encoding="utf-8") as file:
                                    data = file.read()
                                    ctx.results.append({"request": request_item, "result": data})
                                    ctx.reply = True  # send result message
                                    file.close()
                                    print("File read: {}".format(path))
                            else:
                                ctx.results.append({"request": request_item, "result": "File not found"})
                                ctx.reply = True
                                print("File not found: {}".format(path))
                        except Exception as e:
                            ctx.results.append({"request": request_item, "result": "Error {}".format(e)})
                            ctx.reply = True
                            print("Error: {}".format(e))
                    elif item["cmd"] == "delete_file" and self.is_cmd_allowed("delete_file"):
                        try:
                            msg = "Deleting file: {}".format(item["params"]['filename'])
                            print(msg)
                            path = os.path.join(self.window.config.path, 'output', item["params"]['filename'])
                            if os.path.exists(path):
                                os.remove(path)
                                ctx.results.append({"request": request_item, "result": "OK"})
                                ctx.reply = True
                                print("File deleted: {}".format(path))
                            else:
                                ctx.results.append({"request": request_item, "result": "File not found"})
                                ctx.reply = True
                                print("File not found: {}".format(path))
                        except Exception as e:
                            ctx.results.append({"request": request_item, "result": "Error {}".format(e)})
                            ctx.reply = True
                            print("Error: {}".format(e))
                    elif item["cmd"] == "list_files" and self.is_cmd_allowed("list_files"):
                        try:
                            msg = "Listing files: {}".format(item["params"]['path'])
                            print(msg)
                            path = os.path.join(self.window.config.path, 'output', item["params"]['path'])
                            if os.path.exists(path):
                                files = os.listdir(path)
                                ctx.results.append({"request": request_item, "result": files})
                                ctx.reply = True
                                print("Files listed: {}".format(path))
                                print("Result: {}".format(files))
                            else:
                                ctx.results.append({"request": request_item, "result": "Directory not found"})
                                ctx.reply = True
                                print("Directory not found: {}".format(path))
                        except Exception as e:
                            ctx.results.append({"request": request_item, "result": "Error {}".format(e)})
                            ctx.reply = True
                            print("Error: {}".format(e))
                    elif item["cmd"] == "list_dirs" and self.is_cmd_allowed("list_dirs"):
                        try:
                            msg = "Listing directories: {}".format(item["params"]['path'])
                            print(msg)
                            path = os.path.join(self.window.config.path, 'output', item["params"]['path'])
                            if os.path.exists(path):
                                dirs = os.listdir(path)
                                ctx.results.append({"request": request_item, "result": dirs})
                                ctx.reply = True
                                print("Directories listed: {}".format(path))
                                print("Result: {}".format(dirs))
                            else:
                                ctx.results.append({"request": request_item, "result": "Directory not found"})
                                ctx.reply = True
                                print("Directory not found: {}".format(path))
                        except Exception as e:
                            ctx.results.append({"request": request_item, "result": "Error {}".format(e)})
                            ctx.reply = True
                            print("Error: {}".format(e))
                    elif item["cmd"] == "mkdir" and self.is_cmd_allowed("mkdir"):
                        try:
                            msg = "Creating directory: {}".format(item["params"]['path'])
                            print(msg)
                            path = os.path.join(self.window.config.path, 'output', item["params"]['path'])
                            if not os.path.exists(path):
                                os.makedirs(path)
                                ctx.results.append({"request": request_item, "result": "OK"})
                                ctx.reply = True
                                print("Directory created: {}".format(path))
                            else:
                                ctx.results.append({"request": request_item, "result": "Directory already exists"})
                                ctx.reply = True
                                print("Directory already exists: {}".format(path))
                        except Exception as e:
                            ctx.results.append({"request": request_item, "result": "Error {}".format(e)})
                            ctx.reply = True
                            print("Error: {}".format(e))
                    elif item["cmd"] == "rmdir" and self.is_cmd_allowed("rmdir"):
                        try:
                            msg = "Deleting directory: {}".format(item["params"]['path'])
                            print(msg)
                            path = os.path.join(self.window.config.path, 'output', item["params"]['path'])
                            if os.path.exists(path):
                                shutil.rmtree(path)
                                ctx.results.append({"request": request_item, "result": "OK"})
                                ctx.reply = True
                                print("Directory deleted: {}".format(path))
                            else:
                                ctx.results.append({"request": request_item, "result": "Directory not found"})
                                ctx.reply = True
                                print("Directory not found: {}".format(path))
                        except Exception as e:
                            ctx.results.append({"request": request_item, "result": "Error {}".format(e)})
                            ctx.reply = True
                            print("Error: {}".format(e))
                    elif item["cmd"] == "download_file" and self.is_cmd_allowed("download_file"):
                        try:
                            dst = os.path.join(self.window.config.path, 'output', item["params"]['dst'])
                            msg = "Downloading file: {} into {}".format(item["params"]['src'], dst)
                            print(msg)

                            # Check if src is URL
                            if item["params"]['src'].startswith("http"):
                                src = item["params"]['src']
                                # Download file from URL
                                req = Request(
                                    url=src,
                                    headers={'User-Agent': 'Mozilla/5.0'}
                                )
                                context = ssl.create_default_context()
                                context.check_hostname = False
                                context.verify_mode = ssl.CERT_NONE
                                with urlopen(req, context=context, timeout=4) as response, open(dst, 'wb') as out_file:
                                    shutil.copyfileobj(response, out_file)
                            else:
                                # Handle local file paths
                                src = os.path.join(self.window.config.path, 'output', item["params"]['src'])

                                # Copy local file
                                with open(src, 'rb') as in_file, open(dst, 'wb') as out_file:
                                    shutil.copyfileobj(in_file, out_file)

                            # handle result
                            ctx.results.append({"request": request_item, "result": "OK"})
                            ctx.reply = True
                            print("File downloaded: {} into {}".format(src, dst))
                        except Exception as e:
                            ctx.results.append({"request": request_item, "result": "Error {}".format(e)})
                            ctx.reply = True
                            print("Error: {}".format(e))
                    elif item["cmd"] == "copy_file" and self.is_cmd_allowed("copy_file"):
                        try:
                            msg = "Copying file: {} into {}".format(item["params"]['src'], item["params"]['dst'])
                            print(msg)
                            dst = os.path.join(self.window.config.path, 'output', item["params"]['dst'])
                            src = os.path.join(self.window.config.path, 'output', item["params"]['src'])
                            shutil.copyfile(src, dst)
                            ctx.results.append({"request": request_item, "result": "OK"})
                            ctx.reply = True
                            print("File copied: {} into {}".format(src, dst))
                        except Exception as e:
                            ctx.results.append({"request": request_item, "result": "Error {}".format(e)})
                            ctx.reply = True
                            print("Error: {}".format(e))
                    elif item["cmd"] == "copy_dir" and self.is_cmd_allowed("copy_dir"):
                        try:
                            msg = "Copying directory: {} into {}".format(item["params"]['src'], item["params"]['dst'])
                            print(msg)
                            dst = os.path.join(self.window.config.path, 'output', item["params"]['dst'])
                            src = os.path.join(self.window.config.path, 'output', item["params"]['src'])
                            shutil.copytree(src, dst)
                            ctx.results.append({"request": request_item, "result": "OK"})
                            ctx.reply = True
                            print("Directory copied: {} into {}".format(src, dst))
                        except Exception as e:
                            ctx.results.append({"request": request_item, "result": "Error {}".format(e)})
                            ctx.reply = True
                            print("Error: {}".format(e))
                    elif item["cmd"] == "move" and self.is_cmd_allowed("move"):
                        try:
                            msg = "Moving: {} into {}".format(item["params"]['src'], item["params"]['dst'])
                            print(msg)
                            dst = os.path.join(self.window.config.path, 'output', item["params"]['dst'])
                            src = os.path.join(self.window.config.path, 'output', item["params"]['src'])
                            shutil.move(src, dst)
                            ctx.results.append({"request": request_item, "result": "OK"})
                            ctx.reply = True
                            print("Moved: {} into {}".format(src, dst))
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

