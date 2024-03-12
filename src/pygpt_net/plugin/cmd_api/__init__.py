#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.12 06:00:00                  #
# ================================================== #

import json
import ssl
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from pygpt_net.plugin.base import BasePlugin
from pygpt_net.core.dispatcher import Event
from pygpt_net.item.ctx import CtxItem

from .worker import Worker


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "cmd_api"
        self.name = "Command: API calls"
        self.description = "Provides the ability to make external API calls"
        self.order = 100
        self.use_locale = True
        self.init_options()

    def init_options(self):
        """Initialize options"""
        keys = {
            "enabled": "bool",
            "name": "text",
            "instruction": "textarea",
            "get_params": "textarea",
            "post_params": "textarea",
            "post_json": "textarea",
            "headers": "textarea",
            "type": {
                "type": "combo",
                "keys": [
                    {"GET": "GET"},
                    {"POST": "POST"},
                    {"POST_JSON": "POST_JSON"},
                ],
            },
            "endpoint": "textarea",
        }
        items = [
            {
                "enabled": True,
                "name": "search_wiki",
                "instruction": "send API call to Wikipedia to search pages by query",
                "get_params": "query, limit",
                "post_params": "",
                "post_json": "",
                "headers": "",
                "type": "GET",
                "endpoint": 'https://en.wikipedia.org/w/api.php?action=opensearch&limit={limit}&format=json&search={query}',
            },
        ]
        desc = "Add your custom API calls here"
        tooltip = "See the documentation for more details about examples, usage and list of predefined placeholders"
        self.add_option(
            "cmds",
            type="dict",
            value=items,
            label="Your custom API calls",
            description=desc,
            tooltip=tooltip,
            keys=keys,
        )
        self.add_option(
            "disable_ssl",
            type="bool",
            value=False,
            label="Disable SSL verify",
            description="Disables SSL verification when making calls to API",
            tooltip="Disable SSL verify",
        )
        self.add_option(
            "timeout",
            type="int",
            value=5,
            label="Timeout",
            description="Connection timeout (seconds)",
            tooltip="Connection timeout (seconds)",
        )
        self.add_option(
            "user_agent",
            type="text",
            value="Mozilla/5.0",
            label="User agent",
            description="User agent to use when making requests, default: Mozilla/5.0",
            tooltip="User agent to use when making requests",
        )

    def setup(self) -> dict:
        """
        Return available config options

        :return: config options
        """
        return self.options

    def attach(self, window):
        """
        Attach window

        :param window: Window instance
        """
        self.window = window

    def handle(self, event: Event, *args, **kwargs):
        """
        Handle dispatched event

        :param event: event object
        :param args: event args
        :param kwargs: event kwargs
        """
        name = event.name
        data = event.data
        ctx = event.ctx

        if name == Event.CMD_SYNTAX:
            self.cmd_syntax(data)

        elif name == Event.CMD_EXECUTE:
            self.cmd(
                ctx,
                data['commands'],
            )

    def cmd_syntax(self, data: dict):
        """
        Event: CMD_SYNTAX

        :param data: event data dict
        """
        for item in self.get_option_value("cmds"):
            if not item["enabled"]:
                continue
            cmd = {
                "cmd": item["name"],
                "instruction": item["instruction"],
                "params": [],
            }
            # GET
            if item["get_params"].strip() != "":
                params = self.extract_params(item["get_params"])
                if len(params) > 0:
                    for param in params:
                        cmd["params"].append(param)
            # POST
            if item["post_params"].strip() != "":
                params = self.extract_params(item["post_params"])
                if len(params) > 0:
                    for param in params:
                        cmd["params"].append(param)

            data['cmd'].append(cmd)

    def cmd(self, ctx: CtxItem, cmds: list):
        """
        Event: CMD_EXECUTE

        :param ctx: CtxItem
        :param cmds: commands dict
        """
        is_cmd = False
        my_commands = []
        for item in cmds:
            for my_cmd in self.get_option_value("cmds"):
                if not my_cmd["enabled"]:
                    continue
                if my_cmd["name"] == item["cmd"]:
                    is_cmd = True
                    my_commands.append(item)

        if not is_cmd:
            return

        try:
            # worker
            worker = Worker()
            worker.plugin = self
            worker.cmds = my_commands
            worker.ctx = ctx

            # signals (base handlers)
            worker.signals.finished.connect(self.handle_finished)
            worker.signals.log.connect(self.handle_log)
            worker.signals.debug.connect(self.handle_debug)
            worker.signals.status.connect(self.handle_status)
            worker.signals.error.connect(self.handle_error)

            # check if async allowed
            if not self.window.core.dispatcher.async_allowed(ctx):
                worker.run()
                return

            # start
            self.window.threadpool.start(worker)

        except Exception as e:
            self.error(e)

    def get_item(self, name: str) -> dict:
        """
        Get API call by name

        :param name: call name
        :return: call dict
        """
        for item in self.get_option_value("cmds"):
            if item["name"] == name:
                return item
        return {}

    def extract_params(self, text: str) -> list:
        """
        Extract params from params string

        :param text: text
        :return: params list
        """
        params = []
        if text is None or text == "":
            return params
        params_list = text.split(",")
        for param in params_list:
            param = param.strip()
            if param == "":
                continue
            params.append({
                "name": param,
                "type": "str",
                "description": param,
            })
        return params

    def call_get(self, url: str, extra_headers: dict = None) -> bytes:
        """
        Call API with GET method

        :param url: URL
        :param extra_headers: extra headers
        :return: response data
        """
        headers = {
            'User-Agent': self.get_option_value("user_agent"),
        }
        if extra_headers is not None:
            headers.update(extra_headers)

        # log API call details
        log_data = {
            "url": url,
            "headers": headers,
            "type": "GET",
        }
        self.log(str(log_data))

        # prepare request
        req = Request(
            url=url,
            headers=headers,
        )
        if self.get_option_value('disable_ssl'):
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            data = urlopen(
                req,
                context=context,
                timeout=self.get_option_value('timeout'),
            ).read()
        else:
            data = urlopen(
                req,
                timeout=self.get_option_value('timeout'),
            ).read()
        return data

    def call_post(self, url: str, data: dict, extra_headers: dict = None) -> bytes:
        """
        Call API with POST method

        :param url: URL
        :param data: POST data dict
        :param extra_headers: extra headers
        :return: response data
        """
        headers = {
            'User-Agent': self.get_option_value("user_agent"),
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        if extra_headers is not None:
            headers.update(extra_headers)

        # encode data
        data = urlencode(data).encode()

        # log API call details
        log_data = {
            "url": url,
            "data": data,
            "headers": headers,
            "type": "POST",
        }
        self.log(str(log_data))

        # prepare request
        req = Request(
            url=url,
            data=data,
            headers=headers,
        )
        if self.get_option_value('disable_ssl'):
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            data = urlopen(
                req,
                context=context,
                timeout=self.get_option_value('timeout'),
            ).read()
        else:
            data = urlopen(
                req,
                timeout=self.get_option_value('timeout'),
            ).read()
        return data

    def call_post_json(self, url: str, data: dict, extra_headers: dict = None) -> bytes:
        """
        Call API with POST method (JSON)

        :param url: URL
        :param data: POST data dict
        :param extra_headers: extra headers
        :return: response data
        """
        headers = {
            'User-Agent': self.get_option_value("user_agent"),
            'Content-Type': 'application/json',
        }
        if extra_headers is not None:
            headers.update(extra_headers)

        # encode data
        data = json.dumps(data).encode()

        # log API call details
        log_data = {
            "url": url,
            "data": data,
            "headers": headers,
            "type": "POST JSON",
        }
        self.log(str(log_data))

        # prepare request
        req = Request(
            url=url,
            data=data,
            headers=headers,
        )
        if self.get_option_value('disable_ssl'):
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            data = urlopen(
                req,
                context=context,
                timeout=self.get_option_value('timeout'),
            ).read()
        else:
            data = urlopen(
                req,
                timeout=self.get_option_value('timeout'),
            ).read()
        return data

    def log(self, msg: str):
        """
        Log message to console

        :param msg: message to log
        """
        full_msg = '[API] ' + str(msg)
        self.debug(full_msg)
        self.window.ui.status(full_msg)
        if self.is_log():
            print(full_msg)
