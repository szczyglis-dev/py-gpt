#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.06 01:00:00                  #
# ================================================== #

from __future__ import annotations
from typing import TYPE_CHECKING

import json

if TYPE_CHECKING:
    from llama_index.core.readers.base import BaseReader

from ..base import BaseLoader


class Loader(BaseLoader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = "github_repo"
        self.name = "GitHub Repository"
        self.type = ["web"]
        self.instructions = [
            {
                "github_repo": {
                    "description": "read and index GitHub repository",
                    "args": {
                        "commit_sha": {
                            "type": "str",
                            "label": 'options.commit_sha.label',
                        },
                        "branch": {
                            "type": "str",
                            "label": 'options.branch.label',
                        },
                        "owner": {
                            "type": "str",
                            "label": 'options.owner.label',
                        },
                        "repository": {
                            "type": "str",
                            "label": 'options.repository.label',
                        }
                    },
                },
            },
        ]
        self.init_args = {
            "token": "",
            "use_parser": False,
            "verbose": False,
            "concurrent_requests": 5,
            "timeout": 5,
            "retries": 0,
            "filter_dirs_include": None,  # list of directories to include
            "filter_dirs_exclude": None,  # list of directories to exclude
            "filter_file_ext_include": None,  # list of file extensions to include
            "filter_file_ext_exclude": None,  # list of file extensions to exclude
        }
        self.init_args_types = {
            "token": {'type': 'str', 'extra': {'secret': True}},
            "use_parser": {'type': 'bool', 'extra': {}},
            "verbose": {'type': 'bool', 'extra': {}},
            "concurrent_requests": {'type': 'int', 'extra': {}},
            "timeout": {'type': 'int', 'extra': {}},
            "retries": {'type': 'int', 'extra': {}},
            "filter_dirs_include": {'type': 'list', 'extra': {}},
            "filter_dirs_exclude": {'type': 'list', 'extra': {}},
            "filter_file_ext_include": {'type': 'list', 'extra': {}},
            "filter_file_ext_exclude": {'type': 'list', 'extra': {}},
        }
        self.init_args_desc = {
            "filter_dirs_include": "config.filter_dirs_include.desc",
            "filter_dirs_exclude": "config.filter_dirs_exclude.desc",
            "filter_file_ext_include": "config.filter_file_ext_include.desc",
            "filter_file_ext_exclude": "config.filter_file_ext_exclude.desc",
        }

        self.configure_locale(__file__, required_config=[],
                              required_options=['owner', 'repository'])

    def get(self) -> BaseReader:
        """
        Get reader instance

        :return: Data reader instance
        """
        from ..hub.github.repo import GithubRepositoryReader
        args = self.get_args()
        return GithubRepositoryReader(**args)

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
        if "branch" in args and args.get("branch"):
            unique["branch"] = args.get("branch")
        if "commit_sha" in args and args.get("commit_sha"):
            unique["commit_sha"] = args.get("commit_sha")
        return json.dumps(unique)

    def prepare_args(self, **kwargs) -> dict:
        """
        Prepare arguments for load_data() method

        :param kwargs: keyword arguments
        :return: args to pass to reader
        """
        args = {}

        # repository
        if "commit_sha" in kwargs and kwargs.get("commit_sha"):
            if isinstance(kwargs.get("commit_sha"), str):
                args["commit_sha"] = kwargs.get("commit_sha")  # commit sha
        if "branch" in kwargs and kwargs.get("branch"):
            if isinstance(kwargs.get("branch"), str):
                args["branch"] = kwargs.get("branch") # branch
        if "owner" in kwargs and kwargs.get("owner"):
            if isinstance(kwargs.get("owner"), str):
                args["owner"] = kwargs.get("owner")  # repo owner
        if "repository" in kwargs and kwargs.get("repository"):
            if isinstance(kwargs.get("repository"), str):
                args["repository"] = kwargs.get("repository")  # repository name
        return args
