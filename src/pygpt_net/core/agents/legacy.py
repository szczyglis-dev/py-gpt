#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.12 17:55:00                  #
# ================================================== #

class Legacy:
    def __init__(self, window=None):
        """
        Agents core (legacy)

        :param window: Window instance
        """
        self.window = window

    def get_idx(self) -> str:
        """Return the globally selected RAG index.

        Autonomous mode and the inline Autonomous plugin share the same RAG
        selector as the rest of the application; there is no agent-specific
        index setting anymore.
        """
        return self.window.controller.idx.get_current()
