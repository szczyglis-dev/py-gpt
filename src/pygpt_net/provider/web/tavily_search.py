#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.03.30 00:00:00                  #
# ================================================== #

from typing import List, Dict

from .base import BaseProvider


class TavilySearch(BaseProvider):
    def __init__(self, *args, **kwargs):
        """
        Tavily Search provider

        :param args: args
        :param kwargs: kwargs
        """
        super(TavilySearch, self).__init__(*args, **kwargs)
        self.plugin = kwargs.get("plugin")
        self.id = "tavily_search"
        self.name = "Tavily"
        self.type = ["search_engine"]

    def init_options(self):
        """Initialize options"""
        url_api = {
            "API Key": "https://app.tavily.com",
        }
        self.plugin.add_option(
            "tavily_api_key",
            type="text",
            value="",
            label="Tavily API Key",
            description="You can obtain your own API key at "
                        "https://app.tavily.com",
            tooltip="Tavily API Key",
            secret=True,
            persist=True,
            tab="tavily_search",
            urls=url_api,
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
        TavilyClient = self._load_tavily()
        if TavilyClient is None:
            print("tavily-python package not installed.")
            return []

        api_key = self.get_api_key()
        if not api_key:
            print("Tavily API key is not set.")
            return []

        if limit < 1:
            limit = 1
        if limit > 20:
            limit = 20

        urls = []
        try:
            client = TavilyClient(api_key=api_key)
            # Request enough results to satisfy offset + limit, then slice
            target = limit + offset
            if target > 20:
                target = 20
            response = client.search(
                query=query,
                max_results=target,
                search_depth="basic",
            )
            collected = []
            for result in response.get("results", []):
                url = result.get("url")
                if url:
                    collected.append(url)

            if offset > 0:
                collected = collected[offset:offset + limit]
            else:
                collected = collected[:limit]

            # De-dup and keep order
            seen = set()
            for u in collected:
                if u not in seen:
                    urls.append(u)
                    seen.add(u)

        except Exception as e:
            print(e)

        return urls

    def is_configured(self, cmds: List[Dict]) -> bool:
        """
        Check if provider is configured (required API keys, etc.)

        :param cmds: executed commands list
        :return: True if configured, False if configuration is missing
        """
        required = ["web_search", "web_urls"]
        need_api_key = False
        for item in cmds:
            if item["cmd"] in required:
                need_api_key = True
                break
        if need_api_key:
            api_key = self.get_api_key()
            if not api_key:
                return False
        return True

    def get_config_message(self) -> str:
        """
        Return message to display when provider is not configured

        :return: message
        """
        return (
            "Tavily API key is not set. Please set your API key in plugin settings. "
            "You can obtain one at https://app.tavily.com"
        )

    def get_api_key(self) -> str:
        """
        Return Tavily API key

        :return: Tavily API key
        """
        return str(self.plugin.get_option_value("tavily_api_key"))

    @staticmethod
    def _load_tavily():
        """
        Try to import TavilyClient from tavily-python package.
        """
        try:
            from tavily import TavilyClient  # type: ignore
            return TavilyClient
        except Exception:
            return None
