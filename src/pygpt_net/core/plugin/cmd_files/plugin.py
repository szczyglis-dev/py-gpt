#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.14 11:00:00                  #
# ================================================== #
import mimetypes
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
            "read_file",
            "save_file",
            "append_file",
            "delete_file",
            "list_dir",
            "mkdir",
            "download_file",
            "rmdir",
            "copy_file",
            "copy_dir",
            "move",
            "is_dir",
            "is_file",
            "file_exists",
            "file_size",
            "file_info",
        ]
        self.init_options()

    def init_options(self):
        """
        Initializes options
        """
        # cmd enable/disable
        self.add_option("cmd_read_file", "bool", True,
                        "Enable: Read file", "Allows `read_file` command execution")
        self.add_option("cmd_save_file", "bool", True,
                        "Enable: Save file", "Allows `save_file` command execution")
        self.add_option("cmd_append_file", "bool", True,
                        "Enable: Append to file", "Allows `append_file` command execution")
        self.add_option("cmd_delete_file", "bool", True,
                        "Enable: Delete file", "Allows `delete_file` command execution")
        self.add_option("cmd_list_dir", "bool", True,
                        "Enable: List files in directory (ls)", "Allows `list_dir` command execution")
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
        self.add_option("cmd_is_dir", "bool", True,
                        "Enable: Check if path is directory", "Allows `is_dir` command execution")
        self.add_option("cmd_is_file", "bool", True,
                        "Enable: Check if path is file", "Allows `is_file` command execution")
        self.add_option("cmd_file_exists", "bool", True,
                        "Enable: Check if file or directory exists", "Allows `file_exists` command execution")
        self.add_option("cmd_file_size", "bool", True,
                        "Enable: Get file size", "Allows `file_size` command execution")
        self.add_option("cmd_file_info", "bool", True,
                        "Enable: Get file info", "Allows `file_info` command execution")

        # cmd syntax (prompt/instruction)
        self.add_option("syntax_read_file", "textarea", '"read_file": read data from file, params: "filename"',
                        "Syntax: read_file",
                        "Syntax for reading files", advanced=True)
        self.add_option("syntax_save_file", "textarea", '"save_file": save data to file, params: "filename", "data"',
                        "Syntax: save_file",
                        "Syntax for saving files", advanced=True)
        self.add_option("syntax_append_file", "textarea",
                        '"append_file": append data to file, params: "filename", "data"',
                        "Syntax: append_file",
                        "Syntax for appending to files", advanced=True)
        self.add_option("syntax_delete_file", "textarea", '"delete_file": delete file, params: "filename"',
                        "Syntax: delete_file",
                        "Syntax for deleting files", advanced=True)
        self.add_option("syntax_list_dir", "textarea", '"list_dir": list files and dirs in directory, params: "path"',
                        "Syntax: list_dir",
                        "Syntax for listing files", advanced=True)
        self.add_option("syntax_mkdir", "textarea", '"mkdir": create directory, params: "path"',
                        "Syntax: mkdir",
                        "Syntax for directory creation", advanced=True)
        self.add_option("syntax_download_file", "textarea", '"download_file": download file, params: "src", "dst"',
                        "Syntax: download_file",
                        "Syntax for downloading files", advanced=True)
        self.add_option("syntax_rmdir", "textarea", '"rmdir": remove directory, params: "path"',
                        "Syntax: rmdir",
                        "Syntax for removing directories", advanced=True)
        self.add_option("syntax_copy_file", "textarea", '"copy_file": copy file, params: "src", "dst"',
                        "Syntax: copy_file",
                        "Syntax for copying files", advanced=True)
        self.add_option("syntax_copy_dir", "textarea", '"copy_dir": recursive copy directory, params: "src", "dst"',
                        "Syntax: copy_dir",
                        "Syntax for recursive copying directories", advanced=True)
        self.add_option("syntax_move", "textarea", '"move": move file or directory, params: "src", "dst"',
                        "Syntax: move",
                        "Syntax for moving files and directories", advanced=True)
        self.add_option("syntax_is_dir", "textarea", '"is_dir": check if path is directory, params: "path"',
                        "Syntax: is_dir",
                        "Syntax for checking if path is directory", advanced=True)
        self.add_option("syntax_is_file", "textarea", '"is_file": check if path is file, params: "path"',
                        "Syntax: is_file",
                        "Syntax for checking if path is file", advanced=True)
        self.add_option("syntax_file_exists", "textarea", '"file_exists": check if file or directory exists, params: '
                                                          '"path"',
                        "Syntax: file_exists",
                        "Syntax for checking if file or directory exists", advanced=True)
        self.add_option("syntax_file_size", "textarea", '"file_size": get file size, params: "path"',
                        "Syntax: file_size",
                        "Syntax for getting file size", advanced=True)
        self.add_option("syntax_file_info", "textarea", '"file_info": get file info, params: "path"',
                        "Syntax: file_info",
                        "Syntax for getting file info", advanced=True)

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
        Checks if cmd is allowed

        :param cmd: Command
        :return: True if allowed
        """
        key = "cmd_" + cmd
        if key in self.options and self.options[key]["value"] is True:
            return True
        return False

    def log(self, msg):
        """
        Logs message to console

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
        for option in self.allowed_cmds:
            if self.is_cmd_allowed(option):
                key = "syntax_" + option
                if key in self.options:
                    syntax += "\n" + self.options[key]["value"]
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
                    ctx.reply = True  # send result message

                    # save file
                    if item["cmd"] == "save_file":
                        try:
                            msg = "Saving file: {}".format(item["params"]['filename'])
                            self.log(msg)
                            path = os.path.join(self.window.config.path, 'output', item["params"]['filename'])
                            data = item["params"]['data']
                            with open(path, 'w', encoding="utf-8") as file:
                                file.write(data)
                                file.close()
                                ctx.results.append({"request": request_item, "result": "OK"})
                                self.log("File saved: {}".format(path))
                        except Exception as e:
                            ctx.results.append({"request": request_item, "result": "Error: {}".format(e)})
                            self.log("Error: {}".format(e))

                    # append to file
                    elif item["cmd"] == "append_file" and self.is_cmd_allowed("append_file"):
                        try:
                            msg = "Appending file: {}".format(item["params"]['filename'])
                            self.log(msg)
                            path = os.path.join(self.window.config.path, 'output', item["params"]['filename'])
                            data = item["params"]['data']
                            with open(path, 'a', encoding="utf-8") as file:
                                file.write(data)
                                file.close()
                                ctx.results.append({"request": request_item, "result": "OK"})
                                self.log("File appended: {}".format(path))
                        except Exception as e:
                            ctx.results.append({"request": request_item, "result": "Error: {}".format(e)})
                            self.log("Error: {}".format(e))

                    # read file
                    elif item["cmd"] == "read_file" and self.is_cmd_allowed("read_file"):
                        try:
                            msg = "Reading file: {}".format(item["params"]['filename'])
                            self.log(msg)
                            path = os.path.join(self.window.config.path, 'output', item["params"]['filename'])
                            if os.path.exists(path):
                                with open(path, 'r', encoding="utf-8") as file:
                                    data = file.read()
                                    ctx.results.append({"request": request_item, "result": data})
                                    file.close()
                                    self.log("File read: {}".format(path))
                            else:
                                ctx.results.append({"request": request_item, "result": "File not found"})
                                self.log("File not found: {}".format(path))
                        except Exception as e:
                            ctx.results.append({"request": request_item, "result": "Error: {}".format(e)})
                            self.log("Error: {}".format(e))

                    # delete file
                    elif item["cmd"] == "delete_file" and self.is_cmd_allowed("delete_file"):
                        try:
                            msg = "Deleting file: {}".format(item["params"]['filename'])
                            self.log(msg)
                            path = os.path.join(self.window.config.path, 'output', item["params"]['filename'])
                            if os.path.exists(path):
                                os.remove(path)
                                ctx.results.append({"request": request_item, "result": "OK"})
                                self.log("File deleted: {}".format(path))
                            else:
                                ctx.results.append({"request": request_item, "result": "File not found"})
                                self.log("File not found: {}".format(path))
                        except Exception as e:
                            ctx.results.append({"request": request_item, "result": "Error: {}".format(e)})
                            self.log("Error: {}".format(e))

                    # list files
                    elif item["cmd"] == "list_dir" and self.is_cmd_allowed("list_dir"):
                        try:
                            msg = "Listing directory: {}".format(item["params"]['path'])
                            self.log(msg)
                            path = os.path.join(self.window.config.path, 'output', item["params"]['path'])
                            if os.path.exists(path):
                                files = os.listdir(path)
                                ctx.results.append({"request": request_item, "result": files})
                                self.log("Files listed: {}".format(path))
                                self.log("Result: {}".format(files))
                            else:
                                ctx.results.append({"request": request_item, "result": "Directory not found"})
                                self.log("Directory not found: {}".format(path))
                        except Exception as e:
                            ctx.results.append({"request": request_item, "result": "Error: {}".format(e)})
                            self.log("Error: {}".format(e))

                    # mkdir
                    elif item["cmd"] == "mkdir" and self.is_cmd_allowed("mkdir"):
                        try:
                            msg = "Creating directory: {}".format(item["params"]['path'])
                            self.log(msg)
                            path = os.path.join(self.window.config.path, 'output', item["params"]['path'])
                            if not os.path.exists(path):
                                os.makedirs(path)
                                ctx.results.append({"request": request_item, "result": "OK"})
                                self.log("Directory created: {}".format(path))
                            else:
                                ctx.results.append({"request": request_item, "result": "Directory already exists"})
                                self.log("Directory already exists: {}".format(path))
                        except Exception as e:
                            ctx.results.append({"request": request_item, "result": "Error: {}".format(e)})
                            self.log("Error: {}".format(e))

                    # rmdir
                    elif item["cmd"] == "rmdir" and self.is_cmd_allowed("rmdir"):
                        try:
                            msg = "Deleting directory: {}".format(item["params"]['path'])
                            self.log(msg)
                            path = os.path.join(self.window.config.path, 'output', item["params"]['path'])
                            if os.path.exists(path):
                                shutil.rmtree(path)
                                ctx.results.append({"request": request_item, "result": "OK"})
                                self.log("Directory deleted: {}".format(path))
                            else:
                                ctx.results.append({"request": request_item, "result": "Directory not found"})
                                self.log("Directory not found: {}".format(path))
                        except Exception as e:
                            ctx.results.append({"request": request_item, "result": "Error: {}".format(e)})
                            self.log("Error: {}".format(e))

                    # download
                    elif item["cmd"] == "download_file" and self.is_cmd_allowed("download_file"):
                        try:
                            dst = os.path.join(self.window.config.path, 'output', item["params"]['dst'])
                            msg = "Downloading file: {} into {}".format(item["params"]['src'], dst)
                            self.log(msg)

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
                            self.log("File downloaded: {} into {}".format(src, dst))
                        except Exception as e:
                            ctx.results.append({"request": request_item, "result": "Error: {}".format(e)})
                            self.log("Error: {}".format(e))

                    # copy file
                    elif item["cmd"] == "copy_file" and self.is_cmd_allowed("copy_file"):
                        try:
                            msg = "Copying file: {} into {}".format(item["params"]['src'], item["params"]['dst'])
                            self.log(msg)
                            dst = os.path.join(self.window.config.path, 'output', item["params"]['dst'])
                            src = os.path.join(self.window.config.path, 'output', item["params"]['src'])
                            shutil.copyfile(src, dst)
                            ctx.results.append({"request": request_item, "result": "OK"})
                            self.log("File copied: {} into {}".format(src, dst))
                        except Exception as e:
                            ctx.results.append({"request": request_item, "result": "Error: {}".format(e)})
                            self.log("Error: {}".format(e))

                    # copy dir
                    elif item["cmd"] == "copy_dir" and self.is_cmd_allowed("copy_dir"):
                        try:
                            msg = "Copying directory: {} into {}".format(item["params"]['src'], item["params"]['dst'])
                            self.log( msg)
                            dst = os.path.join(self.window.config.path, 'output', item["params"]['dst'])
                            src = os.path.join(self.window.config.path, 'output', item["params"]['src'])
                            shutil.copytree(src, dst)
                            ctx.results.append({"request": request_item, "result": "OK"})
                            self.log("Directory copied: {} into {}".format(src, dst))
                        except Exception as e:
                            ctx.results.append({"request": request_item, "result": "Error {}".format(e)})
                            self.log("Error: {}".format(e))

                    # move
                    elif item["cmd"] == "move" and self.is_cmd_allowed("move"):
                        try:
                            msg = "Moving: {} into {}".format(item["params"]['src'], item["params"]['dst'])
                            self.log(msg)
                            dst = os.path.join(self.window.config.path, 'output', item["params"]['dst'])
                            src = os.path.join(self.window.config.path, 'output', item["params"]['src'])
                            shutil.move(src, dst)
                            ctx.results.append({"request": request_item, "result": "OK"})
                            self.log("Moved: {} into {}".format(src, dst))
                        except Exception as e:
                            ctx.results.append({"request": request_item, "result": "Error: {}".format(e)})
                            self.log("Error: {}".format(e))

                    # is dir
                    elif item["cmd"] == "is_dir" and self.is_cmd_allowed("is_dir"):
                        try:
                            msg = "Checking if directory exists: {}".format(item["params"]['path'])
                            self.log(msg)
                            path = os.path.join(self.window.config.path, 'output', item["params"]['path'])
                            if os.path.isdir(path):
                                ctx.results.append({"request": request_item, "result": "OK"})
                                self.log("Directory exists: {}".format(path))
                            else:
                                ctx.results.append({"request": request_item, "result": "Directory not found"})
                                self.log("Directory not found: {}".format(path))
                        except Exception as e:
                            ctx.results.append({"request": request_item, "result": "Error: {}".format(e)})
                            self.log("Error: {}".format(e))

                    # is file
                    elif item["cmd"] == "is_file" and self.is_cmd_allowed("is_file"):
                        try:
                            msg = "Checking if file exists: {}".format(item["params"]['path'])
                            self.log(msg)
                            path = os.path.join(self.window.config.path, 'output', item["params"]['path'])
                            if os.path.isfile(path):
                                ctx.results.append({"request": request_item, "result": "OK"})
                                self.log("File exists: {}".format(path))
                            else:
                                ctx.results.append({"request": request_item, "result": "File not found"})
                                self.log("File not found: {}".format(path))
                        except Exception as e:
                            ctx.results.append({"request": request_item, "result": "Error: {}".format(e)})
                            self.log("Error: {}".format(e))

                    # file exists
                    elif item["cmd"] == "file_exists" and self.is_cmd_allowed("file_exists"):
                        try:
                            msg = "Checking if path exists: {}".format(item["params"]['path'])
                            self.log(msg)
                            path = os.path.join(self.window.config.path, 'output', item["params"]['path'])
                            if os.path.exists(path):
                                ctx.results.append({"request": request_item, "result": "OK"})
                                self.log("Path exists: {}".format(path))
                            else:
                                ctx.results.append({"request": request_item, "result": "File or directory not found"})
                                self.log("Path not found: {}".format(path))
                        except Exception as e:
                            ctx.results.append({"request": request_item, "result": "Error: {}".format(e)})
                            self.log("Error: {}".format(e))

                    # file size
                    elif item["cmd"] == "file_size" and self.is_cmd_allowed("file_size"):
                        try:
                            msg = "Checking file size: {}".format(item["params"]['path'])
                            self.log(msg)
                            path = os.path.join(self.window.config.path, 'output', item["params"]['path'])
                            if os.path.exists(path):
                                ctx.results.append({"request": request_item, "result": os.path.getsize(path)})
                                self.log("File size: {}".format(os.path.getsize(path)))
                            else:
                                ctx.results.append({"request": request_item, "result": "File not found"})
                                self.log("File not found: {}".format(path))
                        except Exception as e:
                            ctx.results.append({"request": request_item, "result": "Error: {}".format(e)})
                            self.log("Error: {}".format(e))

                    # file info
                    elif item["cmd"] == "file_info" and self.is_cmd_allowed("file_info"):
                        try:
                            msg = "Checking file info: {}".format(item["params"]['path'])
                            self.log(msg)
                            path = os.path.join(self.window.config.path, 'output', item["params"]['path'])
                            if os.path.exists(path):
                                data = {
                                    "size": os.path.getsize(path),
                                    'mime_type': mimetypes.guess_type(path)[0] or 'application/octet-stream',
                                    "last_access": os.path.getatime(path),
                                    "last_modification": os.path.getmtime(path),
                                    "creation_time": os.path.getctime(path),
                                    "is_dir": os.path.isdir(path),
                                    "is_file": os.path.isfile(path),
                                    "is_link": os.path.islink(path),
                                    "is_mount": os.path.ismount(path),
                                    'stat': os.stat(path),
                                }
                                ctx.results.append({"request": request_item, "result": data})
                                self.log("File info: {}".format(data))
                            else:
                                ctx.results.append({"request": request_item, "result": "File not found"})
                                self.log("File not found: {}".format(path))
                        except Exception as e:
                            ctx.results.append({"request": request_item, "result": "Error: {}".format(e)})
                            self.log("Error: {}".format(e))
            except Exception as e:
                ctx.results.append({"request": item, "result": "Error: {}".format(e)})
                ctx.reply = True
                self.log("Error: {}".format(e))

        if msg is not None:
            self.window.statusChanged.emit(msg)
        return ctx

