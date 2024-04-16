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
from llama_index.readers.file.ipynb import IPYNBReader

from .base import BaseLoader


class Loader(BaseLoader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = "ipynb"
        self.name = "IPYNB Notebook files"
        self.extensions = ["ipynb"]
        self.type = ["file"]
        self.init_args = {
            "parser_config": None,
            "concatenate": False,
        }
        self.init_args_types = {
            "parser_config": "dict",
            "concatenate": "bool",
        }

    def get(self) -> BaseReader:
        """
        Get reader instance

        :return: Data reader instance
        """
        args = self.get_args()
        return IPYNBReader(**args)
