#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.30 06:00:00                  #
# ================================================== #

from typing import List, Tuple

from pygpt_net.core.events import (
    BaseEvent,
    KernelEvent,
    ControlEvent,
    AppEvent,
    RenderEvent,
    RealtimeEvent,
)


class Dispatcher:
    def __init__(self, window=None):
        """
        Initialize the Dispatcher with a window context.

        :param window: The window context to which the dispatcher will be bound.
        """
        self.window = window
        self.nolog_events = [
            "system.prompt",
            "render.stream.append",
        ]
        self.call_id = 0
        self._pending_tasks = []

    def dispatch(
            self,
            event: BaseEvent,
            all: bool = False
    ) -> Tuple[List[str], BaseEvent]:
        """
        Dispatch an event to the appropriate handlers.

        :param event: BaseEvent: The event to dispatch.
        :param all: bool: If True, dispatch to all plugins regardless of their state.
        :return: Tuple[List[str], BaseEvent]: A tuple containing a list of affected plugin IDs and the event.
        """
        if not isinstance(event, BaseEvent):
            raise RuntimeError(f"Not an event object: {event}")

        if not isinstance(event, RenderEvent):
            event.call_id = self.call_id

        wnd = self.window
        core = wnd.core
        debug = core.debug
        controller = wnd.controller

        log_event = self.is_log(event)
        if log_event:
            debug.info(f"[event] Dispatch begin: {event.full_name} ({event.call_id})")
            if debug.enabled():
                debug.debug(f"[event] Before handle: {event}")

        if event.stop:
            if log_event:
                debug.info(f"[event] Skipping... (stopped): {event.name}")
            return [], event

        handled = False

        # realtime first, if it's a realtime event
        if isinstance(event, RealtimeEvent):
            controller.realtime.handle(event)
            if log_event:
                debug.info(f"[event] Dispatch end: {event.full_name} ({event.call_id})")
            self.call_id += 1
            return [], event

        # kernel
        if isinstance(event, KernelEvent):
            kernel_auto = (KernelEvent.INIT, KernelEvent.RESTART, KernelEvent.STOP, KernelEvent.TERMINATE)
            if event.name not in kernel_auto:
                controller.kernel.handle(event)
            if log_event:
                debug.info(f"[event] Dispatch end: {event.full_name} ({event.call_id})")
            self.call_id += 1
            if event.name not in kernel_auto:
                handled = True

        # render
        elif isinstance(event, RenderEvent):
            controller.chat.render.handle(event)
            if log_event:
                debug.info(f"[event] Dispatch end: {event.full_name} ({event.call_id})")
            self.call_id += 1
            handled = True

        # tools
        wnd.tools.handle(event)

        if handled:
            return [], event

        # realtime
        controller.realtime.handle(event)
        if event.stop:
            if log_event:
                debug.info(f"[event] Skipping... (stopped): {event.name}")
            return [], event

        # agents
        controller.agent.handle(event)
        if event.stop:
            if log_event:
                debug.info(f"[event] Skipping... (stopped): {event.name}")
            return [], event

        # ctx
        controller.ctx.handle(event)
        if event.stop:
            if log_event:
                debug.info(f"[event] Skipping... (stopped): {event.name}")
            return [], event

        # model
        controller.model.handle(event)
        if event.stop:
            if log_event:
                debug.info(f"[event] Skipping... (stopped): {event.name}")
            return [], event

        # idx
        controller.idx.handle(event)
        if event.stop:
            if log_event:
                debug.info(f"[event] Skipping... (stopped): {event.name}")
            return [], event

        # ui
        controller.ui.handle(event)
        if event.stop:
            if log_event:
                debug.info(f"[event] Skipping... (stopped): {event.name}")
            return [], event

        # access
        if isinstance(event, (ControlEvent, AppEvent)):
            controller.access.handle(event)

        affected = []
        plugins_mgr = core.plugins
        plugins_dict = plugins_mgr.plugins
        plugin_ids = tuple(plugins_dict.keys())

        # plugins
        for pid in plugin_ids:
            if controller.plugins.is_enabled(pid) or all:
                if event.stop:
                    if log_event:
                        debug.info(f"[event] Skipping... (stopped):  {event.name}")
                    break
                if log_event and debug.enabled():
                    debug.debug(f"[event] Apply [{event.name}] to plugin: {pid}")
                self.apply(pid, event)
                affected.append(pid)

        if log_event:
            if debug.enabled():
                debug.debug(f"[event] After handle: {event}")
            debug.info(f"[event] Dispatch end: {event.full_name} ({event.call_id})")

        self.call_id += 1
        return affected, event

    def apply(
            self,
            id: str,
            event: BaseEvent
    ):
        """
        Apply an event to a specific plugin by its ID.

        :param id: str: The ID of the plugin to which the event should be applied.
        :param event: BaseEvent: The event to apply to the plugin.
        """
        plugins = self.window.core.plugins.plugins
        plugin = plugins.get(id)
        if plugin is None:
            return
        try:
            plugin.handle(event)
        except AttributeError:
            pass

    def is_log(self, event: BaseEvent) -> bool:
        """
        Check if the event should be logged based on its type and configuration.

        :param event: BaseEvent: The event to check.
        :return: bool: True if the event should be logged, False otherwise.
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
        Check if event logging is enabled in the configuration.

        :return: bool: True if event logging is enabled, False otherwise.
        """
        return self.window.core.config.get("log.events", False)
