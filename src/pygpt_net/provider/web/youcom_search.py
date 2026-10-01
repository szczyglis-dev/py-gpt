#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.05 18:00:00                  #
# ================================================== #

import json
from typing import List, Dict

import requests

from .base import BaseProvider


class YouComSearch(BaseProvider):
    # default keyless endpoint, used when the endpoint option is not set
    DEFAULT_ENDPOINT = "https://api.you.com/mcp?profile=free"

    def __init__(self, *args, **kwargs):
        """
        You.com Search provider

        :param args: args
        :param kwargs: kwargs
        """
        super(YouComSearch, self).__init__(*args, **kwargs)
        self.plugin = kwargs.get("plugin")
        self.id = "youcom_search"
        self.name = "You.com"
        self.type = ["search_engine"]

    def init_options(self):
        """Initialize options"""
        url_api = {
            "API Key": "https://you.com/platform/api-keys",
        }
        self.plugin.add_option(
            "youcom_api_key",
            type="text",
            value="",
            label="You.com API KEY",
            description="Optional. You can obtain your own API key at "
                        "https://you.com/platform/api-keys - if left empty, the keyless endpoint is used",
            tooltip="You.com API KEY",
            secret=True,
            persist=True,
            tab="youcom_search",
            urls=url_api,
        )
        self.plugin.add_option(
            "youcom_endpoint",
            type="text",
            value="https://api.you.com/mcp?profile=free",
            label="You.com MCP endpoint",
            description="You.com MCP endpoint, default: https://api.you.com/mcp?profile=free (keyless); "
                        "use https://api.you.com/mcp with an API key",
            tooltip="You.com MCP endpoint",
            persist=False,
            tab="youcom_search",
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
        urls = []

        if limit < 1:
            limit = 1
        if limit > 10:
            limit = 10

        if limit + offset > 100:
            limit = 100 - offset

        try:
            # fetch enough results to cover the requested offset + limit
            target = limit + offset
            collected = self._fetch(query, target)
            if offset > 0:
                collected = collected[offset:offset + limit]
            else:
                collected = collected[:limit]

            # de-dup and keep order
            seen = set()
            for u in collected:
                if u and u not in seen:
                    urls.append(u)
                    seen.add(u)

        except Exception as e:
            # fail safe: never raise to the app layer
            print(e)

        return urls

    def _fetch(self, query: str, count: int) -> List[str]:
        """
        Call You.com MCP server (you-search tool) and return list of urls

        :param query: query
        :param count: number of results to fetch
        :return: list of urls
        """
        endpoint = str(self.plugin.get_option_value("youcom_endpoint") or self.DEFAULT_ENDPOINT)
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "you-search",
                "arguments": {
                    "query": query,
                },
            },
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        key = self.get_key()
        if key:
            # authenticated endpoint takes precedence over the keyless one
            headers["Authorization"] = "Bearer " + key
        response = requests.post(
            endpoint,
            json=payload,
            headers=headers,
            timeout=30,
        )
        if response.status_code != 200:
            print('You.com search error:', response.status_code, response.text)
            return []

        # the endpoint answers with SSE stream (text/event-stream) or plain JSON
        data = self._parse_response(response)
        results = data.get("results", {})
        urls: List[str] = []
        for item in results.get("web", []):
            url = item.get("url")
            if url:
                urls.append(url)
            if len(urls) >= count:
                break
        return urls

    def _parse_response(self, response) -> dict:
        """
        Parse MCP response and return the result data dict

        :param response: HTTP response
        :return: result data dict
        """
        content_type = response.headers.get("Content-Type", "")
        body = response.text
        if "text/event-stream" in content_type:
            # take the last data line that holds the JSON-RPC result
            for line in reversed(body.splitlines()):
                line = line.strip()
                if line.startswith("data:"):
                    body = line[len("data:"):].strip()
                    break
        envelope = json.loads(body)
        if "error" in envelope and envelope["error"] is not None:
            print('You.com search error:', envelope["error"])
            return {}
        result = envelope.get("result", {})
        for item in result.get("content", []):
            if item.get("type") == "text":
                try:
                    return json.loads(item.get("text", "{}"))
                except (ValueError, TypeError):
                    return {}
        return {}

    def is_configured(self, cmds: List[Dict]) -> bool:
        """
        Check if provider is configured (required API keys, etc.)

        :param cmds: executed commands list
        :return: True if configured, False if configuration is missing
        """
        # the default (keyless) endpoint requires no API key
        endpoint = str(self.plugin.get_option_value("youcom_endpoint") or self.DEFAULT_ENDPOINT)
        if "profile=free" in endpoint:
            return True
        key = self.get_key()
        return key is not None and key != ""

    def get_config_message(self) -> str:
        """
        Return message to display when provider is not configured

        :return: message
        """
        return ("You.com API key is not set. Please set the API key in plugin settings "
                "or switch the endpoint back to the keyless https://api.you.com/mcp?profile=free")

    def get_key(self) -> str:
        """
        Return You.com API key

        :return: You.com API key
        """
        key = self.plugin.get_option_value("youcom_api_key")
        if key is None or str(key) == "":
            import os
            key = os.environ.get("YDC_API_KEY", "")
        return str(key)
