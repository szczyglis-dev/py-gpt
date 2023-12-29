#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.28 03:00:00                  #
# ================================================== #

import mimetypes
import os.path
import shutil
import ssl
from urllib.request import Request, urlopen
from PySide6.QtCore import QRunnable, Slot, QObject, Signal


class WorkerSignals(QObject):
    finished = Signal(object, object)  # ctx, response
    log = Signal(object)
    debug = Signal(object)
    status = Signal(object)
    error = Signal(object)


class Worker(QRunnable):
    def __init__(self, *args, **kwargs):
        super(Worker, self).__init__()
        self.signals = WorkerSignals()
        self.args = args
        self.kwargs = kwargs
        self.plugin = None
        self.cmds = None
        self.ctx = None

    @Slot()
    def run(self):
        msg = None
        for item in self.cmds:
            try:
                if item["cmd"] in self.plugin.allowed_cmds and self.plugin.is_cmd_allowed(item["cmd"]):

                    # prepare request item for result
                    request_item = {"cmd": item["cmd"]}

                    # save file
                    if item["cmd"] == "save_file":
                        try:
                            msg = "Saving file: {}".format(item["params"]['filename'])
                            self.signals.log.emit(msg)
                            path = os.path.join(self.plugin.window.core.config.path, 'output', item["params"]['filename'])
                            data = item["params"]['data']
                            with open(path, 'w', encoding="utf-8") as file:
                                file.write(data)
                                file.close()
                                response = {"request": request_item, "result": "OK"}
                                self.signals.log.emit("File saved: {}".format(path))
                        except Exception as e:
                            response = {"request": request_item, "result": "Error: {}".format(e)}
                            self.signals.error.emit(e)
                            self.signals.log.emit("Error: {}".format(e))
                        self.signals.finished.emit(self.ctx, response)

                    # append to file
                    elif item["cmd"] == "append_file" and self.plugin.is_cmd_allowed("append_file"):
                        try:
                            msg = "Appending file: {}".format(item["params"]['filename'])
                            self.signals.log.emit(msg)
                            path = os.path.join(self.plugin.window.core.config.path, 'output', item["params"]['filename'])
                            data = item["params"]['data']
                            with open(path, 'a', encoding="utf-8") as file:
                                file.write(data)
                                file.close()
                                response = {"request": request_item, "result": "OK"}
                                self.signals.log.emit("File appended: {}".format(path))
                        except Exception as e:
                            response = {"request": request_item, "result": "Error: {}".format(e)}
                            self.signals.error.emit(e)
                            self.signals.log.emit("Error: {}".format(e))
                        self.signals.finished.emit(self.ctx, response)

                    # read file
                    elif item["cmd"] == "read_file" and self.plugin.is_cmd_allowed("read_file"):
                        try:
                            msg = "Reading file: {}".format(item["params"]['filename'])
                            self.signals.log.emit(msg)
                            path = os.path.join(self.plugin.window.core.config.path, 'output', item["params"]['filename'])
                            if os.path.exists(path):
                                with open(path, 'r', encoding="utf-8") as file:
                                    data = file.read()
                                    response = {"request": request_item, "result": data}
                                    file.close()
                                    self.signals.log.emit("File read: {}".format(path))
                            else:
                                response = {"request": request_item, "result": "File not found"}
                                self.signals.log.emit("File not found: {}".format(path))
                        except Exception as e:
                            response = {"request": request_item, "result": "Error: {}".format(e)}
                            self.signals.error.emit(e)
                            self.signals.log.emit("Error: {}".format(e))
                        self.signals.finished.emit(self.ctx, response)

                    # delete file
                    elif item["cmd"] == "delete_file" and self.plugin.is_cmd_allowed("delete_file"):
                        try:
                            msg = "Deleting file: {}".format(item["params"]['filename'])
                            self.signals.log.emit(msg)
                            path = os.path.join(self.plugin.window.core.config.path, 'output', item["params"]['filename'])
                            if os.path.exists(path):
                                os.remove(path)
                                response = {"request": request_item, "result": "OK"}
                                self.signals.log.emit("File deleted: {}".format(path))
                            else:
                                response = {"request": request_item, "result": "File not found"}
                                self.signals.log.emit("File not found: {}".format(path))
                        except Exception as e:
                            response = {"request": request_item, "result": "Error: {}".format(e)}
                            self.signals.error.emit(e)
                            self.signals.log.emit("Error: {}".format(e))
                        self.signals.finished.emit(self.ctx, response)

                    # list files
                    elif item["cmd"] == "list_dir" and self.plugin.is_cmd_allowed("list_dir"):
                        try:
                            msg = "Listing directory: {}".format(item["params"]['path'])
                            self.signals.log.emit(msg)
                            path = os.path.join(self.plugin.window.core.config.path, 'output', item["params"]['path'])
                            if os.path.exists(path):
                                files = os.listdir(path)
                                response = {"request": request_item, "result": files}
                                self.signals.log.emit("Files listed: {}".format(path))
                                self.signals.log.emit("Result: {}".format(files))
                            else:
                                response = {"request": request_item, "result": "Directory not found"}
                                self.signals.log.emit("Directory not found: {}".format(path))
                        except Exception as e:
                            response = {"request": request_item, "result": "Error: {}".format(e)}
                            self.signals.error.emit(e)
                            self.signals.log.emit("Error: {}".format(e))
                        self.signals.finished.emit(self.ctx, response)

                    # mkdir
                    elif item["cmd"] == "mkdir" and self.plugin.is_cmd_allowed("mkdir"):
                        try:
                            msg = "Creating directory: {}".format(item["params"]['path'])
                            self.signals.log.emit(msg)
                            path = os.path.join(self.plugin.window.core.config.path, 'output', item["params"]['path'])
                            if not os.path.exists(path):
                                os.makedirs(path)
                                response = {"request": request_item, "result": "OK"}
                                self.signals.log.emit("Directory created: {}".format(path))
                            else:
                                response = {"request": request_item, "result": "Directory already exists"}
                                self.signals.log.emit("Directory already exists: {}".format(path))
                        except Exception as e:
                            response = {"request": request_item, "result": "Error: {}".format(e)}
                            self.signals.error.emit(e)
                            self.signals.log.emit("Error: {}".format(e))
                        self.signals.finished.emit(self.ctx, response)

                    # rmdir
                    elif item["cmd"] == "rmdir" and self.plugin.is_cmd_allowed("rmdir"):
                        try:
                            msg = "Deleting directory: {}".format(item["params"]['path'])
                            self.signals.log.emit(msg)
                            path = os.path.join(self.plugin.window.core.config.path, 'output', item["params"]['path'])
                            if os.path.exists(path):
                                shutil.rmtree(path)
                                response = {"request": request_item, "result": "OK"}
                                self.signals.log.emit("Directory deleted: {}".format(path))
                            else:
                                response = {"request": request_item, "result": "Directory not found"}
                                self.signals.log.emit("Directory not found: {}".format(path))
                        except Exception as e:
                            response = {"request": request_item, "result": "Error: {}".format(e)}
                            self.signals.error.emit(e)
                            self.signals.log.emit("Error: {}".format(e))
                        self.signals.finished.emit(self.ctx, response)

                    # download
                    elif item["cmd"] == "download_file" and self.plugin.is_cmd_allowed("download_file"):
                        try:
                            dst = os.path.join(self.plugin.window.core.config.path, 'output', item["params"]['dst'])
                            msg = "Downloading file: {} into {}".format(item["params"]['src'], dst)
                            self.signals.log.emit(msg)

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
                                src = os.path.join(self.plugin.window.core.config.path, 'output', item["params"]['src'])

                                # Copy local file
                                with open(src, 'rb') as in_file, open(dst, 'wb') as out_file:
                                    shutil.copyfileobj(in_file, out_file)

                            # handle result
                            response = {"request": request_item, "result": "OK"}
                            self.signals.log.emit("File downloaded: {} into {}".format(src, dst))
                        except Exception as e:
                            response = {"request": request_item, "result": "Error: {}".format(e)}
                            self.signals.error.emit(e)
                            self.signals.log.emit("Error: {}".format(e))
                        self.signals.finished.emit(self.ctx, response)

                    # copy file
                    elif item["cmd"] == "copy_file" and self.plugin.is_cmd_allowed("copy_file"):
                        try:
                            msg = "Copying file: {} into {}".format(item["params"]['src'], item["params"]['dst'])
                            self.signals.log.emit(msg)
                            dst = os.path.join(self.plugin.window.core.config.path, 'output', item["params"]['dst'])
                            src = os.path.join(self.plugin.window.core.config.path, 'output', item["params"]['src'])
                            shutil.copyfile(src, dst)
                            response = {"request": request_item, "result": "OK"}
                            self.signals.log.emit("File copied: {} into {}".format(src, dst))
                        except Exception as e:
                            response = {"request": request_item, "result": "Error: {}".format(e)}
                            self.signals.error.emit(e)
                            self.signals.log.emit("Error: {}".format(e))
                        self.signals.finished.emit(self.ctx, response)

                    # copy dir
                    elif item["cmd"] == "copy_dir" and self.plugin.is_cmd_allowed("copy_dir"):
                        try:
                            msg = "Copying directory: {} into {}".format(item["params"]['src'], item["params"]['dst'])
                            self.signals.log.emit(msg)
                            dst = os.path.join(self.plugin.window.core.config.path, 'output', item["params"]['dst'])
                            src = os.path.join(self.plugin.window.core.config.path, 'output', item["params"]['src'])
                            shutil.copytree(src, dst)
                            response = {"request": request_item, "result": "OK"}
                            self.signals.log.emit("Directory copied: {} into {}".format(src, dst))
                        except Exception as e:
                            response = {"request": request_item, "result": "Error {}".format(e)}
                            self.signals.error.emit(e)
                            self.signals.log.emit("Error: {}".format(e))
                        self.signals.finished.emit(self.ctx, response)

                    # move
                    elif item["cmd"] == "move" and self.plugin.is_cmd_allowed("move"):
                        try:
                            msg = "Moving: {} into {}".format(item["params"]['src'], item["params"]['dst'])
                            self.signals.log.emit(msg)
                            dst = os.path.join(self.plugin.window.core.config.path, 'output', item["params"]['dst'])
                            src = os.path.join(self.plugin.window.core.config.path, 'output', item["params"]['src'])
                            shutil.move(src, dst)
                            response = {"request": request_item, "result": "OK"}
                            self.signals.log.emit("Moved: {} into {}".format(src, dst))
                        except Exception as e:
                            response = {"request": request_item, "result": "Error: {}".format(e)}
                            self.signals.error.emit(e)
                            self.signals.log.emit("Error: {}".format(e))
                        self.signals.finished.emit(self.ctx, response)

                    # is dir
                    elif item["cmd"] == "is_dir" and self.plugin.is_cmd_allowed("is_dir"):
                        try:
                            msg = "Checking if directory exists: {}".format(item["params"]['path'])
                            self.signals.log.emit(msg)
                            path = os.path.join(self.plugin.window.core.config.path, 'output', item["params"]['path'])
                            if os.path.isdir(path):
                                response = {"request": request_item, "result": "OK"}
                                self.signals.log.emit("Directory exists: {}".format(path))
                            else:
                                response = {"request": request_item, "result": "Directory not found"}
                                self.signals.log.emit("Directory not found: {}".format(path))
                        except Exception as e:
                            response = {"request": request_item, "result": "Error: {}".format(e)}
                            self.signals.error.emit(e)
                            self.signals.log.emit("Error: {}".format(e))
                        self.signals.finished.emit(self.ctx, response)

                    # is file
                    elif item["cmd"] == "is_file" and self.plugin.is_cmd_allowed("is_file"):
                        try:
                            msg = "Checking if file exists: {}".format(item["params"]['path'])
                            self.signals.log.emit(msg)
                            path = os.path.join(self.plugin.window.core.config.path, 'output', item["params"]['path'])
                            if os.path.isfile(path):
                                response = {"request": request_item, "result": "OK"}
                                self.signals.log.emit("File exists: {}".format(path))
                            else:
                                response = {"request": request_item, "result": "File not found"}
                                self.signals.log.emit("File not found: {}".format(path))
                        except Exception as e:
                            response = {"request": request_item, "result": "Error: {}".format(e)}
                            self.signals.error.emit(e)
                            self.signals.log.emit("Error: {}".format(e))
                        self.signals.finished.emit(self.ctx, response)

                    # file exists
                    elif item["cmd"] == "file_exists" and self.plugin.is_cmd_allowed("file_exists"):
                        try:
                            msg = "Checking if path exists: {}".format(item["params"]['path'])
                            self.signals.log.emit(msg)
                            path = os.path.join(self.plugin.window.core.config.path, 'output', item["params"]['path'])
                            if os.path.exists(path):
                                response = {"request": request_item, "result": "OK"}
                                self.signals.log.emit("Path exists: {}".format(path))
                            else:
                                response = {"request": request_item, "result": "File or directory not found"}
                                self.signals.log.emit("Path not found: {}".format(path))
                        except Exception as e:
                            response = {"request": request_item, "result": "Error: {}".format(e)}
                            self.signals.error.emit(e)
                            self.signals.log.emit("Error: {}".format(e))
                        self.signals.finished.emit(self.ctx, response)

                    # file size
                    elif item["cmd"] == "file_size" and self.plugin.is_cmd_allowed("file_size"):
                        try:
                            msg = "Checking file size: {}".format(item["params"]['path'])
                            self.signals.log.emit(msg)
                            path = os.path.join(self.plugin.window.core.config.path, 'output', item["params"]['path'])
                            if os.path.exists(path):
                                response = {"request": request_item, "result": os.path.getsize(path)}
                                self.signals.log.emit("File size: {}".format(os.path.getsize(path)))
                            else:
                                response = {"request": request_item, "result": "File not found"}
                                self.signals.log.emit("File not found: {}".format(path))
                        except Exception as e:
                            response = {"request": request_item, "result": "Error: {}".format(e)}
                            self.signals.error.emit(e)
                            self.signals.log.emit("Error: {}".format(e))
                        self.signals.finished.emit(self.ctx, response)

                    # file info
                    elif item["cmd"] == "file_info" and self.plugin.is_cmd_allowed("file_info"):
                        try:
                            msg = "Checking file info: {}".format(item["params"]['path'])
                            self.signals.log.emit(msg)
                            path = os.path.join(self.plugin.window.core.config.path, 'output', item["params"]['path'])
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
                                response = {"request": request_item, "result": data}
                                self.signals.log.emit("File info: {}".format(data))
                            else:
                                response = {"request": request_item, "result": "File not found"}
                                self.signals.log.emit("File not found: {}".format(path))
                        except Exception as e:
                            response = {"request": request_item, "result": "Error: {}".format(e)}
                            self.signals.error.emit(e)
                            self.signals.log.emit("Error: {}".format(e))
                        self.signals.finished.emit(self.ctx, response)
            except Exception as e:
                response = {"request": item, "result": "Error: {}".format(e)}
                self.signals.finished.emit(self.ctx, response)
                self.signals.error.emit(e)
                self.signals.log.emit("Error: {}".format(e))

        if msg is not None:
            self.signals.log.emit(msg)
            self.signals.status.emit(msg)

    def finish(self, ctx, response):
        self.signals.finished.emit(ctx, response)

    def error(self, err):
        self.signals.error.emit(err)

    def status(self, msg):
        self.signals.status.emit(msg)

    def debug(self, msg):
        self.signals.debug.emit(msg)

    def log(self, msg):
        self.signals.log.emit(msg)
