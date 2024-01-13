#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.13 16:00:00                  #
# ================================================== #

from llama_index.llms import ChatMessage, MessageRole


class Context:
    def __init__(self, window=None):
        """
        Context core

        :param window: Window instance
        """
        self.window = window

    def get_messages(self):
        """
        Get messages from db

        :return: Messages
        """
        messages = []

        if self.window.core.config.get('use_context'):
            items = self.window.core.ctx.get_all_items()
            for item in items:
                # input
                if item.input is not None and item.input != "":
                    messages.append(ChatMessage(
                        role=MessageRole.USER,
                        content=item.input
                    ))
                # output
                if item.output is not None and item.output != "":
                    messages.append(ChatMessage(
                        role=MessageRole.ASSISTANT,
                        content=item.output
                    ))

        return messages
