#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.20 03:00:00                  #
# ================================================== #

import json
import ssl

from urllib.parse import urlencode
from urllib.request import Request, urlopen

from pygpt_net.plugin.base.plugin import BasePlugin
from pygpt_net.core.events import Event, KernelEvent
from pygpt_net.item.ctx import CtxItem

from .config import Config
from .worker import Worker


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "cmd_api"
        self.name = "API calls"
        self.description = "Provides the ability to make external API calls"
        self.prefix = "API"
        self.order = 100
        self.use_locale = True
        self.worker = None
        self.config = Config(self)
        self.init_options()

    def init_options(self):
        """Initialize options"""
        self.config.from_defaults(self)

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

        # set state: busy
        self.cmd_prepare(ctx, my_commands)

        try:
            worker = Worker()
            worker.from_defaults(self)
            worker.cmds = my_commands
            worker.ctx = ctx

            if not self.is_async(ctx):
                worker.run()
                return
            worker.run_async()

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
