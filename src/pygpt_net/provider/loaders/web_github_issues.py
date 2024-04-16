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

from .hub.github.issues import GitHubRepositoryIssuesReader
from .base import BaseLoader


class Loader(BaseLoader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = "github_issues"
        self.name = "GitHub Issues"
        self.type = ["web"]
        self.instructions = [
            {
                "github_issues": {
                    "description": "read and index GitHub issues",
                    "args": {
                        "owner": {
                            "type": "str",
                        },
                        "repository": {
                            "type": "str",
                        },
                        "state": {
                            "type": "enum",
                            "options": ["open", "closed", "all"],
                        },
                        "label_filters_include": {
                            "type": "list",
                        },
                        "label_filters_exclude": {
                            "type": "list",
                        },
                    },
                }
            }
        ]
        self.init_args = {
            "token": "",
            "verbose": False,
        }
        self.init_args_types = {
            "token": "str",
            "verbose": "bool",
        }

    def get(self) -> BaseReader:
        """
        Get reader instance

        :return: Data reader instance
        """
        args = self.get_args()
        return GitHubRepositoryIssuesReader(**args)

    def get_external_id(self, args: dict = None) -> str:
        """
        Get unique web content identifier

        :param args: load_data args
        :return: unique content identifier
        """
        unique = {}
        if "owner" in args and args.get("owner"):
            unique["owner"] = args.get("owner")
        if "repository" in args and args.get("repository"):
            unique["repository"] = args.get("repository")
        if "state" in args and args.get("state"):
            unique["state"] = args.get("state")
        return json.dumps(unique)

    def prepare_args(self, **kwargs) -> dict:
        """
        Prepare arguments for load_data() method

        :param kwargs: keyword arguments
        :return: args to pass to reader
        """
        args = {}

        # repository
        if "owner" in kwargs and kwargs.get("owner"):
            if isinstance(kwargs.get("owner"), str):
                args["owner"] = kwargs.get("owner")  # repo owner
        if "repository" in kwargs and kwargs.get("repository"):
            if isinstance(kwargs.get("repository"), str):
                args["repository"] = kwargs.get("repository")  # repo name

        # filters
        if "label_filters_include" in kwargs and kwargs.get("label_filters_include"):
            if isinstance(kwargs.get("label_filters_include"), list):
                args["label_filters_include"] = kwargs.get("label_filters_include")
        if "label_filters_exclude" in kwargs and kwargs.get("label_filters_exclude"):
            if isinstance(kwargs.get("label_filters_exclude"), list):
                args["label_filters_exclude"] = kwargs.get("label_filters_exclude")

        return args
