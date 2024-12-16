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

import json

from llama_index.core.readers.base import BaseReader

from llama_index.readers.twitter.base import TwitterTweetReader
from .base import BaseLoader


class Loader(BaseLoader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = "twitter"
        self.name = "Twitter posts"
        self.type = ["web"]
        self.instructions = [
            {
                "twitter": {
                    "description": "read and index user tweets from Twitter/X",
                    "args": {
                        "users": {
                            "type": "list",
                            "label": "Twitter/X usernames",
                        },
                        "max_tweets": {
                            "type": "int",
                            "label": "Max tweets",
                        },
                    },
                }
            }
        ]
        self.init_args = {
            "bearer_token" : "",
            "num_tweets": 100,
        }
        self.init_args_types = {
            "bearer_token": "str",
            "num_tweets": "int",
        }

    def get(self) -> BaseReader:
        """
        Get reader instance

        :return: Data reader instance
        """
        args = self.get_args()
        return TwitterTweetReader(**args)

    def get_external_id(self, args: dict = None) -> str:
        """
        Get unique web content identifier

        :param args: load_data args
        :return: unique content identifier
        """
        unique = {}
        if "users" in args and args.get("users"):
            unique["users"] = args.get("users")
        return json.dumps(unique)

    def prepare_args(self, **kwargs) -> dict:
        """
        Prepare arguments for load_data() method

        :param kwargs: keyword arguments
        :return: args to pass to reader
        """
        args = {}
        if "users" in kwargs and kwargs.get("users"):
            if isinstance(kwargs.get("users"), list):
                args["twitterhandles"] = kwargs.get("users")  # usernames
            elif isinstance(kwargs.get("users"), str):
                args["twitterhandles"] = self.explode(kwargs.get("users"))

        if "max_tweets" in kwargs and kwargs.get("max_tweets"):
            if isinstance(kwargs.get("max_tweets"), int):
                args["num_tweets"] = kwargs.get("max_tweets")  # max number of tweets
        return args
