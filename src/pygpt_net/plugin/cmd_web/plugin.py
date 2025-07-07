#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.06.30 02:00:00                  #
# ================================================== #

import ssl
from urllib.request import Request, urlopen

from pygpt_net.plugin.base.plugin import BasePlugin
from pygpt_net.provider.web.base import BaseProvider
from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem

from .config import Config
from .websearch import WebSearch
from .worker import Worker


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "cmd_web"
        self.name = "Web Search"
        self.description = "Allows to connect to the Web and search web pages for actual data."
        self.prefix = "Web"
        self.urls = {}
        self.input_text = None
        self.allowed_cmds = [
            "web_search",
            "web_urls",
            "web_url_open",
            "web_url_raw",
            "web_request",
            "web_index",
            "web_index_query",
            "web_extract_links",
            "web_extract_images",
        ]
        self.order = 100
        self.use_locale = True
        self.worker = None
        self.websearch = WebSearch(self)
        self.config = Config(self)

    def init_options(self):
        """Initialize options"""
        self.config.from_defaults(self)
        self.init_provider()
        self.init_idx_options()

    def init_provider(self):
        """Initialize provider options"""
        providers = self.get_providers()
        for id in providers:
            providers[id].init(self)

    def init_idx_options(self):
        """Initialize indexing options"""
        instructions = self.window.core.idx.indexing.get_external_instructions()
        providers = self.window.core.idx.indexing.get_data_providers()
        # enable/disable indexing for each loader
        for id in list(instructions.keys()):
            name = id
            if id in providers:
                name = providers[id].name
            self.add_option(
                "index_web_" + id,
                type="bool",
                value=True,
                label="Enable: " + name,
                description="Enable indexing data from web loader: " + id,
                advanced=False,
                locale=False,
                tab="indexing",
            )

    def is_indexing_allowed(self, id: str) -> bool:
        """
        Check if indexing from specified loader is allowed

        :param id: loader ID
        :return: True if allowed
        """
        return self.get_option_value("index_web_" + id)

    def get_providers(self) -> dict:
        """
        Get web search providers

        :return: providers dict
        """
        return self.window.core.web.get_providers(self.window.core.web.PROVIDER_SEARCH_ENGINE)

    def get_provider_options(self) -> list:
        """Get provider options"""
        options = []
        providers = self.get_providers()
        for id in providers:
            options.append({id: providers[id].name})
        return options

    def init_tabs(self) -> dict:
        """
        Initialize provider tabs

        :return: dict of tabs
        """
        tabs = {}
        tabs["general"] = "General"
        tabs["indexing"] = "Indexing"
        providers = self.get_providers()
        for id in providers:
            tabs[id] = providers[id].name
        return tabs

    def attach(self, window):
        """
        Attach window

        :param window: Window
        """
        self.window = window

        # register provider tabs
        self.tabs = self.init_tabs()

        # register options
        self.init_options()

    def get_provider(self) -> BaseProvider:
        """
        Get search engine provider

        :return: provider instance
        """
        current = self.get_option_value("provider")
        providers = self.get_providers()
        if current not in providers:
            raise Exception("Provider '{}' not found!".format(current))
        return providers[current]

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

        if name == Event.INPUT_BEFORE:
            self.on_input_before(data['value'])

        elif name == Event.CMD_SYNTAX:
            self.cmd_syntax(data)

        elif name == Event.CMD_EXECUTE:
            self.cmd(ctx, data['commands'])

        elif name == Event.SETTINGS_CHANGED:
            # update indexes list
            self.refresh_option("idx")

        elif name == Event.MODELS_CHANGED:
            # update models list
            self.refresh_option("model_tmp_query")

    def on_input_before(self, text: str):
        """
        Event: INPUT_BEFORE

        :param text: input text
        """
        self.input_text = text

    def prepare_idx_syntax(self) -> dict:
        """
        Prepare web_index command syntax with instructions parsed from web loaders

        :return: syntax string
        """
        instructions = self.window.core.idx.indexing.get_external_instructions()
        types = {}
        args = {}
        for type in instructions:
            if not self.is_indexing_allowed(type):  # check if data loader is allowed
                continue
            types[type] = instructions[type]["description"]
            args[type] = list(instructions[type]["args"].keys())

        cmd = {
            "cmd": "web_index",
            "instruction": "read and index content from external source. Use it to read and index as vectors "
                        "(embed in vector DB) the provided URL for webpage or any other remote resource, like "
                        "YT video, RSS, etc. Provide type of the resource in the \"type\" param. If there is no allowed "
                        "type for a specified resource then use the default \"webpage\" type. If selected type requires "
                        "additional args, then pass them into \"args\"",
            "params": [
                {
                    "name": "type",
                    "type": "enum",
                    "description": "data type",
                    "required": True,
                    "default": "webpage",
                    "enum": {
                        "type": types,
                    }
                },
                {
                    "name": "args",
                    "type": "dict",
                    "description": "extra args for type",
                    "required": True,
                    "enum": {
                        "args": args,
                    }
                }
            ],
            "enabled": True,
        }
        return cmd

    def prepare_idx_query_syntax(self) -> dict:
        """
        Prepare web_index command syntax with instructions parsed from web loaders

        :return: syntax string
        """
        instructions = self.window.core.idx.indexing.get_external_instructions()
        types = {}
        args = {}
        for type in instructions:
            if not self.is_indexing_allowed(type):  # check if data loader is allowed
                continue
            types[type] = instructions[type]["description"]
            args[type] = list(instructions[type]["args"].keys())

        cmd = {
            "cmd": "web_index_query",
            "instruction": "read, index and query external content for additional context",
            "params": [
                {
                    "name": "type",
                    "type": "enum",
                    "description": "data type",
                    "required": True,
                    "default": "webpage",
                    "enum": {
                        "type": types,
                    }
                },
                {
                    "name": "args",
                    "type": "dict",
                    "description": "extra args for type",
                    "required": True,
                    "enum": {
                        "args": args,
                    }
                }
            ],
            "enabled": True,
        }
        return cmd

    def cmd_syntax(self, data: dict):
        """
        Event: CMD_SYNTAX

        :param data: event data dict
        """
        max_urls = self.get_option_value("max_open_urls")
        is_summary = True
        if self.get_option_value("raw"):
            is_summary = False

        for option in self.allowed_cmds:
            if not self.has_cmd(option):
                continue

            if option == "web_index":
                data['cmd'].append(self.prepare_idx_syntax())  # prepare params
                continue
            elif option == "web_index_query":
                data['cmd'].append(self.prepare_idx_query_syntax())  # prepare params
                continue
            elif option == "web_url_open":
                cmd = self.get_cmd(option)
                try:
                    cmd["instruction"] = cmd["instruction"].format(
                        max_urls=max_urls,
                    )
                    if not is_summary:
                        for param in list(cmd["params"]):
                            if param["name"] == "summarize_prompt":
                                cmd["params"].remove(param)
                    data['cmd'].append(cmd)
                    continue
                except Exception as e:
                    pass
            elif option == "web_url_raw":
                cmd = self.get_cmd(option)
                try:
                    cmd["instruction"] = cmd["instruction"].format(
                        max_urls=max_urls,
                    )
                    if not is_summary:
                        for param in list(cmd["params"]):
                            if param["name"] == "summarize_prompt":
                                cmd["params"].remove(param)
                    data['cmd'].append(cmd)
                    continue
                except Exception as e:
                    pass
            elif option == "web_search":
                max_pages = self.get_option_value("num_pages")
                cmd = self.get_cmd(option)
                try:
                    cmd["instruction"] = cmd["instruction"].format(
                        max_pages=max_pages,
                        max_urls=max_urls,
                    )
                    if not is_summary:
                        for param in list(cmd["params"]):
                            if param["name"] == "summarize_prompt":
                                cmd["params"].remove(param)
                    data['cmd'].append(cmd)
                    continue
                except Exception as e:
                    pass

            data['cmd'].append(self.get_cmd(option))  # append command

    def cmd(self, ctx: CtxItem, cmds: list):
        """
        Event: CMD_EXECUTE

        :param ctx: CtxItem
        :param cmds: commands dict
        """
        my_commands = []
        for item in cmds:
            if item["cmd"] in self.allowed_cmds and self.has_cmd(item["cmd"]):
                my_commands.append(item)

        if len(my_commands) == 0:
            return

        # check required API keys and other settings
        if not self.get_provider().is_configured(my_commands):
            self.window.ui.dialogs.alert(self.get_provider().get_config_message())
            self.gen_api_key_response(ctx, cmds)
            return

        # set state: busy
        self.cmd_prepare(ctx, my_commands)

        try:
            worker = Worker()
            worker.from_defaults(self)
            worker.cmds = my_commands
            worker.ctx = ctx
            worker.websearch = self.websearch
            if not self.is_async(ctx):
                worker.run()
                return
            worker.run_async()

        except Exception as e:
            self.error(e)

    def gen_api_key_response(self, ctx: CtxItem, cmds: list):
        """
        Generate response for empty API key error

        :param ctx: CtxItem
        :param cmds: commands dict
        """
        for item in cmds:
            request = {
                "cmd": item["cmd"],
            }
            err = "API key is not set. Please set credentials in plugin settings."
            self.log(err)
            self.window.update_status(err)
            msg = "Tell the user that the required API key or other config is not configured in the plugin settings, " \
                  "and to set the API key in the settings in order to use the internet search plugin."
            data = {
                'msg_to_user': msg,
            }
            response = {
                "request": request,
                "result": data,
            }
            self.reply(response, ctx)
            return

    def get_url(self, url: str, extra_headers: dict = None) -> bytes:
        """
        Get URL content

        :param url: URL
        :param extra_headers: extra headers
        :return: response data (bytes)
        """
        headers = {
            'User-Agent': self.get_option_value("user_agent"),
        }
        if extra_headers is not None:
            headers.update(extra_headers)

        req = Request(
            url=url,
            headers=headers,
        )
        data = ""
        try:
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
        except Exception as e:
            data = str(e)
        return data
