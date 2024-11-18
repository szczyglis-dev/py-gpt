#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.14 01:00:00                  #
# ================================================== #

import ssl
from urllib.request import Request, urlopen

from pygpt_net.plugin.base import BasePlugin
from pygpt_net.provider.web.base import BaseProvider
from pygpt_net.core.dispatcher import Event
from pygpt_net.item.ctx import CtxItem

from .websearch import WebSearch
from .worker import Worker


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "cmd_web"
        self.name = "Command: Web Search"
        self.description = "Allows to connect to the Web and search web pages for actual data."
        self.urls = {}
        self.input_text = None
        self.allowed_cmds = [
            "web_search",
            "web_urls",
            "web_url_open",
            "web_url_raw",
            "web_index",
            "web_index_query",
        ]
        self.order = 100
        self.use_locale = True
        self.worker = None
        self.websearch = WebSearch(self)

    def init_options(self):
        """Initialize options"""
        self.add_option(
            "provider",
            type="combo",
            value="google_custom_search",
            label="Provider",
            description="Select search engine provider, default: Google",
            tooltip="Select search engine provider",
            keys=self.get_provider_options(),
        )
        self.add_option(
            "num_pages",
            type="int",
            value=10,
            label="Number of pages to search",
            description="Number of max pages to search per query",
            min=1,
            max=None,
        )
        self.add_option(
            "max_page_content_length",
            type="int",
            value=0,
            label="Max content characters",
            description="Max characters of page content to get (0 = unlimited)",
            min=0,
            max=None,
        )
        self.add_option(
            "chunk_size",
            type="int",
            value=20000,
            label="Per-page content chunk size",
            description="Per-page content chunk size (max characters per chunk)",
            min=1,
            max=None,
        )
        self.add_option(
            "disable_ssl",
            type="bool",
            value=True,
            label="Disable SSL verify",
            description="Disables SSL verification when crawling web pages",
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
        self.add_option(
            "max_result_length",
            type="int",
            value=1500,
            label="Max result length",
            description="Max length of summarized result (characters)",
            min=0,
            max=None,
        )
        self.add_option(
            "summary_max_tokens",
            type="int",
            value=1500,
            label="Max summary tokens",
            description="Max tokens in output when generating summary",
            min=0,
            max=None,
        )
        self.add_option(
            "model_tmp_query",
            type="combo",
            value="gpt-3.5-turbo",
            label="Model for query in-memory index",
            description="Model used for query in-memory index for `web_index_query` command, "
                        "default: gpt-3.5-turbo",
            tooltip="Query model",
            use="models",
            tab="indexing",
        )
        self.add_option(
            "auto_index",
            type="bool",
            value=False,
            label="Auto-index all used URLs using Llama-index",
            description="If enabled, every URL used by the model will be automatically indexed using Llama-index "
                        "(persistent index)",
            tooltip="If enabled, every URL used by the model will be automatically indexed using Llama-index "
                    "(persistent index)",
            tab="indexing",
        )
        self.add_option(
            "idx",
            type="text",
            value="base",
            label="Index to use",
            description="ID of index to use for web page indexing (persistent index)",
            tooltip="Index name",
            tab="indexing",
        )
        self.add_option(
            "summary_model",
            type="text",
            value="gpt-3.5-turbo-1106",
            label="Model used for web page summarize",
            description="Model used for web page summarize, default: gpt-3.5-turbo-1106",
            advanced=True,
        )
        self.add_option(
            "prompt_summarize",
            type="textarea",
            value="Summarize text in English in a maximum of 3 paragraphs, trying to find the most "
                  "important content that can help answer the following question: {query}",
            label="Summarize prompt",
            description="Prompt used for web search results summarize, use {query} "
                        "as a placeholder for search query",
            tooltip="Prompt",
            advanced=True,
        )
        self.add_option(
            "prompt_summarize_url",
            type="textarea",
            value="Summarize text in English in a maximum of 3 paragraphs, trying to find the most "
                  "important content.",
            label="Summarize prompt (URL open)",
            description="Prompt used for specified URL page summarize",
            tooltip="Prompt",
            advanced=True,
        )

        # commands
        self.add_cmd(
            "web_search",
            instruction="search the Web for more info, prepare a query for the search engine itself, start from page 1. "
                        "If no results, then try the next page. "
                        "Use a custom summary prompt if necessary, otherwise, a default summary will be used. "
                        "Max pages: {max_pages}",
            params=[
                {
                    "name": "query",
                    "type": "str",
                    "description": "search query",
                    "required": True,
                },
                {
                    "name": "page",
                    "type": "int",
                    "description": "page number",
                    "required": False,
                },
                {
                    "name": "summarize_prompt",
                    "type": "str",
                    "description": "summary prompt",
                    "required": False,
                },
            ],
            enabled=True,
            description="If enabled, model will be able to search the Web",
        )
        self.add_cmd(
            "web_url_open",
            instruction="read and get summarized content from ANY website URL. Use a custom summary prompt if necessary, "
                        "otherwise default summary will be used",
            params=[
                {
                    "name": "url",
                    "type": "str",
                    "description": "URL to website",
                    "required": True,
                },
                {
                    "name": "summarize_prompt",
                    "type": "str",
                    "description": "summary prompt",
                    "required": False,
                },
            ],
            enabled=True,
            description="If enabled, model will be able to open URL and summarize content",
        )
        self.add_cmd(
            "web_url_raw",
            instruction="read and get raw HTML/txt content (not summarized) from ANY website URL",
            params=[
                {
                    "name": "url",
                    "type": "str",
                    "description": "URL to website",
                    "required": True,
                },
            ],
            enabled=True,
            description="If enabled, model will be able to open specified URL and get raw content",
        )
        self.add_cmd(
            "web_urls",
            instruction="search the Web for list of URLs, prepare search query itself, list of "
                        "URLs will be returned, 10 links per page max.",
            params=[
                {
                    "name": "query",
                    "type": "str",
                    "description": "search query",
                    "required": True,
                },
                {
                    "name": "page",
                    "type": "int",
                    "description": "page number",
                    "required": False,
                },
                {
                    "name": "num_links",
                    "type": "int",
                    "description": "links per page",
                    "required": False,
                },
            ],
            enabled=True,
            description="If enabled, model will be able to search the Web and get founded URLs list",
        )
        self.add_cmd(
            "web_index",
            instruction="",
            params=[],  # prepared dynamically
            enabled=True,
            tab="indexing",
            description="If enabled, model will be able to index web content using Llama-index (persistent index)",
        )
        self.add_cmd(
            "web_index_query",
            instruction="read, index and query external content for additional context.",
            params=[],  # prepared dynamically
            enabled=True,
            tab="indexing",
            description="If enabled, model will be able to index and query web content using Llama-index "
                    "(temporary index, on the fly)",
        )
        
        # register provider options
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
        return self.window.core.web.get_providers("search_engine")

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

    def setup(self) -> dict:
        """
        Return available config options

        :return: config options
        """
        return self.options

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
        for option in self.allowed_cmds:
            if not self.has_cmd(option):
                continue

            # special case for web_index
            if option == "web_index":
                data['cmd'].append(self.prepare_idx_syntax())  # prepare params
                continue
            elif option == "web_index_query":
                data['cmd'].append(self.prepare_idx_query_syntax())  # prepare params
                continue
            elif option == "web_search":
                max_pages = self.get_option_value("num_pages")
                cmd = self.get_cmd(option)
                try:
                    cmd["instruction"] = cmd["instruction"].format(max_pages=max_pages)
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

        try:
            # worker
            self.worker = Worker()
            self.worker.plugin = self
            self.worker.cmds = my_commands
            self.worker.ctx = ctx
            self.worker.websearch = self.websearch

            # signals (base handlers)
            self.worker.signals.finished_more.connect(self.handle_finished_more)
            self.worker.signals.log.connect(self.handle_log)
            self.worker.signals.debug.connect(self.handle_debug)
            self.worker.signals.status.connect(self.handle_status)
            self.worker.signals.error.connect(self.handle_error)

            # check if async allowed
            if not self.window.core.dispatcher.async_allowed(ctx):
                self.worker.run()
                return

            # start
            self.window.threadpool.start(self.worker)

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
            self.window.ui.status(err)
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
        if self.is_threaded():
            return
        full_msg = '[CMD] ' + str(msg)
        self.debug(full_msg)
        self.window.ui.status(full_msg)
        if self.is_log():
            print(full_msg)
