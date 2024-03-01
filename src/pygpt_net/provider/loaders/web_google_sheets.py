#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.01 02:00:00                  #
# ================================================== #

import json

from llama_index.core.readers.base import BaseReader

from .hub.google.sheets import GoogleSheetsReader
from .base import BaseLoader


class Loader(BaseLoader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = "google_sheets"
        self.name = "Google Sheets"
        self.type = ["web"]
        self.instructions = [
            {
                "google_sheets": "use it to read and index spreadsheets from Google Sheets, "
                                "allowed additional args: `spreadsheet_ids`: list",
            }
        ]
        self.init_args = {
            "credentials_path": "credentials.json",
            "token_path": "token.json",
            "is_remote": True,
        }

    def get(self) -> BaseReader:
        """
        Get reader instance

        :return: Data reader instance
        """
        args = self.get_args()
        return GoogleSheetsReader(**args)

    def get_external_id(self, args: dict = None) -> str:
        """
        Get unique web content identifier

        :param args: load_data args
        :return: unique content identifier
        """
        unique = {}
        if "spreadsheet_ids" in args and args.get("spreadsheet_ids"):
            unique["spreadsheet_ids"] = args.get("spreadsheet_ids")
        return json.dumps(unique)

    def prepare_args(self, **kwargs) -> dict:
        """
        Prepare arguments for load_data() method

        :param kwargs: keyword arguments
        :return: args to pass to reader
        """
        args = {}
        if "spreadsheet_ids" in kwargs and kwargs.get("spreadsheet_ids"):
            if isinstance(kwargs.get("spreadsheet_ids"), list):
                args["spreadsheet_ids"] = kwargs.get("spreadsheet_ids")  # spreadsheet ids
        return args
