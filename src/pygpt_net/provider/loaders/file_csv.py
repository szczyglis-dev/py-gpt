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

from .hub.simple_csv.base import SimpleCSVReader
from .base import BaseLoader


class Loader(BaseLoader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = "csv"
        self.name = "CSV files"
        self.extensions = ["csv"]
        self.type = ["file"]
        self.init_args = {
            "concat_rows": True,
            "encoding": "utf-8",
        }
        self.init_args_types = {
            "concat_rows": "bool",
            "encoding": "str",
        }

    def get(self) -> BaseReader:
        """
        Get reader instance

        :return: Data reader instance
        """
        args = self.get_args()
        return SimpleCSVReader(**args)
