#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.23 19:00:00                  #
# ================================================== #

from .base import BaseCtxProvider


class JsonFilesCtxProvider(BaseCtxProvider):
    def __init__(self):
        super(JsonFilesCtxProvider, self).__init__()
        self.id = "json_files"
        self.type = "ctx"
