#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.27 20:18:26                  #
# ================================================== #

from pygpt_net.plugin.base.config import BaseConfig, BasePlugin


class Config(BaseConfig):
    def __init__(self, plugin: BasePlugin = None, *args, **kwargs):
        super(Config, self).__init__(plugin)
        self.plugin = plugin

    def from_defaults(self, plugin: BasePlugin = None):
        # Settings
        plugin.add_option(
            "lang",
            type="text",
            value="en",
            label="Language",
            description="Default Wikipedia language (e.g., en, pl, de).",
        )
        plugin.add_option(
            "auto_suggest",
            type="bool",
            value=True,
            label="Auto suggest",
            description="Use Wikipedia auto_suggest when resolving titles.",
        )
        plugin.add_option(
            "redirect",
            type="bool",
            value=True,
            label="Follow redirects",
            description="Follow redirects when resolving pages.",
        )
        plugin.add_option(
            "rate_limit",
            type="bool",
            value=True,
            label="Rate limit",
            description="Enable built-in wikipedia rate limiting.",
        )
        plugin.add_option(
            "user_agent",
            type="text",
            value="pygpt-net-wikipedia-plugin/1.0 (+https://pygpt.net)",
            label="User-Agent",
            description="Custom User-Agent for requests.",
        )
        plugin.add_option(
            "summary_sentences",
            type="int",
            value=3,
            label="Summary sentences",
            description="Default number of sentences returned by wp_summary.",
        )
        plugin.add_option(
            "results_default",
            type="int",
            value=10,
            label="Default results limit",
            description="Default number of results for searches and geosearch.",
        )
        plugin.add_option(
            "content_max_chars",
            type="int",
            value=5000,
            label="Content max chars",
            description="Max characters returned for page content when clipping.",
        )
        plugin.add_option(
            "max_list_items",
            type="int",
            value=50,
            label="Max list items",
            description="Max items from lists like links, images, etc.",
        )
        plugin.add_option(
            "content_full_default",
            type="bool",
            value=False,
            label="Full content by default",
            description="Return un-clipped article/section content unless overridden by command param.",
        )

        # ---------------- Commands ----------------

        # Language
        plugin.add_cmd(
            "wp_set_lang",
            instruction="Set Wikipedia language (MediaWiki code).",
            params=[{"name": "lang", "type": "str", "required": True, "description": "e.g., en, pl, de"}],
            enabled=True,
            description="Lang: set",
            tab="lang",
        )
        plugin.add_cmd(
            "wp_get_lang",
            instruction="Get current Wikipedia language.",
            params=[],
            enabled=True,
            description="Lang: get",
            tab="lang",
        )
        plugin.add_cmd(
            "wp_languages",
            instruction="Get list of supported languages.",
            params=[{"name": "short", "type": "bool", "required": False, "description": "Return only codes"}],
            enabled=True,
            description="Lang: list",
            tab="lang",
        )

        # Search / Suggest
        plugin.add_cmd(
            "wp_search",
            instruction="Search Wikipedia by query.",
            params=[
                {"name": "q", "type": "str", "required": True, "description": "Query string"},
                {"name": "results", "type": "int", "required": False, "description": "Results limit"},
                {"name": "suggestion", "type": "bool", "required": False, "description": "Return suggestion as well"},
            ],
            enabled=True,
            description="Search: query",
            tab="search",
        )
        plugin.add_cmd(
            "wp_suggest",
            instruction="Get suggestion for a query.",
            params=[{"name": "q", "type": "str", "required": True, "description": "Query string"}],
            enabled=True,
            description="Search: suggest",
            tab="search",
        )

        # Read
        plugin.add_cmd(
            "wp_summary",
            instruction="Get article summary.",
            params=[
                {"name": "title", "type": "str", "required": False, "description": "Article title (or use 'q')"},
                {"name": "q", "type": "str", "required": False, "description": "Alias of title"},
                {"name": "sentences", "type": "int", "required": False, "description": "Number of sentences"},
                {"name": "auto_suggest", "type": "bool", "required": False, "description": "Use auto suggest"},
                {"name": "redirect", "type": "bool", "required": False, "description": "Follow redirects"},
            ],
            enabled=True,
            description="Read: summary",
            tab="page",
        )
        plugin.add_cmd(
            "wp_page",
            instruction="Get page details (content and lists).",
            params=[
                {"name": "title", "type": "str", "required": True, "description": "Article title"},
                {"name": "include", "type": "list", "required": False, "description": "Fields to include"},
                {"name": "content_chars", "type": "int", "required": False, "description": "Limit content length (ignored if full=true)"},
                {"name": "max_list_items", "type": "int", "required": False, "description": "Limit list items"},
                {"name": "auto_suggest", "type": "bool", "required": False, "description": "Use auto suggest"},
                {"name": "redirect", "type": "bool", "required": False, "description": "Follow redirects"},
                {"name": "open", "type": "bool", "required": False, "description": "Open in browser"},
                {"name": "full", "type": "bool", "required": False, "description": "Return full content (no clipping)"},
            ],
            enabled=True,
            description="Read: page",
            tab="page",
        )
        plugin.add_cmd(
            "wp_section",
            instruction="Get content of a specific section.",
            params=[
                {"name": "title", "type": "str", "required": True, "description": "Article title"},
                {"name": "section", "type": "str", "required": True, "description": "Section title"},
                {"name": "content_chars", "type": "int", "required": False, "description": "Limit content length (ignored if full=true)"},
                {"name": "auto_suggest", "type": "bool", "required": False, "description": "Use auto suggest"},
                {"name": "redirect", "type": "bool", "required": False, "description": "Follow redirects"},
                {"name": "full", "type": "bool", "required": False, "description": "Return full content (no clipping)"},
            ],
            enabled=True,
            description="Read: section",
            tab="page",
        )

        # Discover
        plugin.add_cmd(
            "wp_random",
            instruction="Get random article titles.",
            params=[{"name": "results", "type": "int", "required": False, "description": "How many"}],
            enabled=True,
            description="Discover: random",
            tab="discover",
        )
        plugin.add_cmd(
            "wp_geosearch",
            instruction="Find pages near coordinates.",
            params=[
                {"name": "lat", "type": "float", "required": True, "description": "Latitude"},
                {"name": "lon", "type": "float", "required": True, "description": "Longitude"},
                {"name": "radius", "type": "int", "required": False, "description": "Radius in meters"},
                {"name": "results", "type": "int", "required": False, "description": "Results limit"},
                {"name": "title", "type": "str", "required": False, "description": "Optional search bias title"},
            ],
            enabled=True,
            description="Discover: geosearch",
            tab="discover",
        )

        # Utilities
        plugin.add_cmd(
            "wp_open",
            instruction="Open article in browser by title or URL.",
            params=[
                {"name": "title", "type": "str", "required": False, "description": "Article title"},
                {"name": "url", "type": "str", "required": False, "description": "Direct URL"},
                {"name": "auto_suggest", "type": "bool", "required": False, "description": "Use auto suggest"},
                {"name": "redirect", "type": "bool", "required": False, "description": "Follow redirects"},
            ],
            enabled=True,
            description="Utils: open in browser",
            tab="utils",
        )