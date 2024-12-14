#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 22:00:00                  #
# ================================================== #

import json
from typing import List, Dict
from urllib.parse import quote
from .base import BaseProvider


class GoogleCustomSearch(BaseProvider):
    def __init__(self, *args, **kwargs):
        """
        Google Custom Search provider

        :param args: args
        :param kwargs: kwargs
        """
        super(GoogleCustomSearch, self).__init__(*args, **kwargs)
        self.plugin = kwargs.get("plugin")
        self.id = "google_custom_search"
        self.name = "Google"
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
            description="You can obtain your own API key at "
                        "https://developers.google.com/custom-search/v1/overview",
            tooltip="Google Custom Search API KEY",
            secret=True,
            persist=True,
            tab="google_custom_search",
            urls=url_api,
        )
        self.plugin.add_option(
            "google_api_cx",
            type="text",
            value="",
            label="Google Custom Search CX ID",
            description="You will find your CX ID at https://programmablesearchengine.google.com/controlpanel/all\n"
                        "Remember to enable \"Search on ALL internet pages\" option in project settings.",
            tooltip="Google Custom Search CX ID",
            secret=True,
            persist=True,
            tab="google_custom_search",
            urls=url_cx,
        )

    def search(
            self,
            query: str,
            limit: int = 10,
            offset: int = 0
    ) -> List[str]:
        """
        Execute search query and return list of urls

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

    def is_configured(self, cmds: List[Dict]) -> bool:
        """
        Check if provider is configured (required API keys, etc.)

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
        Return message to display when provider is not configured

        :return: message
        """
        return "Google Custom Search API key or Google Search CX is not set. Please set credentials in plugin settings."

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


