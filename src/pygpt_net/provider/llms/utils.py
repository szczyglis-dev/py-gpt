#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.15 01:00:00                  #
# ================================================== #

import os
from contextlib import ContextDecorator
from typing import Optional

class ProxyEnv(ContextDecorator):
    def __init__(self, proxy: Optional[str]):
        self.proxy = proxy
        self._saved = {}

    def __enter__(self):
        if not self.proxy:
            return self
        for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
            self._saved[key] = os.environ.get(key)
        os.environ["HTTP_PROXY"] = self.proxy
        os.environ["HTTPS_PROXY"] = self.proxy
        os.environ["ALL_PROXY"] = self.proxy
        return self

    def __exit__(self, exc_type, exc, tb):
        if not self.proxy:
            return False
        for key, val in self._saved.items():
            if val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = val
        return False