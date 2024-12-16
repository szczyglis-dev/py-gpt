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

from .hub.database.base import DatabaseReader
from .base import BaseLoader


class Loader(BaseLoader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = "db"
        self.name = "SQL Database"
        self.type = ["web"]
        self.instructions = [
            {
                "db": {
                    "description": "read and index files from connected SQL database",
                    "args": {
                        "query": {
                            "type": "str",
                            "label": "SQL query",
                            "description": "SQL query to read data from database, e.g. SELECT * FROM table",
                        },
                    },
                }
            }
        ]
        self.init_args = {
            # "sql_database": None,
            # "engine": None,
            "uri": None,
            "scheme": None,
            "host": None,
            "port": None,
            "user": None,
            "password": None,
            "dbname": None,
        }
        self.init_args_types = {
            # "sql_database": "str",
            # "engine": "str",
            "uri": "str",
            "scheme": "str",
            "host": "str",
            "port": "int",
            "user": "str",
            "password": "str",
            "dbname": "str",
        }
        self.init_args_desc = {
            # "sql_database": "str",
            # "engine": "str",
            "uri": "You can provide a single URI in the form of: {scheme}://{user}:{password}@{host}:{port}/{dbname}, "
                   "or you can provide each field manually:",
        }

    def get(self) -> BaseReader:
        """
        Get reader instance

        :return: Data reader instance
        """
        args = self.get_args()
        return DatabaseReader(**args)

    def get_external_id(self, args: dict = None) -> str:
        """
        Get unique web content identifier

        :param args: load_data args
        :return: unique content identifier
        """
        unique = {}
        if "dbname" in args and args.get("dbname"):
            unique["dbname"] = args.get("dbname")
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
                args["query"] = kwargs.get("query")  # query
        return args
