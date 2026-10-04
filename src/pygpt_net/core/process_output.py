#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.02 14:00:00                  #
# ================================================== #

"""Subprocess output with exit status, compatible with stdout/stderr unpacking."""


class ProcessOutput(tuple):
    def __new__(cls, stdout, stderr, return_code=None):
        value = super().__new__(cls, (stdout, stderr))
        value.return_code = return_code if isinstance(return_code, int) else None
        return value
