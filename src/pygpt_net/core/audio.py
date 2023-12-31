#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.31 22:00:00                  #
# ================================================== #

import re


class Audio:
    def __init__(self, window=None):
        """
        Audio core

        :param window: Window instance
        """
        self.window = window

    def clean_text(self, text: str) -> str:
        """
        Clean text before send to audio synthesis

        :param text: text
        :return: cleaned text
        """
        return re.sub(r'~###~.*?~###~', '', str(text))
