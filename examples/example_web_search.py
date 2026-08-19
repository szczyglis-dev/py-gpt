#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# PyGPT web-search provider tutorial                 #
# Docs: https://pygpt.readthedocs.io/en/latest/      #
# Updated: 2026-08-19                                #
# ================================================== #

import json
from typing import Dict, List
from urllib.parse import quote

from pygpt_net.provider.web.base import BaseProvider


class ExampleWebSearchEngine(BaseProvider):
    """Example search-engine provider using Google Custom Search."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = "example_web_search"  # must be unique
        self.name = "Example search engine (Google)"
        self.type = ["search_engine"]

    def init_options(self):
        """Add credentials to the Web Search plugin settings."""
        self.plugin.add_option(
            "example_api_key",
            type="text",
            value="",
            label="Google Custom Search API key",
            description="API key used only by this example provider.",
            secret=True,
            persist=True,
            tab=self.id,
            urls={
                "API key": "https://developers.google.com/custom-search/v1/overview",
            },
        )
        self.plugin.add_option(
            "example_cx",
            type="text",
            value="",
            label="Google Custom Search CX ID",
            description="Programmable Search Engine identifier used by this example provider.",
            secret=True,
            persist=True,
            tab=self.id,
            urls={
                "CX ID": "https://programmablesearchengine.google.com/controlpanel/all",
            },
        )

    def search(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
    ) -> List[str]:
        """Return a list of result URLs for `query`."""
        limit = max(1, min(int(limit), 10))
        offset = max(0, int(offset))
        if limit + offset > 100:
            limit = 100 - offset
        if limit < 1:
            return []

        url = "https://www.googleapis.com/customsearch/v1"
        url += "?key=" + quote(self.get_key())
        url += "&cx=" + quote(self.get_cx())
        url += "&num=" + str(limit)
        url += "&fields=items(link)"
        url += "&start=" + str(offset)
        url += "&q=" + quote(query)

        # `get_url()` is provided by the owning Web Search plugin, so custom
        # providers do not need to create another application-level HTTP helper.
        raw = self.plugin.get_url(url)
        try:
            payload = json.loads(raw)
        except Exception:
            return []

        return [
            item["link"]
            for item in payload.get("items", [])
            if isinstance(item, dict) and item.get("link")
        ]

    def is_configured(self, cmds: List[Dict]) -> bool:
        """Require credentials only when a web command actually needs search."""
        required_commands = {"web_search", "web_urls"}
        needs_search = any(
            item.get("cmd") in required_commands
            for item in (cmds or [])
            if isinstance(item, dict)
        )
        if not needs_search:
            return True
        return bool(self.get_key() and self.get_cx())

    def get_config_message(self) -> str:
        return "Configure the example Google API key and CX ID in Web Search plugin settings."

    def get_key(self) -> str:
        return str(self.plugin.get_option_value("example_api_key") or "")

    def get_cx(self) -> str:
        return str(self.plugin.get_option_value("example_cx") or "")
