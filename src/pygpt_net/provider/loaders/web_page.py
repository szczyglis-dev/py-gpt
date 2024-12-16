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

from .hub.web_page.base import WebPage
from .base import BaseLoader


class Loader(BaseLoader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = "webpage"
        self.name = "Webpage"
        self.type = ["web"]
        self.instructions = [
            {
                "webpage": {
                    "description": "index provided standard webpage URL",
                    "args": {
                        "url": {
                            "type": "str",
                            "label": "URL",
                            "description": "URL of the webpage to index, e.g. https://www.example.com",
                        },
                    },
                }
            }
        ]

    def get(self) -> BaseReader:
        """
        Get reader instance

        :return: Data reader instance
        """
        return WebPage()

    def prepare_args(self, **kwargs) -> dict:
        """
        Prepare arguments for reader

        :param kwargs: keyword arguments
        :return: args to pass to reader
        """
        args = {}
        args["url"] = kwargs.get("url")
        return args
