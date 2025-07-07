#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.21 17:00:00                  #
# ================================================== #

from typing import List, Tuple

from pygpt_net.core.events import (
    BaseEvent,
    KernelEvent,
    ControlEvent,
    AppEvent,
    RenderEvent,
)


class Dispatcher:
    def __init__(self, window=None):
        """
        Event dispatcher

        :param window: Window instance
        """
        self.window = window
        self.nolog_events = ["system.prompt", "render.stream.append"]
        self.call_id = 0

    def dispatch(
            self,
            event: BaseEvent,
            all: bool = False
    ) -> Tuple[List[str], BaseEvent]:
        """
        Dispatch event

        :param event: event to dispatch
        :param all: true if dispatch to all plugins (enabled or not)
        :return: list of affected plugins ids and event object
        """
        if not isinstance(event, RenderEvent):
            event.call_id = self.call_id

        if self.is_log(event):
            self.window.core.debug.info("[event] Dispatch begin: " + str(event.full_name) + " (" + str(event.call_id) + ")")
            if self.window.core.debug.enabled():
                self.window.core.debug.debug("[event] Before handle: " + str(event))

        if event.stop:
            self.window.core.debug.info("[event] Skipping... (stopped): " + str(event.name))
            return [], event

        # kernel events
        if isinstance(event, KernelEvent):
            # dispatch event to kernel controller
            if not event.name in [  # those events are sent by kernel
                KernelEvent.INIT,
                KernelEvent.RESTART,
                KernelEvent.STOP,
                KernelEvent.TERMINATE,
            ]:
                self.window.controller.kernel.handle(event)
            if self.is_log(event):
                self.window.core.debug.info("[event] Dispatch end: " + str(event.full_name) + " (" + str(event.call_id) + ")")
            self.call_id += 1
            if not event.name in [
                KernelEvent.INIT,
                KernelEvent.RESTART,
                KernelEvent.STOP,
                KernelEvent.TERMINATE,
            ]:
                return [], event # kernel events finish here

        # render events
        elif isinstance(event, RenderEvent):
            # dispatch event to render controller
            self.window.controller.chat.render.handle(event)
            if self.is_log(event):
                self.window.core.debug.info("[event] Dispatch end: " + str(event.full_name) + " (" + str(event.call_id) + ")")
            self.call_id += 1
            return [], event

        # accessibility events
        if isinstance(event, ControlEvent) or isinstance(event, AppEvent):
            # dispatch event to accessibility controller
            self.window.controller.access.handle(event)

        # dispatch event to plugins
        affected = []
        for id in list(self.window.core.plugins.plugins.keys()):
            if self.window.controller.plugins.is_enabled(id) or all:
                if event.stop:
                    self.window.core.debug.info("[event] Skipping... (stopped):  " + str(event.name))
                    break
                if self.window.core.debug.enabled() and self.is_log(event):
                    self.window.core.debug.debug("[event] Apply [{}] to plugin: ".format(event.name) + id)
                self.apply(id, event)
                affected.append(id)

        if self.is_log(event):
            if self.window.core.debug.enabled():
                self.window.core.debug.debug("[event] After handle: " + str(event))
            self.window.core.debug.info("[event] Dispatch end: " + str(event.full_name) + " (" + str(event.call_id) + ")")

        self.call_id += 1
        return affected, event

    def apply(
            self,
            id: str,
            event: BaseEvent
    ):
        """
        Handle event in plugin with provided id

        :param id: plugin id
        :param event: event object
        """
        if id in self.window.core.plugins.plugins:
            try:
                self.window.core.plugins.plugins[id].handle(event)
            except AttributeError:
                pass

    def is_log(self, event: BaseEvent) -> bool:
        """
        Check if event can be logged

        :param event: event object
        :return: true if can be logged
        """
        if event.name in self.nolog_events:
            return False
        if not self.is_log_display():
            return False
        data = event.data
        if data is not None and "silent" in data and data["silent"]:
            return False
        return True

    def is_log_display(self) -> bool:
        """
        Check if logging enabled

        :return: True logging enabled
        """
        return self.window.core.config.get("log.events", False)
