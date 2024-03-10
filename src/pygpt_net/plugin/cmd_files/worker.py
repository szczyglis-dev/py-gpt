#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.09 07:00:00                  #
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
        self.msg = None

    @Slot()
    def run(self):
        for item in self.cmds:
            try:
                if item["cmd"] in self.plugin.allowed_cmds and self.plugin.is_cmd_allowed(item["cmd"]):

                    # save file
                    if item["cmd"] == "save_file":
                        self.cmd_save_file(item)

                    # append to file
                    elif item["cmd"] == "append_file":
                        self.cmd_append_file(item)

                    # read file
                    elif item["cmd"] == "read_file":
                        self.cmd_read_file(item)

                    # query file
                    elif item["cmd"] == "query_file":
                        self.cmd_query_file(item)

                    # delete file
                    elif item["cmd"] == "delete_file":
                        self.cmd_delete_file(item)

                    # list files
                    elif item["cmd"] == "list_dir":
                        self.cmd_list_dir(item)

                    # mkdir
                    elif item["cmd"] == "mkdir":
                        self.cmd_mkdir(item)

                    # rmdir
                    elif item["cmd"] == "rmdir":
                        self.cmd_rmdir(item)

                    # download
                    elif item["cmd"] == "download_file":
                        self.cmd_download_file(item)

                    # copy file
                    elif item["cmd"] == "copy_file":
                        self.cmd_copy_file(item)

                    # copy dir
                    elif item["cmd"] == "copy_dir":
                        self.cmd_copy_dir(item)

                    # move
                    elif item["cmd"] == "move":
                        self.cmd_move(item)

                    # is dir
                    elif item["cmd"] == "is_dir":
                        self.cmd_is_dir(item)

                    # is file
                    elif item["cmd"] == "is_file":
                        self.cmd_is_file(item)

                    # file exists
                    elif item["cmd"] == "file_exists":
                        self.cmd_file_exists(item)

                    # file size
                    elif item["cmd"] == "file_size":
                        self.cmd_file_size(item)

                    # file info
                    elif item["cmd"] == "file_info":
                        self.cmd_file_info(item)

                    # cwd
                    elif item["cmd"] == "cwd":
                        self.cmd_cwd(item)

                    # get file as attachment
                    elif item["cmd"] == "send_file":
                        self.cmd_send_file(item)

                    # index file or directory
                    elif item["cmd"] == "file_index":
                        self.cmd_file_index(item)

            except Exception as e:
                self.response(
                    {
                        "request": item,
                        "result": "Error: {}".format(e),
                    },
                    self.get_extra_data(),
                )
                self.error(e)
                self.log("Error: {}".format(e))

        if self.msg is not None:
            self.status(self.msg)

    def prepare_request(self, item) -> dict:
        """
        Prepare request item for result

        :param item: item with parameters
        :return: request item
        """
        request = {"cmd": item["cmd"]}  # prepare request item for result
        return request

    def get_extra_data(self) -> dict:
        """
        Return extra data for response

        :return: extra data
        """
        return {
            "post_update": ["file_explorer"],  # update file explorer after processing
        }

    def cmd_save_file(self, item: dict):
        """
        Save file

        :param item: item with parameters
        """
        request = self.prepare_request(item)
        try:
            self.msg = "Saving file: {}".format(item["params"]['filename'])
            self.log(self.msg)
            path = self.prepare_path(item["params"]['filename'])
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
        self.response(response, self.get_extra_data())

    def cmd_append_file(self, item: dict):
        """
        Append to file

        :param item: item with parameters
        """
        request = self.prepare_request(item)
        try:
            self.msg = "Appending file: {}".format(item["params"]['filename'])
            self.log(self.msg)
            path = self.prepare_path(item["params"]['filename'])
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
        self.response(response, self.get_extra_data())

    def cmd_read_file(self, item: dict):
        """
        Read file

        :param item: item with parameters
        """
        request = self.prepare_request(item)
        try:
            self.msg = "Reading file: {}".format(item["params"]['filename'])
            self.log(self.msg)
            path = item["params"]['filename']
            paths = []
            if isinstance(path, list):
                paths = path
            elif isinstance(path, str):
                paths = [path]
            data, context = self.read_files(paths)
            context_str = None
            if context:
                context_str = "\n\n".join(context)
            response = {
                "request": request,
                "result": data,
            }
            if context_str:
                response["context"] = context_str
        except Exception as e:
            response = {
                "request": request,
                "result": "Error: {}".format(e),
            }
            self.error(e)
            self.log("Error: {}".format(e))
        self.response(response, self.get_extra_data())

    def cmd_query_file(self, item: dict):
        """
        Query file

        :param item: item with parameters
        """
        request = self.prepare_request(item)
        response = {}
        query = None
        try:
            self.msg = "Reading path: {}".format(item["params"]['path'])
            self.log(self.msg)
            path = self.prepare_path(item["params"]['path'])
            if "query" in item["params"] and item["params"]["query"]:
                query = item["params"]["query"]

            # check if file exists
            if os.path.exists(path):
                if query is not None:
                    # query file using temp index (created on the fly)
                    self.log("Querying file: {}".format(path))

                    # get tmp query model
                    model = self.plugin.window.core.models.from_defaults()
                    tmp_model = self.plugin.get_option_value("model_tmp_query")
                    if self.plugin.window.core.models.has(tmp_model):
                        model = self.plugin.window.core.models.get(tmp_model)

                    answer = self.plugin.window.core.idx.chat.query_file(
                        ctx=self.ctx,
                        path=path,
                        query=query,
                        model=model,
                    )
                    self.log("Response from temporary in-memory index: {}".format(answer))
                    if answer:
                        response = {
                            "request": request,
                            "result": answer,
                            "context": "From: " + os.path.basename(path) + ":\n--------------------------------\n" + answer,
                            # add additional context
                        }

                # + auto-index file to main index using Llama-index
                if self.plugin.get_option_value("auto_index"):
                    idx_name = self.plugin.get_option_value("idx")
                    self.plugin.window.core.idx.index_files(
                        idx_name,
                        path,
                    )
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
        self.response(response, self.get_extra_data())

    def cmd_delete_file(self,item: dict):
        """
        Delete file

        :param item: item with parameters
        """
        request = self.prepare_request(item)
        try:
            self.msg = "Deleting file: {}".format(item["params"]['filename'])
            self.log(self.msg)
            path = self.prepare_path(item["params"]['filename'])
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
        self.response(response, self.get_extra_data())

    def cmd_list_dir(self, item: dict):
        """
        List directory

        :param item: item with parameters
        """
        request = self.prepare_request(item)
        try:
            self.msg = "Listing directory: {}".format(item["params"]['path'])
            self.log(self.msg)
            path = self.prepare_path(item["params"]['path'])
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
        self.response(response, self.get_extra_data())

    def cmd_mkdir(self, item: dict):
        """
        Make directory

        :param item: item with parameters
        """
        request = self.prepare_request(item)
        try:
            self.msg = "Creating directory: {}".format(item["params"]['path'])
            self.log(self.msg)
            path = self.prepare_path(item["params"]['path'])
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
        self.response(response, self.get_extra_data())

    def cmd_rmdir(self, item: dict):
        """
        Remove directory

        :param item: item with parameters
        """
        request = self.prepare_request(item)
        try:
            self.msg = "Deleting directory: {}".format(item["params"]['path'])
            self.log(self.msg)
            path = self.prepare_path(item["params"]['path'])
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
        self.response(response, self.get_extra_data())

    def cmd_download_file(self, item: dict):
        """
        Download file

        :param item: item with parameters
        """
        request = self.prepare_request(item)
        try:
            dst = self.prepare_path(item["params"]['dst'])
            self.msg = "Downloading file: {} into {}".format(item["params"]['src'], dst)
            self.log(self.msg)
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

                size = os.path.getsize(dst)
            else:
                # Handle local file paths
                src = os.path.join(
                    self.plugin.window.core.config.get_user_dir('data'),
                    item["params"]['src'],
                )

                # Copy local file
                with open(src, 'rb') as in_file, open(dst, 'wb') as out_file:
                    shutil.copyfileobj(in_file, out_file)
                size = os.path.getsize(dst)

            # handle result
            response = {
                "request": request,
                "result": {
                    "result": "OK",
                    "size_bytes": size,
                    "size_human": self.get_human_readable_size(size),
                }
            }
            self.log("File downloaded: {} into {}".format(src, dst))
        except Exception as e:
            response = {
                "request": request,
                "result": "Error: {}".format(e),
            }
            self.error(e)
            self.log("Error: {}".format(e))
        self.response(response, self.get_extra_data())

    def cmd_copy_file(self, item: dict):
        """
        Copy file

        :param item: item with parameters
        """
        request = self.prepare_request(item)
        try:
            self.msg = "Copying file: {} into {}".format(item["params"]['src'], item["params"]['dst'])
            self.log(self.msg)
            dst = self.prepare_path(item["params"]['dst'])
            src = self.prepare_path(item["params"]['src'])
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
        self.response(response, self.get_extra_data())

    def cmd_copy_dir(self, item: dict):
        """
        Copy directory

        :param item: item with parameters
        """
        request = self.prepare_request(item)
        try:
            self.msg = "Copying directory: {} into {}".format(item["params"]['src'],
                                                              item["params"]['dst'])
            self.log(self.msg)
            dst = self.prepare_path(item["params"]['dst'])
            src = self.prepare_path(item["params"]['src'])
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
        self.response(response, self.get_extra_data())

    def cmd_move(self, item: dict):
        """
        Move file or directory

        :param item: item with parameters
        """
        request = self.prepare_request(item)
        try:
            self.msg = "Moving: {} into {}".format(item["params"]['src'], item["params"]['dst'])
            self.log(self.msg)
            dst = self.prepare_path(item["params"]['dst'])
            src = self.prepare_path(item["params"]['src'])
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
        self.response(response, self.get_extra_data())

    def cmd_is_dir(self, item: dict):
        """
        Check if directory exists

        :param item: item with parameters
        """
        request = self.prepare_request(item)
        try:
            self.msg = "Checking if directory exists: {}".format(item["params"]['path'])
            self.log(self.msg)
            path = self.prepare_path(item["params"]['path'])
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
        self.response(response, self.get_extra_data())

    def cmd_is_file(self, item: dict):
        """
        Check if file exists

        :param item: item with parameters
        """
        request = self.prepare_request(item)
        try:
            self.msg = "Checking if file exists: {}".format(item["params"]['path'])
            self.log(self.msg)
            path = self.prepare_path(item["params"]['path'])
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
        self.response(response, self.get_extra_data())

    def cmd_file_exists(self, item: dict):
        """
        Check if file exists

        :param item: item with parameters
        """
        request = self.prepare_request(item)
        try:
            self.msg = "Checking if path exists: {}".format(item["params"]['path'])
            self.log(self.msg)
            path = self.prepare_path(item["params"]['path'])
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
        self.response(response, self.get_extra_data())

    def cmd_file_size(self, item: dict):
        """
        Check file size

        :param item: item with parameters
        """
        request = self.prepare_request(item)
        try:
            self.msg = "Checking file size: {}".format(item["params"]['path'])
            self.log(self.msg)
            path = self.prepare_path(item["params"]['path'])
            if os.path.exists(path):
                size = os.path.getsize(path)
                response = {
                    "request": request,
                    "result": {
                        'size_bytes': size,
                        'size_human': self.plugin.human_readable_size(size),
                    },
                }
                self.log("File size: {}".format(size))
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
        self.response(response, self.get_extra_data())

    def cmd_file_info(self, item: dict):
        """
        Check file info

        :param item: item with parameters
        """
        request = self.prepare_request(item)
        try:
            self.msg = "Checking file info: {}".format(item["params"]['path'])
            self.log(self.msg)
            path = self.prepare_path(item["params"]['path'])
            if os.path.exists(path):
                size = os.path.getsize(path)
                data = {
                    "size": size,
                    "size_human": self.get_human_readable_size(size),
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
        self.response(response, self.get_extra_data())

    def cmd_cwd(self, item: dict):
        """
        Get current working directory

        :param item: item with parameters
        """
        request = self.prepare_request(item)
        try:
            self.msg = "Getting CWD: {}".format(self.plugin.window.core.config.get_user_dir('data'))
            self.log(self.msg)
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
        self.response(response, self.get_extra_data())

    def cmd_send_file(self, item: dict):
        """
        Get file as attachment

        :param item: item with parameters
        """
        request = self.prepare_request(item)
        try:
            self.msg = "Adding attachment: {}".format(item["params"]['path'])
            self.log(self.msg)
            path = self.prepare_path(item["params"]['path'])
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
        self.response(response, self.get_extra_data())

    def cmd_file_index(self, item: dict):
        """
        Index file or directory

        :param item: item with parameters
        """
        request = self.prepare_request(item)
        try:
            self.msg = "Indexing path: {}".format(item["params"]['path'])
            self.log(self.msg)
            path = self.prepare_path(item["params"]['path'])
            if os.path.exists(path):
                idx_name = self.plugin.get_option_value("idx")
                # index path using Llama-index
                files, errors = self.plugin.window.core.idx.index_files(
                    idx_name,
                    path,
                )
                data = {
                    'num_indexed': len(files),
                    'index_name': idx_name,
                    'errors': errors,
                    'path': path,
                }
                response = {
                    "request": request,
                    "result": data,
                }
            else:
                response = {
                    "request": request,
                    "result": "File or directory not found",
                }
                self.log("File not found: {}".format(path))
        except Exception as e:
            response = {
                "request": request,
                "result": "Error: {}".format(e),
            }
            self.error(e)
            self.log("Error: {}".format(e))
        self.response(response, self.get_extra_data())

    def get_human_readable_size(self, size, decimal_places=2):
        """
        Return a human-readable file size.

        :param size: file size in bytes
        :param decimal_places: number of decimal places
        :return: human-readable file size
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                break
            size /= 1024.0
        return f"{size:.{decimal_places}f} {unit}"

    def is_absolute_path(self, path: str) -> bool:
        """
        Check if path is absolute

        :param path: path to check
        :return: True if absolute
        """
        return os.path.isabs(path)

    def prepare_path(self, path: str) -> str:
        """
        Prepare path

        :param path: path to prepare
        :return: prepared path
        """
        if self.is_absolute_path(path):
            return path
        else:
            return os.path.join(
                self.plugin.window.core.config.get_user_dir('data'),
                path,
            )

    def read_files(self, paths: list) -> (dict, str):
        """
        Read files from directory

        :param paths: list of paths
        :return: response data and context
        """
        data = []
        context = []
        for path in paths:
            path = self.prepare_path(path)
            if os.path.exists(path):
                # + auto-index file using Llama-index
                if self.plugin.get_option_value("auto_index") \
                        or self.plugin.get_option_value("only_index"):
                    idx_name = self.plugin.get_option_value("idx")
                    files, errors = self.plugin.window.core.idx.index_files(
                        idx_name,
                        path,
                    )
                    # if only index, return response and continue
                    if self.plugin.get_option_value("only_index"):
                        data.append({
                            'num_indexed': len(files),
                            'index_name': idx_name,
                            'errors': errors,
                            'path': path,
                        })
                        self.log("File read (index only): {}".format(path))
                        return data, context

                # read file as text
                content = self.plugin.read_as_text(
                    path,
                    use_loaders=self.plugin.get_option_value("use_loaders"),
                )
                context.append(os.path.basename(path) + ":\n--------------------------------\n" + content)
                self.log("File read: {}".format(path))
            else:
                self.log("File not found: {}".format(path))
                data.append("File not found: {}".format(path))

        return data, context
