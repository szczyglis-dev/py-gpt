#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.16 16:00:00                  #
# ================================================== #

import mimetypes
import os.path
import shutil
import ssl
from urllib.request import Request, urlopen
from PySide6.QtCore import Slot

from pygpt_net.plugin.base import BaseWorker, BaseSignals


class WorkerSignals(BaseSignals):
    pass  # add custom signals here


class Worker(BaseWorker):
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
                if item["cmd"] in self.plugin.allowed_cmds \
                        and self.plugin.is_cmd_allowed(item["cmd"]):
                    request = {"cmd": item["cmd"]}  # prepare request item for result

                    # save file
                    if item["cmd"] == "save_file":
                        try:
                            msg = "Saving file: {}".format(item["params"]['filename'])
                            self.log(msg)
                            path = os.path.join(
                                self.plugin.window.core.config.get_user_dir('data'),
                                item["params"]['filename'],
                            )
                            data = item["params"]['data']
                            with open(path, 'w', encoding="utf-8") as file:
                                file.write(data)
                                response = {
                                    "request": request,
                                    "result": "OK",
                                }
                                self.log("File saved: {}".format(path))
                        except Exception as e:
                            response = {
                                "request": request,
                                "result": "Error: {}".format(e),
                            }
                            self.error(e)
                            self.log("Error: {}".format(e))
                        self.response(response)

                    # append to file
                    elif item["cmd"] == "append_file" and self.plugin.is_cmd_allowed("append_file"):
                        try:
                            msg = "Appending file: {}".format(item["params"]['filename'])
                            self.log(msg)
                            path = os.path.join(
                                self.plugin.window.core.config.get_user_dir('data'),
                                item["params"]['filename'],
                            )
                            data = item["params"]['data']
                            with open(path, 'a', encoding="utf-8") as file:
                                file.write(data)
                                response = {
                                    "request": request,
                                    "result": "OK",
                                }
                                self.log("File appended: {}".format(path))
                        except Exception as e:
                            response = {
                                "request": request,
                                "result": "Error: {}".format(e),
                            }
                            self.error(e)
                            self.log("Error: {}".format(e))
                        self.response(response)

                    # read file
                    elif item["cmd"] == "read_file" and self.plugin.is_cmd_allowed("read_file"):
                        try:
                            msg = "Reading file: {}".format(item["params"]['filename'])
                            self.log(msg)
                            path = os.path.join(
                                self.plugin.window.core.config.get_user_dir('data'),
                                item["params"]['filename'],
                            )
                            if os.path.exists(path):
                                with open(path, 'r', encoding="utf-8") as file:
                                    data = file.read()
                                    response = {
                                        "request": request,
                                        "result": data,
                                    }
                                    self.log("File read: {}".format(path))
                            else:
                                response = {
                                    "request": request,
                                    "result": "File not found",
                                }
                                self.log("File not found: {}".format(path))
                        except Exception as e:
                            response = {
                                "request": request,
                                "result": "Error: {}".format(e),
                            }
                            self.error(e)
                            self.log("Error: {}".format(e))
                        self.response(response)

                    # delete file
                    elif item["cmd"] == "delete_file" and self.plugin.is_cmd_allowed("delete_file"):
                        try:
                            msg = "Deleting file: {}".format(item["params"]['filename'])
                            self.log(msg)
                            path = os.path.join(
                                self.plugin.window.core.config.get_user_dir('data'),
                                item["params"]['filename'],
                            )
                            if os.path.exists(path):
                                os.remove(path)
                                response = {"request": request, "result": "OK"}
                                self.log("File deleted: {}".format(path))
                            else:
                                response = {
                                    "request": request,
                                    "result": "File not found",
                                }
                                self.log("File not found: {}".format(path))
                        except Exception as e:
                            response = {
                                "request": request,
                                "result": "Error: {}".format(e),
                            }
                            self.error(e)
                            self.log("Error: {}".format(e))
                        self.response(response)

                    # list files
                    elif item["cmd"] == "list_dir" and self.plugin.is_cmd_allowed("list_dir"):
                        try:
                            msg = "Listing directory: {}".format(item["params"]['path'])
                            self.log(msg)
                            path = os.path.join(
                                self.plugin.window.core.config.get_user_dir('data'),
                                item["params"]['path'],
                            )
                            if os.path.exists(path):
                                files = os.listdir(path)
                                response = {
                                    "request": request,
                                    "result": files,
                                }
                                self.log("Files listed: {}".format(path))
                                self.log("Result: {}".format(files))
                            else:
                                response = {
                                    "request": request,
                                    "result": "Directory not found",
                                }
                                self.log("Directory not found: {}".format(path))
                        except Exception as e:
                            response = {
                                "request": request,
                                "result": "Error: {}".format(e),
                            }
                            self.error(e)
                            self.log("Error: {}".format(e))
                        self.response(response)

                    # mkdir
                    elif item["cmd"] == "mkdir" and self.plugin.is_cmd_allowed("mkdir"):
                        try:
                            msg = "Creating directory: {}".format(item["params"]['path'])
                            self.log(msg)
                            path = os.path.join(
                                self.plugin.window.core.config.get_user_dir('data'),
                                item["params"]['path'],
                            )
                            if not os.path.exists(path):
                                os.makedirs(path)
                                response = {
                                    "request": request,
                                    "result": "OK",
                                }
                                self.log("Directory created: {}".format(path))
                            else:
                                response = {
                                    "request": request,
                                    "result": "Directory already exists",
                                }
                                self.log("Directory already exists: {}".format(path))
                        except Exception as e:
                            response = {
                                "request": request,
                                "result": "Error: {}".format(e),
                            }
                            self.error(e)
                            self.log("Error: {}".format(e))
                        self.response(response)

                    # rmdir
                    elif item["cmd"] == "rmdir" and self.plugin.is_cmd_allowed("rmdir"):
                        try:
                            msg = "Deleting directory: {}".format(item["params"]['path'])
                            self.log(msg)
                            path = os.path.join(
                                self.plugin.window.core.config.get_user_dir('data'),
                                item["params"]['path'],
                            )
                            if os.path.exists(path):
                                shutil.rmtree(path)
                                response = {
                                    "request": request,
                                    "result": "OK",
                                }
                                self.log("Directory deleted: {}".format(path))
                            else:
                                response = {
                                    "request": request,
                                    "result": "Directory not found",
                                }
                                self.log("Directory not found: {}".format(path))
                        except Exception as e:
                            response = {
                                "request": request,
                                "result": "Error: {}".format(e),
                            }
                            self.error(e)
                            self.log("Error: {}".format(e))
                        self.response(response)

                    # download
                    elif item["cmd"] == "download_file" and self.plugin.is_cmd_allowed("download_file"):
                        try:
                            dst = os.path.join(
                                self.plugin.window.core.config.get_user_dir('data'),
                                item["params"]['dst'],
                            )
                            msg = "Downloading file: {} into {}".format(item["params"]['src'], dst)
                            self.log(msg)

                            # Check if src is URL
                            if item["params"]['src'].startswith("http"):
                                src = item["params"]['src']
                                # Download file from URL
                                req = Request(
                                    url=src,
                                    headers={'User-Agent': 'Mozilla/5.0'},
                                )
                                context = ssl.create_default_context()
                                context.check_hostname = False
                                context.verify_mode = ssl.CERT_NONE
                                with urlopen(
                                        req,
                                        context=context,
                                        timeout=5) as response, \
                                        open(dst, 'wb') as out_file:
                                    shutil.copyfileobj(response, out_file)
                            else:
                                # Handle local file paths
                                src = os.path.join(
                                    self.plugin.window.core.config.get_user_dir('data'),
                                    item["params"]['src'],
                                )

                                # Copy local file
                                with open(src, 'rb') as in_file, open(dst, 'wb') as out_file:
                                    shutil.copyfileobj(in_file, out_file)

                            # handle result
                            response = {
                                "request": request,
                                "result": "OK",
                            }
                            self.log("File downloaded: {} into {}".format(src, dst))
                        except Exception as e:
                            response = {
                                "request": request,
                                "result": "Error: {}".format(e),
                            }
                            self.error(e)
                            self.log("Error: {}".format(e))
                        self.response(response)

                    # copy file
                    elif item["cmd"] == "copy_file" and self.plugin.is_cmd_allowed("copy_file"):
                        try:
                            msg = "Copying file: {} into {}".format(item["params"]['src'], item["params"]['dst'])
                            self.log(msg)
                            dst = os.path.join(
                                self.plugin.window.core.config.get_user_dir('data'),
                                item["params"]['dst'],
                            )
                            src = os.path.join(
                                self.plugin.window.core.config.get_user_dir('data'),
                                item["params"]['src'],
                            )
                            shutil.copyfile(src, dst)
                            response = {
                                "request": request,
                                "result": "OK",
                            }
                            self.log("File copied: {} into {}".format(src, dst))
                        except Exception as e:
                            response = {
                                "request": request,
                                "result": "Error: {}".format(e),
                            }
                            self.error(e)
                            self.log("Error: {}".format(e))
                        self.response(response)

                    # copy dir
                    elif item["cmd"] == "copy_dir" and self.plugin.is_cmd_allowed("copy_dir"):
                        try:
                            msg = "Copying directory: {} into {}".format(item["params"]['src'],
                                                                         item["params"]['dst'])
                            self.log(msg)
                            dst = os.path.join(
                                self.plugin.window.core.config.get_user_dir('data'),
                                item["params"]['dst'],
                            )
                            src = os.path.join(
                                self.plugin.window.core.config.get_user_dir('data'),
                                item["params"]['src'],
                            )
                            shutil.copytree(src, dst)
                            response = {
                                "request": request,
                                "result": "OK",
                            }
                            self.log("Directory copied: {} into {}".format(src, dst))
                        except Exception as e:
                            response = {
                                "request": request,
                                "result": "Error {}".format(e),
                            }
                            self.error(e)
                            self.log("Error: {}".format(e))
                        self.response(response)

                    # move
                    elif item["cmd"] == "move" and self.plugin.is_cmd_allowed("move"):
                        try:
                            msg = "Moving: {} into {}".format(item["params"]['src'], item["params"]['dst'])
                            self.log(msg)
                            dst = os.path.join(
                                self.plugin.window.core.config.get_user_dir('data'),
                                item["params"]['dst'],
                            )
                            src = os.path.join(
                                self.plugin.window.core.config.get_user_dir('data'),
                                item["params"]['src'],
                            )
                            shutil.move(src, dst)
                            response = {
                                "request": request,
                                "result": "OK",
                            }
                            self.log("Moved: {} into {}".format(src, dst))
                        except Exception as e:
                            response = {
                                "request": request,
                                "result": "Error: {}".format(e),
                            }
                            self.error(e)
                            self.log("Error: {}".format(e))
                        self.response(response)

                    # is dir
                    elif item["cmd"] == "is_dir" and self.plugin.is_cmd_allowed("is_dir"):
                        try:
                            msg = "Checking if directory exists: {}".format(item["params"]['path'])
                            self.log(msg)
                            path = os.path.join(
                                self.plugin.window.core.config.get_user_dir('data'),
                                item["params"]['path'],
                            )
                            if os.path.isdir(path):
                                response = {
                                    "request": request,
                                    "result": "OK",
                                }
                                self.log("Directory exists: {}".format(path))
                            else:
                                response = {"request": request, "result": "Directory not found"}
                                self.log("Directory not found: {}".format(path))
                        except Exception as e:
                            response = {
                                "request": request,
                                "result": "Error: {}".format(e),
                            }
                            self.error(e)
                            self.log("Error: {}".format(e))
                        self.response(response)

                    # is file
                    elif item["cmd"] == "is_file" and self.plugin.is_cmd_allowed("is_file"):
                        try:
                            msg = "Checking if file exists: {}".format(item["params"]['path'])
                            self.log(msg)
                            path = os.path.join(
                                self.plugin.window.core.config.get_user_dir('data'),
                                item["params"]['path'],
                            )
                            if os.path.isfile(path):
                                response = {
                                    "request": request,
                                    "result": "OK",
                                }
                                self.log("File exists: {}".format(path))
                            else:
                                response = {
                                    "request": request,
                                    "result": "File not found",
                                }
                                self.log("File not found: {}".format(path))
                        except Exception as e:
                            response = {
                                "request": request,
                                "result": "Error: {}".format(e),
                            }
                            self.error(e)
                            self.log("Error: {}".format(e))
                        self.response(response)

                    # file exists
                    elif item["cmd"] == "file_exists" and self.plugin.is_cmd_allowed("file_exists"):
                        try:
                            msg = "Checking if path exists: {}".format(item["params"]['path'])
                            self.log(msg)
                            path = os.path.join(
                                self.plugin.window.core.config.get_user_dir('data'),
                                item["params"]['path'],
                            )
                            if os.path.exists(path):
                                response = {
                                    "request": request,
                                    "result": "OK",
                                }
                                self.log("Path exists: {}".format(path))
                            else:
                                response = {
                                    "request": request,
                                    "result": "File or directory not found",
                                }
                                self.log("Path not found: {}".format(path))
                        except Exception as e:
                            response = {
                                "request": request,
                                "result": "Error: {}".format(e),
                            }
                            self.error(e)
                            self.log("Error: {}".format(e))
                        self.response(response)

                    # file size
                    elif item["cmd"] == "file_size" and self.plugin.is_cmd_allowed("file_size"):
                        try:
                            msg = "Checking file size: {}".format(item["params"]['path'])
                            self.log(msg)
                            path = os.path.join(
                                self.plugin.window.core.config.get_user_dir('data'),
                                item["params"]['path'],
                            )
                            if os.path.exists(path):
                                response = {
                                    "request": request,
                                    "result": os.path.getsize(path),
                                }
                                self.log("File size: {}".format(os.path.getsize(path)))
                            else:
                                response = {
                                    "request": request,
                                    "result": "File not found",
                                }
                                self.log("File not found: {}".format(path))
                        except Exception as e:
                            response = {
                                "request": request,
                                "result": "Error: {}".format(e),
                            }
                            self.error(e)
                            self.log("Error: {}".format(e))
                        self.response(response)

                    # file info
                    elif item["cmd"] == "file_info" and self.plugin.is_cmd_allowed("file_info"):
                        try:
                            msg = "Checking file info: {}".format(item["params"]['path'])
                            self.log(msg)
                            path = os.path.join(
                                self.plugin.window.core.config.get_user_dir('data'),
                                item["params"]['path'],
                            )
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
                                response = {
                                    "request": request,
                                    "result": data,
                                }
                                self.log("File info: {}".format(data))
                            else:
                                response = {
                                    "request": request,
                                    "result": "File not found",
                                }
                                self.log("File not found: {}".format(path))
                        except Exception as e:
                            response = {
                                "request": request,
                                "result": "Error: {}".format(e),
                            }
                            self.error(e)
                            self.log("Error: {}".format(e))
                        self.response(response)

                    # cwd
                    elif item["cmd"] == "cwd" and self.plugin.is_cmd_allowed("cwd"):
                        try:
                            msg = "Getting CWD: {}".format(self.plugin.window.core.config.get_user_dir('data'))
                            self.log(msg)
                            response = {
                                "request": request,
                                "result": self.plugin.window.core.config.get_user_dir('data'),
                            }
                        except Exception as e:
                            response = {
                                "request": request,
                                "result": "Error: {}".format(e),
                            }
                            self.error(e)
                            self.log("Error: {}".format(e))
                        self.response(response)

                    # get file as attachment
                    elif item["cmd"] == "send_file" and self.plugin.is_cmd_allowed("send_file"):
                        try:
                            msg = "Adding attachment: {}".format(item["params"]['path'])
                            self.log(msg)
                            path = os.path.join(
                                self.plugin.window.core.config.get_user_dir('data'),
                                item["params"]['path'],
                            )

                            if os.path.exists(path):
                                # make attachment
                                mode = self.plugin.window.core.config.get('mode')
                                title = os.path.basename(path)
                                self.plugin.window.core.attachments.new(mode, title, path, False)
                                self.plugin.window.core.attachments.save()
                                self.plugin.window.controller.attachment.update()
                                response = {
                                    "request": request,
                                    "result": "Sending attachment: {}".format(title),
                                }
                                self.log("Added attachment: {}".format(path))
                            else:
                                response = {
                                    "request": request,
                                    "result": "File not found",
                                }
                                self.log("File not found: {}".format(path))
                        except Exception as e:
                            response = {
                                "request": request,
                                "result": "Error: {}".format(e),
                            }
                            self.error(e)
                            self.log("Error: {}".format(e))
                        self.response(response)

            except Exception as e:
                self.response(
                    {
                        "request": item,
                        "result": "Error: {}".format(e),
                    }
                )
                self.error(e)
                self.log("Error: {}".format(e))

        if msg is not None:
            self.status(msg)
