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
from llama_index.readers.file.markdown import MarkdownReader

from .base import BaseLoader


class Loader(BaseLoader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = "md"
        self.name = "Markdown files"
        self.extensions = ["md"]
        self.type = ["file"]
        self.init_args = {
            "remove_hyperlinks": True,
            "remove_images": True,
        }
        self.init_args_types = {
            "remove_hyperlinks": "bool",
            "remove_images": "bool",
        }

    def get(self) -> BaseReader:
        """
        Get reader instance

        :return: Data reader instance
        """
        args = self.get_args()
        return MarkdownReader(**args)
