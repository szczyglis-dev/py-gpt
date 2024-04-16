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

from .hub.chatgpt_retrieval.base import ChatGPTRetrievalPluginReader
from .base import BaseLoader


class Loader(BaseLoader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = "chatgpt_retrieval"
        self.name = "ChatGPT Retrieval Plugin"
        self.type = ["web"]
        self.instructions = [
            {
                "chatgpt_retrieval": {
                    "description": "read and index data from ChatGPT Retrieval Plugin",
                    "args": {
                        "query": {
                            "type": "str",
                        },
                    },
                }
            }
        ]
        self.init_args = {
            "endpoint_url": None,
            "bearer_token": None,
            "retries": None,
            "batch_size": 100,
        }
        self.init_args_types = {
            "endpoint_url": "str",
            "bearer_token": "str",
            "retries": "int",
            "batch_size": "int",
        }

    def get(self) -> BaseReader:
        """
        Get reader instance

        :return: Data reader instance
        """
        args = self.get_args()
        return ChatGPTRetrievalPluginReader(**args)

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

        # query
        if "query" in kwargs and kwargs.get("query"):
            if isinstance(kwargs.get("query"), str):
                args["query"] = kwargs.get("query")  # query

        return args
