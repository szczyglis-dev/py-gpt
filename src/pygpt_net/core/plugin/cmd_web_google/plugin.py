#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.05 22:00:00                  #
# ================================================== #

from ..base_plugin import BasePlugin
from .websearch import WebSearch


class Plugin(BasePlugin):
    def __init__(self):
        super(Plugin, self).__init__()
        self.id = "cmd_web_google"
        self.name = "Command: Google Web Search"
        self.description = "Allows to connect to the Web and search web pages for actual data."
        self.options = {}
        self.options["google_api_key"] = {
            "type": "text",
            "slider": False,
            "label": "Google Custom Search API KEY",
            "description": "You can obtain your own API key at https://developers.google.com/custom-search/v1/overview",
            "tooltip": "Google Custom Search API Key",
            "value": '',
            "min": None,
            "max": None,
            "multiplier": None,
            "step": None,
        }
        self.options["google_api_cx"] = {
            "type": "text",
            "slider": False,
            "label": "Google Custom Search CX ID",
            "description": "You will find your CX ID at https://programmablesearchengine.google.com/controlpanel/all"
                           "\nRemember to enable \"Search on ALL internet pages\" option in project settings.",
            "tooltip": "Google Custom Search CX ID",
            "value": '',
            "min": None,
            "max": None,
            "multiplier": None,
            "step": None,
        }
        self.options["num_pages"] = {
            "type": "int",
            "slider": False,
            "label": "Number of max pages to search per query",
            "description": "",
            "tooltip": "",
            "value": 10,
            "min": 1,
            "max": None,
            "multiplier": None,
            "step": None,
        }
        self.options["max_page_content_length"] = {
            "type": "int",
            "slider": False,
            "label": "Max characters of page content to get (0 = unlimited)",
            "description": "",
            "tooltip": "",
            "value": 0,
            "min": 0,
            "max": None,
            "multiplier": None,
            "step": None,
        }
        self.options["chunk_size"] = {
            "type": "int",
            "slider": False,
            "label": "Per-page content chunk size (max characters per chunk)",
            "description": "",
            "tooltip": "",
            "value": 100000,
            "min": None,
            "max": None,
            "multiplier": None,
            "step": None,
        }
        self.options["use_google"] = {
            "type": "bool",
            "slider": False,
            "label": "Use Google Custom Search",
            "description": "Enable Google Custom Search API (API key required)",
            "tooltip": "Google Custom Search",
            "value": True,
            "min": None,
            "max": None,
            "multiplier": None,
            "step": None,
        }
        """
        self.options["use_wikipedia"] = {
            "type": "bool",
            "slider": False,
            "label": "Use Wikipedia",
            "description": "Enable above option to use Wikipedia API (free, no API key required)",
            "tooltip": "Wikipedia API",
            "value": True,
            "min": None,
            "max": None,
            "multiplier": None,
            "step": None,
        }
        """
        self.options["disable_ssl"] = {
            "type": "bool",
            "slider": False,
            "label": "Disable SSL verify",
            "description": "Disables SSL verification when crawling web pages",
            "tooltip": "Disable SSL verify",
            "value": True,
            "min": None,
            "max": None,
            "multiplier": None,
            "step": None,
        }
        self.options["prompt_summarize"] = {
            "type": "textarea",
            "slider": False,
            "label": "Summarize prompt",
            "description": "Prompt used for summarize web search results",
            "tooltip": "Prompt",
            "value": "Summarize in English text from website into 3 paragraphs trying to find the most important "
                     "content which can help answer for question. "
                     "If there is no info about it then return only **FAILED** without any additional info: ",
            "min": None,
            "max": None,
            "multiplier": None,
            "step": None,
        }
        self.options["max_result_length"] = {
            "type": "int",
            "slider": False,
            "label": "Max result length",
            "description": "Max length of sumamrized result (characters)",
            "tooltip": "Max result length",
            "value": 1500,
            "min": 0,
            "max": None,
            "multiplier": None,
            "step": None,
        }
        self.options["summary_max_tokens"] = {
            "type": "int",
            "slider": False,
            "label": "Max summary tokens",
            "description": "Max tokens in output when generating summary",
            "tooltip": "Max tokens",
            "value": 1500,
            "min": 0,
            "max": None,
            "multiplier": None,
            "step": None,
        }
        self.options["summary_model"] = {
            "type": "text",
            "slider": False,
            "label": "Model used to summarize page",
            "description": "Model used to summarize page, default: gpt-3.5-turbo-1106",
            "tooltip": "Max tokens",
            "value": "gpt-3.5-turbo-1106",
            "min": 0,
            "max": None,
            "multiplier": None,
            "step": None,
        }
        self.input_text = None
        self.window = None
        self.websearch = WebSearch(self)
        self.allowed_cmds = ["web_search"]
        self.order = 100

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
        """Event: On user send text"""
        return text

    def on_ctx_begin(self, ctx):
        """Event: On new context begin"""
        return ctx

    def on_ctx_end(self, ctx):
        """Event: On context end"""
        return ctx

    def on_system_prompt(self, prompt):
        """Event: On prepare system prompt"""
        return prompt

    def on_ai_name(self, name):
        """Event: On set AI name"""
        return name

    def on_user_name(self, name):
        """Event: On set username"""
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

    def cmd_syntax(self, syntax):
        """Event: On cmd syntax prepare"""
        syntax += '\n"web_search": use it for search Web for more info, prepare query for search engine itself, ' \
                  'start from page 1, If you don\'t find anything or don\'t find enough information, try the next ' \
                  'page. Max pages limit: {}, params: "query", "page"'.format(self.options["num_pages"]["value"])
        return syntax

    def cmd(self, ctx, cmds):
        msg = None
        for item in cmds:
            try:
                if item["cmd"] in self.allowed_cmds:
                    if item["cmd"] == "web_search":
                        page = 1
                        if "page" in item["params"]:
                            page = int(item["params"]["page"])
                        msg = "Web search finished: '{}'".format(item["params"]["query"])
                        result, total_found, current, url = self.websearch.make_query(item["params"]["query"], page)
                        data = {
                            'content': result,
                            'url': url,
                            'page': current,
                            'total_found': total_found,
                        }
                        response = {"request": item, "result": data}
                        ctx.results.append(response)
                        ctx.reply = True
            except Exception as e:
                response = {"request": item, "result": "Error: {}".format(e)}
                ctx.results.append(response)
                ctx.reply = True
                print("Error: {}".format(e))

        if msg is not None:
            print(msg)
            self.window.statusChanged.emit(msg)
        return ctx
