#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.17 01:00:00                  #
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
                "rss": {
                    "description": "read sitemap XML from URL",
                    "args": {
                        "url": {
                            "type": "str",
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
