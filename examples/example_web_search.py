#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.23 19:00:00                  #
# ================================================== #

import json
from urllib.parse import quote
from pygpt_net.provider.web.base import BaseProvider


class ExampleWebSearchEngine(BaseProvider):
    def __init__(self, *args, **kwargs):
        """
        Example web search engine provider (Google Custom Search used as example)

        :param args: args
        :param kwargs: kwargs
        """
        super(ExampleWebSearchEngine, self).__init__(*args, **kwargs)
        self.plugin = kwargs.get("plugin")
        self.id = "example_web_search"
        self.name = "Example search engine (Google)"
        self.type = ["search_engine"]

    def init_options(self):
        """Initialize options"""
        url_api = {
            "API Key": "https://developers.google.com/custom-search/v1/overview",
        }
        url_cx = {
            "CX ID": "https://programmablesearchengine.google.com/controlpanel/all",
        }
        self.plugin.add_option(
            "google_api_key",
            type="text",
            value="",
            label="Google Custom Search API KEY",
            description="Example description #1",
            tooltip="Example tooltip #1",
            secret=True,
            persist=True,
            tab="example_web_search",
            urls=url_api,
        )
        self.plugin.add_option(
            "google_api_cx",
            type="text",
            value="",
            label="Google Custom Search CX ID",
            description="Example description #2",
            tooltip="Example tooltip #2",
            secret=True,
            persist=True,
            tab="example_web_search",
            urls=url_cx,
        )

    def search(self, query: str, limit: int = 10, offset: int = 0) -> list:
        """
        Execute search query and return list of urls

        Method must provide list of URLs for provided search query

        :param query: query
        :param limit: limit
        :param offset: offset
        :return: list of urls
        """
        key = self.get_key()
        cx = self.get_cx()

        if limit < 1:
            limit = 1
        if limit > 10:
            limit = 10

        if limit + offset > 100:
            limit = 100 - offset

        urls = []
        url = 'https://www.googleapis.com/customsearch/v1'
        url += '?key=' + str(key)
        url += '&cx=' + str(cx)
        url += '&num=' + str(limit)
        url += '&sort=date-sdate:d:s'
        url += '&fields=items(link)'
        url += '&start=' + str(offset)
        url += '&q=' + quote(query)

        data = self.plugin.get_url(url)
        res = json.loads(data)

        if 'items' not in res:
            return []
        for item in res['items']:
            urls.append(item['link'])

        return urls

    def is_configured(self, cmds: list) -> bool:
        """
        Check if provider is configured (required API keys, etc.)

        This method should check that all required config options are provided (API keys, etc.)

        :param cmds: executed commands list
        :return: True if configured, False if configuration is missing
        """
        required = ["web_search", "web_urls"]
        key = self.get_key()
        cx = self.get_cx()
        need_api_key = False
        for item in cmds:
            if item["cmd"] in required:
                need_api_key = True
                break
        if need_api_key and \
                (key is None or cx is None or key == "" or cx == ""):
            return False
        return True

    def get_config_message(self) -> str:
        """
        Return message to display when provider is not configured (no API keys, etc.)

        :return: message
        """
        return "You must define an API key in the plugin settings!"

    def get_key(self) -> str:
        """
        Return Google API key

        :return: Google API key
        """
        return str(self.plugin.get_option_value("google_api_key"))

    def get_cx(self) -> str:
        """
        Return Google API CX

        :return: Google API CX
        """
        return str(self.plugin.get_option_value("google_api_cx"))


