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

import requests

from .base import BaseProvider


class MicrosoftBingSearch(BaseProvider):
    def __init__(self, *args, **kwargs):
        """
        Google Custom Search provider

        :param args: args
        :param kwargs: kwargs
        """
        super(MicrosoftBingSearch, self).__init__(*args, **kwargs)
        self.plugin = kwargs.get("plugin")
        self.id = "microsoft_bing"
        self.name = "Bing"
        self.type = ["search_engine"]

    def init_options(self):
        """Initialize options"""
        url_api = {
            "API Key": "https://www.microsoft.com/en-us/bing/apis/bing-web-search-api",
        }
        self.plugin.add_option(
            "bing_api_key",
            type="text",
            value="",
            label="Bing Search API KEY",
            description="You can obtain your own API key at "
                        "https://www.microsoft.com/en-us/bing/apis/bing-web-search-api",
            tooltip="Bing Search API KEY",
            secret=True,
            persist=True,
            tab="microsoft_bing",
            urls=url_api,
        )
        self.plugin.add_option(
            "bing_endpoint",
            type="text",
            value="https://api.bing.microsoft.com/v7.0/search",
            label="Bing Search API endpoint",
            description="API endpoint for Bing Search API",
            tooltip="Bing Search API endpoint",
            persist=False,
            tab="microsoft_bing",
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
        urls = []

        if limit < 1:
            limit = 1
        if limit > 10:
            limit = 10

        if limit + offset > 100:
            limit = 100 - offset

        headers = {
            'Ocp-Apim-Subscription-Key': key,
        }
        endpoint = self.plugin.get_option_value("bing_endpoint")
        url = f"{endpoint}?q={quote(query)}&count={limit}&offset={offset}&mkt=en-US"
        response = requests.get(
            url,
            headers=headers,
        )
        if response.status_code == 200:
            data = response.json()
            for result in data['webPages']['value']:
                urls.append(result['url'])
        else:
            print('Error:', response.status_code, response.text)
        return urls

    def is_configured(self, cmds: List[Dict]) -> bool:
        """
        Check if provider is configured (required API keys, etc.)

        :param cmds: executed commands list
        :return: True if configured, False if configuration is missing
        """
        required = ["web_search", "web_urls"]
        key = self.get_key()
        need_api_key = False
        for item in cmds:
            if item["cmd"] in required:
                need_api_key = True
                break
        if need_api_key and (key is None or key == ""):
            return False
        return True

    def get_config_message(self) -> str:
        """
        Return message to display when provider is not configured

        :return: message
        """
        return "Microsoft Bing Search API key is not set. Please set credentials in plugin settings."

    def get_key(self) -> str:
        """
        Return Google API key

        :return: Google API key
        """
        return str(self.plugin.get_option_value("bing_api_key"))


