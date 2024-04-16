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

from .hub.bitbucket.repo import BitbucketReader
from .base import BaseLoader


class Loader(BaseLoader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = "bitbucket_repo"
        self.name = "Bitbucket Repository"
        self.type = ["web"]
        self.instructions = [
            {
                "bitbucket_repo": {
                    "description": "read and index BitBucket repository",
                    "args": {
                        "base_url": {
                            "type": "str",
                        },
                        "project_key": {
                            "type": "str",
                        },
                        "branch": {
                            "type": "str",
                        },
                        "repository": {
                            "type": "str",
                        },
                    },
                }
            }
        ]
        self.init_args = {
            "username": None,
            "api_key": None,
            "extensions_to_skip": [],
        }
        self.init_args_types = {
            "username": "str",
            "api_key": "str",
            "extensions_to_skip": "list",
        }

    def get(self) -> BaseReader:
        """
        Get reader instance

        :return: Data reader instance
        """
        args = self.get_args()
        return BitbucketReader(**args)

    def get_external_id(self, args: dict = None) -> str:
        """
        Get unique web content identifier

        :param args: load_data args
        :return: unique content identifier
        """
        unique = {}
        if "base_url" in args and args.get("base_url"):
            unique["base_url"] = args.get("base_url")
        if "repository" in args and args.get("repository"):
            unique["repository"] = args.get("repository")
        if "branch" in args and args.get("branch"):
            unique["branch"] = args.get("branch")
        return json.dumps(unique)

    def prepare_args(self, **kwargs) -> dict:
        """
        Prepare arguments for load_data() method

        :param kwargs: keyword arguments
        :return: args to pass to reader
        """
        args = {}

        # repository
        if "base_url" in kwargs and kwargs.get("base_url"):
            if isinstance(kwargs.get("base_url"), str):
                args["base_url"] = kwargs.get("base_url")  # base_url
        if "project_key" in kwargs and kwargs.get("project_key"):
            if isinstance(kwargs.get("project_key"), str):
                args["project_key"] = kwargs.get("project_key")  # project_key
        if "branch" in kwargs and kwargs.get("branch"):
            if isinstance(kwargs.get("branch"), str):
                args["branch"] = kwargs.get("branch") # branch
        if "repository" in kwargs and kwargs.get("repository"):
            if isinstance(kwargs.get("repository"), str):
                args["repository"] = kwargs.get("repository")  # repository name

        return args
