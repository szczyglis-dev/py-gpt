#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 18:00:00                  #
# ================================================== #

from typing import List

class Whisper:
    def __init__(self, window=None):
        """
        Whisper core

        :param window: Window instance
        """
        self.window = window
        self.voices = [
            "alloy",
            "echo",
            "fable",
            "onyx",
            "nova",
            "shimmer",
        ]

    def get_voices(self) -> List[str]:
        """
        Get whisper voices

        :return: whisper voice name
        """
        return self.voices