#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.26 12:30:00                  #
# ================================================== #

from enum import Enum
from urllib.parse import quote_plus


class CanvasSearchEngine(str, Enum):
    """Search engines available to the Canvas address bar."""

    GOOGLE = ("google", "Google", "https://www.google.com/search?q={query}")
    BING = ("bing", "Bing", "https://www.bing.com/search?q={query}")
    DUCKDUCKGO = ("duckduckgo", "DuckDuckGo", "https://duckduckgo.com/?q={query}")
    BRAVE = ("brave", "Brave Search", "https://search.brave.com/search?q={query}")
    YAHOO = ("yahoo", "Yahoo", "https://search.yahoo.com/search?p={query}")
    ECOSIA = ("ecosia", "Ecosia", "https://www.ecosia.org/search?q={query}")
    STARTPAGE = ("startpage", "Startpage", "https://www.startpage.com/sp/search?query={query}")
    QWANT = ("qwant", "Qwant", "https://www.qwant.com/?q={query}")

    def __new__(cls, value: str, label: str, url_template: str):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.label = label
        obj.url_template = url_template
        return obj

    @classmethod
    def from_value(cls, value) -> "CanvasSearchEngine":
        try:
            return cls(str(value or "").strip().lower())
        except ValueError:
            return cls.GOOGLE

    @classmethod
    def combo_keys(cls) -> list:
        """Return plugin combo entries in the format expected by config widgets."""
        return [{engine.value: engine.label} for engine in cls]

    def build_url(self, query: str) -> str:
        return self.url_template.format(query=quote_plus(str(query or "").strip()))
