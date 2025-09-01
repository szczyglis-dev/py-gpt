#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.02 01:00:00                  #
# ================================================== #

from typing import List, Dict

from .base import BaseProvider


class DuckDuckGoSearch(BaseProvider):
    def __init__(self, *args, **kwargs):
        """
        DuckDuckGo Search provider

        :param args: args
        :param kwargs: kwargs
        """
        super(DuckDuckGoSearch, self).__init__(*args, **kwargs)
        self.plugin = kwargs.get("plugin")
        self.id = "duckduckgo_search"
        self.name = "DuckDuckGo"
        self.type = ["search_engine"]

    def init_options(self):
        """Initialize options"""
        url_params = {
            "URL parameters": "https://duckduckgo.com/duckduckgo-help-pages/settings/params/",
        }
        url_pkg = {
            "ddgs": "https://pypi.org/project/ddgs/",
        }

        # Region (kl), e.g. us-en, pl-pl, wt-wt (no region)
        self.plugin.add_option(
            "ddg_region",
            type="text",
            value="us-en",
            label="Region (kl)",
            description="DuckDuckGo region, e.g. us-en, pl-pl, wt-wt.",
            tooltip="DuckDuckGo region (kl)",
            persist=True,
            tab="duckduckgo_search",
            urls=url_params,
        )
        # SafeSearch: on | moderate | off
        self.plugin.add_option(
            "ddg_safesearch",
            type="text",
            value="off",
            label="SafeSearch",
            description="Allowed values: on, moderate, off.",
            tooltip="DuckDuckGo SafeSearch",
            persist=True,
            tab="duckduckgo_search",
            urls=url_params,
        )
        # Time limit: d (day), w (week), m (month), y (year), or empty for any time
        self.plugin.add_option(
            "ddg_timelimit",
            type="text",
            value="",
            label="Time limit (df)",
            description="Use: d, w, m, y or leave empty for any time.",
            tooltip="DuckDuckGo time filter",
            tab="duckduckgo_search",
            urls=url_params,
        )
        # Backend selection: auto | html | lite (defaults to html for stability)
        self.plugin.add_option(
            "ddg_backend",
            type="text",
            value="html",
            label="Backend",
            description="Engine backend: auto, html, lite.",
            tooltip="DDG backend",
            persist=True,
            tab="duckduckgo_search",
            urls=url_pkg,
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
        DDGS = self._load_ddgs()
        if DDGS is None:
            print("duckduckgo-search (or ddgs) package not installed.")
            return []

        # Normalize limits to align with other providers
        if limit < 1:
            limit = 1
        if limit > 10:
            limit = 10
        if limit + offset > 100:
            limit = 100 - offset
            if limit < 1:
                return []

        region = str(self.plugin.get_option_value("ddg_region") or "us-en")
        safesearch = str(self.plugin.get_option_value("ddg_safesearch") or "moderate").lower()
        timelimit = str(self.plugin.get_option_value("ddg_timelimit") or "").lower() or None
        backend = str(self.plugin.get_option_value("ddg_backend") or "html").lower()

        urls: List[str] = []
        try:
            # Using a context manager to ensure proper session cleanup
            with DDGS() as ddgs:
                # Request enough results to satisfy offset + limit, then slice
                target = limit + offset
                results_iter = ddgs.text(
                    query,
                    region=region,
                    safesearch=safesearch,
                    timelimit=timelimit,
                    backend=backend,
                    max_results=target,
                )

                # The library may return a generator or a list; handle both
                collected = []
                for r in results_iter or []:
                    # r keys typically: title, href, body
                    href = r.get("href") or r.get("url")
                    if href:
                        collected.append(href)
                    if len(collected) >= target:
                        break

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
            # Fail safe: never raise to the app layer
            print(e)

        return urls

    def is_configured(self, cmds: List[Dict]) -> bool:
        """
        Check if provider is configured (required API keys, etc.)

        :param cmds: executed commands list
        :return: True if configured, False if configuration is missing
        """
        required = ["web_search", "web_urls"]
        need_backend = False
        for item in cmds:
            if item["cmd"] in required:
                need_backend = True
                break

        if not need_backend:
            return True

        # Package presence is the only requirement (no API keys needed)
        if self._load_ddgs() is None:
            return False

        return True

    def get_config_message(self) -> str:
        """
        Return message to display when provider is not configured

        :return: message
        """
        return (
            "DuckDuckGo provider requires the 'duckduckgo-search' (or 'ddgs') Python package. "
            "Install with: pip install -U duckduckgo-search"
        )

    @staticmethod
    def _load_ddgs():
        """
        Try to import DDGS from available packages (duckduckgo-search preferred).
        """
        try:
            from duckduckgo_search import DDGS  # type: ignore
            return DDGS
        except Exception:
            try:
                from ddgs import DDGS  # type: ignore
                return DDGS
            except Exception:
                return None