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

if TYPE_CHECKING:
    from llama_index.core.readers.base import BaseReader

from ..base import BaseLoader


class Loader(BaseLoader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = "html"
        self.name = "HTML files"
        self.extensions = ["html", "htm"]
        self.type = ["file"]
        self.init_args = {
            "tag": "section",
            "ignore_no_id": False,
        }
        self.init_args_types = {
            "tag": {'type': 'str', 'extra': {}},
            "ignore_no_id": {'type': 'bool', 'extra': {}},
        }

        self.configure_locale(__file__, required_config=[],
                              required_options=[])

    def get(self) -> BaseReader:
        """
        Get reader instance

        :return: Data reader instance
        """
        from llama_index.readers.file.html import HTMLTagReader
        args = self.get_args()
        return HTMLTagReader(**args)
