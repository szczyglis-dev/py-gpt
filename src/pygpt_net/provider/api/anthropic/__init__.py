#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.28 09:00:00                  #
# ================================================== #

from anthropic import Anthropic

from pygpt_net.core.types import (
    MODE_CHAT,
)
from pygpt_net.item.model import ModelItem

class ApiAnthropic:

    def __init__(self, window=None):
        """
        Anthropic API wrapper core

        :param window: Window instance
        """
        self.window = window
        self.client = None
        self.locked = False

    def get_client(
            self,
            mode: str = MODE_CHAT,
            model: ModelItem = None
    ) -> Anthropic:
        """
        Return Anthropic client

        :param mode: Mode
        :param model: Model
        :return: Anthropic client
        """
        if self.client is not None:
            try:
                self.client.close()  # close previous client if exists
            except Exception as e:
                self.window.core.debug.log(e)
                print("Error closing previous Anthropic client:", e)
        self.client = Anthropic(
            api_key=self.window.core.config.get('api_key_anthropic', "")
        )
        return self.client

    def stop(self):
        """On global event stop"""
        pass

    def close(self):
        """Close Anthropic client"""
        if self.locked:
            return
        if self.client is not None:
            try:
                pass
                # self.client.close()
            except Exception as e:
                self.window.core.debug.log(e)
                print("Error closing Anthropic client:", e)
