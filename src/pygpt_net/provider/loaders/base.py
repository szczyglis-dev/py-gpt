#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.27 04:00:00                  #
# ================================================== #

from llama_index.readers.base import BaseReader


class BaseLoader:
    def __init__(self, *args, **kwargs):
        self.id = ""
        self.name = ""
        self.extensions = []
        self.type = ["file"]
        self.instructions = []  # list of instructions for 'web_index' command for how to handle this type

    def get(self) -> BaseReader:
        """
        Get reader instance

        :return: Data reader instance
        """
        pass
