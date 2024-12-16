#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.16 01:00:00                  #
# ================================================== #

from llama_index.core.readers.base import BaseReader
from llama_index.readers.web.sitemap.base import SitemapReader

from .base import BaseLoader


class Loader(BaseLoader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = "sitemap"
        self.name = "Sitemap"
        self.type = ["web"]
        self.instructions = [
            {
                "sitemap": {
                    "description": "read all web pages from sitemap.xml",
                    "args": {
                        "url": {
                            "type": "str",
                            "label": "URL",
                            "description": "URL to sitemap XML, e.g. https://example.com/sitemap.xml, all pages will be read",
                        },
                    },
                }
            }
        ]
        self.init_args = {
            "html_to_text": False,
            "limit": 10,
        }
        self.init_args_types = {
            "html_to_text": "bool",
            "limit": "int",
        }
        self.init_args_desc = {
            "html_to_text": "Whether to convert HTML to text",
            "limit": "Maximum number of concurrent requests",
        }

    def get(self) -> BaseReader:
        """
        Get reader instance

        :return: Data reader instance
        """
        args = self.get_args()
        return SitemapReader(**args)

    def prepare_args(self, **kwargs) -> dict:
        """
        Prepare arguments for reader

        :param kwargs: keyword arguments
        :return: args to pass to reader
        """
        args = {}
        args["sitemap_url"] = kwargs.get("url")  # list of links
        return args
