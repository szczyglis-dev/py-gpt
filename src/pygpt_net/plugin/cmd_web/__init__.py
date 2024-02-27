#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.27 04:00:00                  #
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
        ]
        self.order = 100
        self.use_locale = True
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
            "cmd_web_search",
            type="bool",
            value=True,
            label="Enable: \"web_search\" command",
            description="Allow using command: web_search",
            tooltip="If enabled, model will be able to search the Web",
        )
        self.add_option(
            "cmd_web_url_open",
            type="bool",
            value=True,
            label="Enable: \"web_url_open\" command",
            description="Allow using command: web_url_open",
            tooltip="If enabled, model will be able to open specified URL and summarize content",
        )
        self.add_option(
            "cmd_web_url_raw",
            type="bool",
            value=True,
            label="Enable: \"web_url_raw\" command",
            description="Allow using command: web_url_raw",
            tooltip="If enabled, model will be able to open specified URL and get raw content",
        )
        self.add_option(
            "cmd_web_urls",
            type="bool",
            value=True,
            label="Enable: \"web_urls\" command",
            description="Allow using command: web_urls",
            tooltip="If enabled, model will be able to search the Web and get founded URLs list",
        )
        self.add_option(
            "cmd_web_index",
            type="bool",
            value=True,
            label="Enable: \"web_index\" command",
            description="If enabled, model will be able to index web pages using Llama-index",
            tooltip="If enabled, model will be able to index web pages using Llama-index",
        )
        self.add_option(
            "auto_index",
            type="bool",
            value=False,
            label="Auto-index all used URLs using Llama-index",
            description="If enabled, every URL used by the model will be automatically indexed using Llama-index",
            tooltip="If enabled, every URL used by the model will be automatically indexed using Llama-index",
        )
        self.add_option(
            "idx",
            type="text",
            value="base",
            label="Index to use",
            description="ID of index to use for web page indexing",
            tooltip="Index name",
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
        self.add_option(
            "syntax_web_search",
            type="textarea",
            value='"web_search": use it to search the Web for more info, prepare a query for the search '
                  'engine itself, start from page 1. If you don\'t find anything or don\'t find enough '
                  'information, try the next page. Use a custom summary prompt if necessary, otherwise, '
                  'a default summary will be used. Max pages limit: {max_pages}, params: "query", "page", '
                  '"summarize_prompt"',
            label="Syntax: web_search",
            description="Syntax for web_search command, use {max_pages} as a placeholder for "
                        "`num_pages` value",
            advanced=True,
        )
        self.add_option(
            "syntax_web_url_open",
            type="textarea",
            value='"web_url_open": use it to get contents from a specific Web page. Use a custom summary '
                  'prompt if necessary, otherwise a default summary will be used. Params: "url", '
                  '"summarize_prompt"',
            label="Syntax: web_url_open",
            description="Syntax for web_url_open command",
            advanced=True,
        )
        self.add_option(
            "syntax_web_url_raw",
            type="textarea",
            value='"web_url_raw": use it to get RAW text/html content (not summarized) from a specific Web page. '
                  'Params: "url"',
            label="Syntax: web_url_raw",
            description="Syntax for web_url_raw command",
            advanced=True,
        )
        self.add_option(
            "syntax_web_urls",
            type="textarea",
            value='"web_urls": use it to search the Web for URLs to use, prepare a search query itself, '
                  'a list of found links to websites will be returned, 10 links per page max. You can change the page '
                  'or the number of links per page using the provided parameters. Params: "query", "page", '
                  '"num_links"',
            label="Syntax: web_urls",
            description="Syntax for web_urls command",
            advanced=True,
        )
        """
        # handled by code
        self.add_option(
            "syntax_web_index",
            type="textarea",
            value='"web_index": use it to index (embed in Vector Store) provided webpage URL for future use. '
                  'Params: "url"',
            label="Syntax: web_index",
            description="Syntax for web_index command",
            advanced=True,
        )
        """

        # register provider options
        self.init_provider()

    def init_provider(self):
        """Initialize provider options"""
        providers = self.get_providers()
        for id in providers:
            providers[id].init(self)

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

    def prepare_idx_syntax(self) -> str:
        """
        Prepare web_index command syntax

        :return: syntax string
        """
        types = self.window.core.idx.indexing.get_external_instructions()
        allowed_types = ""
        for key in types:
            allowed_types += "\n- `{}`: {}".format(key, types[key])
        return '"web_index": with this command YOU CAN READ AND INDEX CONTENT FROM EXTERNAL SOURCES. ' \
               'Use it to read and index (embed in a Vector Store) the provided URL for webpage or any other ' \
               'remote resource, like YT video. Provide type of resource in the "type" ' \
               'param. If there is no allowed type for a specified resource then use the default "webpage" type. ' \
               'If selected type requires additional args then pass them into "extra_args" param.\n' \
               'Allowed types:{allowed_types}.\n ' \
               'Params: "url", "type", "extra_args"'.format(allowed_types=allowed_types)

    def cmd_syntax(self, data: dict):
        """
        Event: CMD_SYNTAX

        :param data: event data dict
        """
        for option in self.allowed_cmds:
            if not self.get_option_value("cmd_" + option):
                continue

            # special case for web_index
            if option == "web_index":
                data['syntax'].append(
                    self.prepare_idx_syntax(),
                )
                continue

            key = "syntax_" + option
            if self.has_option(key):
                data['syntax'].append(
                    self.get_option_value(key),
                )

    def cmd(self, ctx: CtxItem, cmds: list):
        """
        Event: CMD_EXECUTE

        :param ctx: CtxItem
        :param cmds: commands dict
        """
        my_commands = []
        for item in cmds:
            if item["cmd"] in self.allowed_cmds and self.get_option_value("cmd_" + item["cmd"]):
                my_commands.append(item)

        if len(my_commands) == 0:
            return

        # check required API keys and other settings
        if not self.get_provider().is_configured(my_commands):
            self.gen_api_key_response(ctx, cmds)
            self.window.ui.dialogs.alert(self.get_provider().get_config_message())
            return

        try:
            # worker
            worker = Worker()
            worker.plugin = self
            worker.cmds = my_commands
            worker.ctx = ctx
            worker.websearch = self.websearch

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
            ctx.results.append(response)
            ctx.reply = True
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
        full_msg = '[CMD] ' + str(msg)
        self.debug(full_msg)
        self.window.ui.status(full_msg)
        if self.is_log():
            print(full_msg)
