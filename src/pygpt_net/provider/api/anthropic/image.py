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

from typing import Optional, Dict
from pygpt_net.core.bridge.context import BridgeContext


class Image:
    def __init__(self, window=None):
        self.window = window

    def generate(self, context: BridgeContext, extra: Optional[Dict] = None, sync: bool = True) -> bool:
        """
        Anthropic does not support image generation; only vision input.
        """
        # Inform handlers that nothing was generated
        return False