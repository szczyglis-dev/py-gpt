#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.18 21:00:00                  #
# ================================================== #

import json
from urllib.parse import quote

from PySide6.QtCore import Slot

from pygpt_net.plugin.base.worker import BaseWorker, BaseSignals


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
        responses = []
        msg = None
        for item in self.cmds:
            if self.is_stopped():
                break
            for my_cmd in self.plugin.get_option_value("cmds"):
                if self.is_stopped():
                    break
                if my_cmd["name"] == item["cmd"]:
                    try:
                        response = self.handle_cmd(my_cmd, item)
                        if response is False:
                            continue
                        responses.append(response)

                    except Exception as e:
                        msg = "Error: {}".format(e)
                        responses.append(
                            self.make_response(
                                item,
                                self.throw_error(e)
                            )
                        )

        # send response
        if len(responses) > 0:
            self.reply_more(responses)

        # update status
        if msg is not None:
            self.status(msg)

    def handle_cmd(self, command: dict, item: dict) -> dict or bool:
        """
        Handle API command

        :param command: command configuration
        :param item: requested item
        :return: response or False
        """
        post_params = {}
        post_json_tpl = ""
        headers = {}  # HTTP headers, if any, Auth, API key, etc.
        result = None
        if 'post_json' in command and command["post_json"].strip() != "":
            post_json_tpl = str(command["post_json"])  # POST JSON, as string

        # prepare call
        endpoint = command["endpoint"]  # API endpoint URL

        # extract extra headers from JSON if any
        if 'headers' in command and command["headers"].strip() != "":
            try:
                headers = json.loads(command["headers"])  # key-value pairs
            except json.JSONDecodeError as e:
                msg = "Error decoding headers JSON: {}".format(e)
                self.log(msg)
                return False  # abort

        # append GET params to endpoint URL placeholders
        if 'get_params' in command and command["get_params"].strip() != "":
            # append params to cmd placeholders
            params_list = self.plugin.extract_params(
                command["get_params"],
            )
            for p in params_list:
                param = p["name"]
                if param in item["params"]:
                    endpoint = endpoint.replace(
                        "{" + param + "}",  # replace { placeholder }
                        quote(str(item["params"][param])),
                    )

        # append POST params to POST data placeholders and POST JSON
        if 'post_params' in command and command["post_params"].strip() != "":
            # append params to post params
            params_list = self.plugin.extract_params(
                command["post_params"],
            )
            for p in params_list:
                param = p["name"]
                if param in item["params"]:
                    post_params[param] = item["params"][param]

                    # append to POST JSON
                    post_json_tpl = post_json_tpl.replace(
                        "%" + param + "%",  # replace % placeholder
                        str(item["params"][param]),
                    )

        # check if endpoint is not empty
        if endpoint is None or endpoint == "":
            msg = "Endpoint URL is empty!"
            self.log(msg)
            return False  # abort

        # check if type is not empty
        if command["type"] not in ["POST", "POST_JSON", "GET"]:
            command["type"] = "GET"

        # POST
        if command["type"] == "POST":
            msg = "[POST] Calling API endpoint: {}".format(endpoint)
            self.log(msg)
            result = self.plugin.call_post(endpoint, post_params, headers)

        # POST JSON
        elif command["type"] == "POST_JSON":
            msg = "[POST JSON] Calling API endpoint: {}".format(endpoint)
            self.log(msg)
            try:
                json_object = {}
                if post_json_tpl is not None and post_json_tpl.strip() != "":
                    json_object = json.loads(post_json_tpl)
                result = self.plugin.call_post_json(endpoint, json_object, headers)
            except Exception as e:
                msg = "Error: {}".format(e)
                self.error(e)
                self.log(msg)

        # GET
        elif command["type"] == "GET":
            msg = "[GET] Calling API endpoint: {}".format(endpoint)
            self.log(msg)
            result = self.plugin.call_get(endpoint, headers)

        if result is None:
            result = "No response from API."
            self.log(result)
        else:
            # encode bytes result to utf-8
            result = result.decode("utf-8")

        extra = {
            'url': endpoint,
            'type': command["type"],
        }
        return self.make_response(item, result, extra=extra)
