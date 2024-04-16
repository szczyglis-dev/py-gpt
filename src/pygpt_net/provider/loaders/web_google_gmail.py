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

import json

from llama_index.core.readers.base import BaseReader

from .hub.google.gmail import GmailReader
from .base import BaseLoader


class Loader(BaseLoader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = "google_gmail"
        self.name = "Google Gmail"
        self.type = ["web"]
        self.instructions = [
            {
                "google_gmail": {
                    "description": "read and index emails from Google Gmail",
                    "args": {
                        "query": {
                            "type": "str",
                        },
                    },
                }
            }
        ]
        self.init_args = {
            "credentials_path": "credentials.json",
            "token_path": "token.json",
            "use_iterative_parser": False,
            "max_results": 10,
            "service": None,
            "results_per_page": None,
        }
        self.init_args_types = {
            "credentials_path": "str",
            "token_path": "str",
            "use_iterative_parser": "bool",
            "max_results": "int",
            "service": "str",
            "results_per_page": "int",
        }

    def get(self) -> BaseReader:
        """
        Get reader instance

        :return: Data reader instance
        """
        args = self.get_args()
        return GmailReader(**args)

    def get_external_id(self, args: dict = None) -> str:
        """
        Get unique web content identifier

        :param args: load_data args
        :return: unique content identifier
        """
        unique = {}
        if "query" in args and args.get("query"):
            unique["query"] = args.get("query")
        return json.dumps(unique)

    def prepare_args(self, **kwargs) -> dict:
        """
        Prepare arguments for load_data() method

        :param kwargs: keyword arguments
        :return: args to pass to reader
        """
        args = {}
        if "query" in kwargs and kwargs.get("query"):
            if isinstance(kwargs.get("query"), str):
                args["query"] = kwargs.get("query")  # query, e.g. "from:me after:2023-01-01"
        return args
