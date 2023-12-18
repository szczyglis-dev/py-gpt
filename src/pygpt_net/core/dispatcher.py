#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.18 04:00:00                  #
# ================================================== #


class Dispatcher:
    def __init__(self, window=None):
        """
        Event dispatcher

        :param window: Window instance
        """
        self.window = window

    def dispatch(self, id, event):
        """
        Dispatch event to plugin with provided id

        :param id: plugin id
        :param event: event object
        """
        if id in self.window.controller.plugins.handler.plugins:
            try:
                self.window.controller.plugins.handler.plugins[id].handle(event)
            except AttributeError:
                pass


class Event:
    def __init__(self, name=None, data=None):
        """
        Event class

        :param name: event name
        :param data: event data
        """
        self.name = name
        self.data = data
        self.ctx = None
        self.stop = False
