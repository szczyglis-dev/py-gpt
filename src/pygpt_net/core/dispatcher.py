#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.31 04:00:00                  #
# ================================================== #

import json

from pygpt_net.item.ctx import CtxItem


class Event:
    def __init__(self, name: str = None, data: dict = None):
        """
        Event object class

        :param name: event name
        :param data: event data
        """
        self.name = name
        self.data = data
        self.ctx = None
        self.stop = False


class Dispatcher:
    def __init__(self, window=None):
        """
        Event dispatcher

        :param window: Window instance
        """
        self.window = window

    def dispatch(self, event: Event, all: bool = False, is_async: bool = False) -> (list, Event):
        """
        Dispatch event to plugins

        :param event: event to dispatch
        :param all: true if dispatch to all plugins (enabled or not)
        :param is_async: true if async event
        :return:list of affected plugins ids and event object
        """
        affected = []
        for id in self.window.core.plugins.plugins:
            if self.window.controller.plugins.is_enabled(id) or all:
                if event.stop:
                    break
                self.apply(id, event, is_async)
                affected.append(id)

        return affected, event

    def apply(self, id: str, event: Event, is_async: bool = False):
        """
        Handle event in plugin with provided id

        :param id: plugin id
        :param event: event object
        :param is_async: true if async event
        """
        if id in self.window.core.plugins.plugins:
            try:
                self.window.core.plugins.plugins[id].is_async = is_async
                self.window.core.plugins.plugins[id].handle(event)
            except AttributeError:
                pass

    def reply(self, ctx: CtxItem):
        """
        Reply to late response (async event)

        :param ctx: context object
        """
        if ctx is not None:
            self.window.ui.status("")  # Clear status
            if ctx.reply:
                self.window.core.ctx.update_item(ctx)  # update context in db
                self.window.ui.status('...')
                self.window.controller.chat.input.send(json.dumps(ctx.results), force=True)  # force send to input
