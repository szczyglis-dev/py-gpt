#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.25 01:00:00                  #
# ================================================== #

import json
from urllib.parse import quote

from PySide6.QtCore import Slot

from pygpt_net.plugin.base import BaseWorker, BaseSignals


class WorkerSignals(BaseSignals):
    pass  # add custom signals here


class Worker(BaseWorker):
    def __init__(self, *args, **kwargs):
        super(Worker, self).__init__()
        self.signals = BaseSignals()
        self.args = args
        self.kwargs = kwargs
        self.plugin = None
        self.cmds = None
        self.ctx = None

    @Slot()
    def run(self):
        msg = None
        for item in self.cmds:
            for my_cmd in self.plugin.get_option_value("cmds"):
                request = {"cmd": item["cmd"]}  # prepare request item for result
                if my_cmd["name"] == item["cmd"]:
                    try:
                        post_params = {}
                        post_json = str(my_cmd["post_json"])  # POST JSON, as string
                        headers = {}  # HTTP headers, if any, Auth, API key, etc.
                        result = None

                        # prepare call
                        endpoint = my_cmd["endpoint"]  # API endpoint URL

                        # extract extra headers from JSON if any
                        if 'headers' in my_cmd and my_cmd["headers"].strip() != "":
                            try:
                                headers = json.loads(my_cmd["headers"])  # key-value pairs
                            except json.JSONDecodeError as e:
                                msg = "Error decoding headers JSON: {}".format(e)
                                self.log(msg)
                                continue

                        # append GET params to endpoint URL placeholders
                        if 'get_params' in my_cmd and my_cmd["get_params"].strip() != "":
                            # append params to cmd placeholders
                            params_list = self.plugin.extract_params(
                                my_cmd["get_params"],
                            )
                            for param in params_list:
                                if param in item["params"]:
                                    endpoint = endpoint.replace(
                                        "{" + param + "}",  # replace { placeholder }
                                        quote(str(item["params"][param])),
                                    )

                        # append POST params to POST data placeholders and POST JSON
                        if 'post_params' in my_cmd and my_cmd["post_params"].strip() != "":
                            # append params to post params
                            params_list = self.plugin.extract_params(
                                my_cmd["post_params"],
                            )
                            for param in params_list:
                                if param in item["params"]:
                                    post_params[param] = item["params"][param]

                                    # append to POST JSON
                                    post_json = post_json.replace(
                                        "%" + param + "%",  # replace % placeholder
                                        str(item["params"][param]),
                                    )

                        # check if endpoint is not empty
                        if endpoint is None or endpoint == "":
                            msg = "Endpoint URL is empty!"
                            self.log(msg)
                            continue

                        # POST
                        if my_cmd["type"] == "POST":
                            msg = "[POST] Calling API endpoint: {}".format(endpoint)
                            self.log(msg)
                            result = self.plugin.call_post(endpoint, post_params, headers)

                        # POST JSON
                        elif my_cmd["type"] == "POST_JSON":
                            msg = "[POST JSON] Calling API endpoint: {}".format(endpoint)
                            self.log(msg)
                            try:
                                json_object = json.loads(post_json)
                                result = self.plugin.call_post(endpoint, json_object, headers)
                            except Exception as e:
                                msg = "Error: {}".format(e)
                                self.error(e)
                                self.log(msg)

                        # GET
                        elif my_cmd["type"] == "GET":
                            msg = "[GET] Calling API endpoint: {}".format(endpoint)
                            self.log(msg)
                            result = self.plugin.call_get(endpoint, headers)

                        if result is None:
                            result = "No response from API."
                            self.log(result)
                        else:
                            # encode bytes result to utf-8
                            result = result.decode("utf-8")

                        response = {
                            "request": request,
                            "result": result,
                        }

                    except Exception as e:
                        msg = "Error: {}".format(e)
                        response = {
                            "request": request,
                            "result": "Error {}".format(e),
                        }
                        self.error(e)
                        self.log(msg)
                    self.response(response)

        # update status
        if msg is not None:
            self.status(msg)
