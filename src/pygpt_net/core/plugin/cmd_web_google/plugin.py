#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.14 15:00:00                  #
# ================================================== #

from ..base_plugin import BasePlugin
from .websearch import WebSearch


class Plugin(BasePlugin):
    def __init__(self):
        super(Plugin, self).__init__()
        self.id = "cmd_web_google"
        self.name = "Command: Google Web Search"
        self.description = "Allows to connect to the Web and search web pages for actual data."
        self.input_text = None
        self.window = None
        self.allowed_cmds = ["web_search", "web_url_open"]
        self.order = 100
        self.init_options()
        self.websearch = WebSearch(self)

    def init_options(self):
        """
        Initializes options
        """
        self.add_option("google_api_key", "text", "",
                        "Google Custom Search API KEY",
                        "You can obtain your own API key at https://developers.google.com/custom-search/v1/overview",
                        tooltip="Google Custom Search CX ID", secret=True, persist=True)
        self.add_option("google_api_cx", "text", "",
                        "Google Custom Search CX ID",
                        "You will find your CX ID at https://programmablesearchengine.google.com/controlpanel/all"
                        "\nRemember to enable \"Search on ALL internet pages\" option in project settings.",
                        tooltip="Google Custom Search CX ID", secret=True, persist=True)
        self.add_option("num_pages", "int", 10,
                        "Number of pages to search",
                        "Number of max pages to search per query",
                        min=1, max=None)
        self.add_option("max_page_content_length", "int", 0,
                        "Max content characters",
                        "Max characters of page content to get (0 = unlimited)",
                        min=0, max=None)
        self.add_option("chunk_size", "int", 100000,
                        "Per-page content chunk size",
                        "Per-page content chunk size (max characters per chunk)",
                        min=1, max=None)
        self.add_option("use_google", "bool", True,
                        "Use Google Custom Search",
                        "Enable Google Custom Search API (API key required)",
                        tooltip="Google Custom Search")
        """
        self.add_option("use_wikipedia", "bool", True,
                        "Use Wikipedia",
                        "Enable above option to use Wikipedia API (free, no API key required)",
                        tooltip="Wikipedia API")
        """
        self.add_option("disable_ssl", "bool", True,
                        "Disable SSL verify",
                        "Disables SSL verification when crawling web pages",
                        tooltip="Disable SSL verify")
        self.add_option("max_result_length", "int", 1500,
                        "Max result length",
                        "Max length of summarized result (characters)",
                        min=0, max=None)
        self.add_option("summary_max_tokens", "int", 1500,
                        "Max summary tokens",
                        "Max tokens in output when generating summary",
                        min=0, max=None)
        self.add_option("summary_model", "text", "gpt-3.5-turbo-1106",
                        "Model used for web page summarize",
                        "Model used for web page summarize, default: gpt-3.5-turbo-1106", advanced=True)
        self.add_option("prompt_summarize", "textarea", "Summarize text in English in a maximum of 3 paragraphs, "
                                                        "trying to find the most important content that can help "
                                                        "answer the following question: {query}",
                        "Summarize prompt",
                        "Prompt used for web search results summarize, use {query} as a placeholder for search query",
                        tooltip="Prompt", advanced=True)
        self.add_option("prompt_summarize_url", "textarea", "Summarize text in English in a maximum of 3 paragraphs, "
                                                            "trying to find the most important content.",
                        "Summarize prompt (URL open)",
                        "Prompt used for specified URL page summarize",
                        tooltip="Prompt", advanced=True)

        self.add_option("syntax_web_search", "textarea", '"web_search": use it to search the Web for more info, '
                                                         'prepare a query for the search engine itself, start from '
                                                         'page 1. If you don\'t find anything or don\'t find enough '
                                                         'information, try the next page. Use a custom summary prompt '
                                                         'if necessary, otherwise, a default summary will be used. '
                                                         'Max pages limit: {max_pages}, params: "query", "page", '
                                                         '"summarize_prompt"',
                        "Syntax: web_search",
                        "Syntax for web search command, use {max_pages} as a placeholder for `num_pages` value", advanced=True)
        self.add_option("syntax_web_url_open", "textarea", '"web_url_open": use it to get contents from a specific '
                                                           'Web page. Use a custom summary prompt if necessary, '
                                                           'otherwise a default summary will be used. Params: "url", '
                                                           '"summarize_prompt"',
                        "Syntax: web_url_open",
                        "Syntax for web URL open command", advanced=True)

    def setup(self):
        """
        Returns available config options

        :return: config options
        """
        return self.options

    def attach(self, window):
        """
        Attaches window

        :param window: Window
        """
        self.window = window

    def on_user_send(self, text):
        """
        Event: On user send text

        :param text: Text
        :return: Text
        """
        return text

    def on_ctx_begin(self, ctx):
        """
        Event: On new context begin

        :param ctx: Context
        :return: Context
        """
        return ctx

    def on_ctx_end(self, ctx):
        """
        Event: On context end

        :param ctx: Context
        :return: Context
        """
        return ctx

    def on_system_prompt(self, prompt):
        """
        Event: On prepare system prompt

        :param prompt: Prompt
        :return: Prompt
        """
        return prompt

    def on_ai_name(self, name):
        """
        Event: On set AI name

        :param name: Name
        :return: Name
        """
        return name

    def on_user_name(self, name):
        """
        Event: On set username

        :param name: Name
        :return: Name
        """
        return name

    def on_enable(self):
        """Event: On plugin enable"""
        pass

    def on_disable(self):
        """Event: On plugin disable"""
        pass

    def on_input_before(self, text):
        """
        Event: Before input

        :param text: Text
        """
        self.input_text = text
        return text

    def on_ctx_before(self, ctx):
        """
        Event: Before ctx

        :param ctx: Text
        """
        return ctx

    def on_ctx_after(self, ctx):
        """
        Event: After ctx

        :param ctx: ctx
        """
        return ctx

    def log(self, msg):
        """
        Logs message to console

        :param msg: Message to log
        """
        self.window.log('[CMD] ' + str(msg))
        print('[CMD] ' + str(msg))

    def cmd_syntax(self, syntax):
        """
        Event: On cmd syntax prepare

        :param syntax: Syntax
        :return: Syntax
        """
        for option in self.allowed_cmds:
            key = "syntax_" + option
            if key in self.options:
                syntax += "\n" + self.options[key]["value"]
        return syntax

    def cmd(self, ctx, cmds):
        """
        Event: On cmd

        :param ctx: Context
        :param cmds: Commands
        :return: Context
        """
        msg = None
        for item in cmds:
            try:
                if item["cmd"] in self.allowed_cmds:

                    ctx.reply = True

                    # prepare request item for result
                    request_item = {"cmd": item["cmd"]}

                    if item["cmd"] == "web_search":
                        page = 1
                        if "page" in item["params"]:
                            page = int(item["params"]["page"])
                        custom_summarize_prompt = None
                        if "summarize_prompt" in item["params"]:
                            custom_summarize_prompt = item["params"]["summarize_prompt"]
                        msg = "Web search finished: '{}'".format(item["params"]["query"])
                        result, total_found, current, url = self.websearch.make_query(item["params"]["query"], page, custom_summarize_prompt)
                        data = {
                            'content': result,
                            'url': url,
                            'page': current,
                            'total_found': total_found,
                        }
                        response = {"request": request_item, "result": data}
                        ctx.results.append(response)

                    elif item["cmd"] == "web_url_open":
                        custom_summarize_prompt = None
                        if "summarize_prompt" in item["params"]:
                            custom_summarize_prompt = item["params"]["summarize_prompt"]
                        url = item["params"]["url"]
                        msg = "Opening Web URL: '{}'".format(item["params"]["url"])
                        result, url = self.websearch.open_url(url, custom_summarize_prompt)
                        data = {
                            'content': result,
                            'url': url,
                        }
                        response = {"request": request_item, "result": data}
                        ctx.results.append(response)
            except Exception as e:
                response = {"request": item, "result": "Error: {}".format(e)}
                ctx.results.append(response)
                ctx.reply = True
                self.log("Error: {}".format(e))

        if msg is not None:
            self.log(msg)
            self.window.statusChanged.emit(msg)
        return ctx
