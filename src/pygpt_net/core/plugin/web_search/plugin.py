#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.04.15 02:00:00                  #
# ================================================== #

from ..base_plugin import BasePlugin
from .websearch import WebSearch


class Plugin(BasePlugin):
    def __init__(self):
        super(Plugin, self).__init__()
        self.id = "web_search"
        self.name = "Web Search"
        self.description = "Allows GPT to connect with the Internet and search web pages when generating answers (experimental alpha)."
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
            "value": 1,
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
            "value": 1000,
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
            "value": 10000,
            "min": None,
            "max": None,
            "multiplier": None,
            "step": None,
        }
        self.options["use_google"] = {
            "type": "bool",
            "slider": False,
            "label": "Use Google Custom Search",
            "description": "Enable above option to use Google Custom Search API (API key required)",
            "tooltip": "Google Custom Search",
            "value": True,
            "min": None,
            "max": None,
            "multiplier": None,
            "step": None,
        }
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
        self.options["rebuild_question"] = {
            "type": "bool",
            "slider": False,
            "label": "Rebuild question to search engine",
            "description": "Enables building question to search engine from original question",
            "tooltip": "Rebuild question to search engine",
            "value": True,
            "min": None,
            "max": None,
            "multiplier": None,
            "step": None,
        }
        self.options["rebuild_question_context"] = {
            "type": "bool",
            "slider": False,
            "label": "Use context memory when rebuilding question to search engine",
            "description": "Appends also context memory when building question to search engine from original question",
            "tooltip": "Enable or disable context memory when rebuilding question to search engine",
            "value": True,
            "min": None,
            "max": None,
            "multiplier": None,
            "step": None,
        }
        self.options["disable_ssl"] = {
            "type": "bool",
            "slider": False,
            "label": "Disable SSL verify",
            "description": "Disables SSL verification when crawling web pages",
            "tooltip": "Disable SSL verify",
            "value": False,
            "min": None,
            "max": None,
            "multiplier": None,
            "step": None,
        }
        self.options["prompt_question"] = {
            "type": "textarea",
            "slider": False,
            "label": "Question build prompt",
            "description": "Prompt used for building question to search engine",
            "tooltip": "Prompt",
            "value": "Today is {time}. You are providing single best query for search in Google based on the question "
                     "and context of whole conversation and nothing more in the answer.",
            "min": None,
            "max": None,
            "multiplier": None,
            "step": None,
        }
        self.options["prompt_question_prefix"] = {
            "type": "textarea",
            "slider": False,
            "label": "Question prefix prompt",
            "description": "Prefix added to original question to build question to search engine",
            "tooltip": "Prompt",
            "value": "Prepare single query for this question and put it in <query>: ",
            "min": None,
            "max": None,
            "multiplier": None,
            "step": None,
        }
        self.options["prompt_summarize"] = {
            "type": "textarea",
            "slider": False,
            "label": "Summarize prompt",
            "description": "Prompt used for summarizing web search results",
            "tooltip": "Prompt",
            "value": "Summarize this text from website into 3 paragraphs trying to find the most "
                     "important content which will help answering for question: ",
            "min": None,
            "max": None,
            "multiplier": None,
            "step": None,
        }
        self.options["prompt_system"] = {
            "type": "textarea",
            "slider": False,
            "label": "System append prompt",
            "description": "Prompt appended to system prompt after summarize web search results",
            "tooltip": "Prompt",
            "value": " Use this summary text to answer the question or try to answer without it "
                     "if summary text do not have sufficient info: ",
            "min": None,
            "max": None,
            "multiplier": None,
            "step": None,
        }
        self.options["prompt_system_length"] = {
            "type": "int",
            "slider": False,
            "label": "System append prompt max length",
            "description": "Max length of system append prompt (characters)",
            "tooltip": "Prompt max length",
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
        self.input_text = None
        self.window = None
        self.websearch = WebSearch(self)

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
        return self.websearch.get_system_prompt(self.input_text, prompt)

    def on_ai_name(self, name):
        """Event: On set AI name"""
        return name

    def on_user_name(self, name):
        """Event: On set user name"""
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
