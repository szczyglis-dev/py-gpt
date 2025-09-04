#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.05 01:00:00                  #
# ================================================== #

from typing import Tuple


class Audio:
    def __init__(self, window=None):
        """
        Audio helpers for xAI.

        Note: As of now, the public xAI Python SDK does not expose TTS/STT or realtime audio APIs.
        This class exists to keep provider surface compatible.

        :param window: Window instance
        """
        self.window = window

    # Placeholders to keep interface parity
    def build_part(self, multimodal_ctx) -> None:
        return None

    def extract_first_audio_part(self, response) -> Tuple[None, None]:
        return None, None