#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 19:00:00                  #
# ================================================== #

from pygpt_net.core.events import (
    ControlEvent,
    AppEvent,
    Event,
    KernelEvent,
    RenderEvent,
    BaseEvent
)


class EventsDebug:
    def __init__(self, window=None):
        """
        Events debug

        :param window: Window instance
        """
        self.window = window
        self.id = 'events'

    def update(self):
        """Update debug window."""
        self.window.core.debug.begin(self.id)
        self.window.core.debug.add(self.id, 'App Events:', str(self.extract_events(AppEvent)))
        self.window.core.debug.add(self.id, 'Control Events:', str(self.extract_events(ControlEvent)))
        self.window.core.debug.add(self.id, 'Kernel Events:', str(self.extract_events(KernelEvent)))
        self.window.core.debug.add(self.id, 'Render Events:', str(self.extract_events(RenderEvent)))
        self.window.core.debug.add(self.id, 'Plugin Events:', str(self.extract_events(Event)))
        self.window.core.debug.add(self.id, '----', '')
        self.window.core.debug.add(self.id, 'Voice Cmds (all):', str(self.window.core.access.voice.commands))
        self.window.core.debug.add(self.id, 'Voice Cmds (allowed):', str(self.window.core.access.voice.get_commands()))
        self.window.core.debug.end(self.id)

    def extract_events(self, events: BaseEvent) -> dict:
        """
        Extract events

        :param events: Events class
        """
        result = {}
        for property, value in vars(events).items():
            if (isinstance(value, str)
                    or isinstance(value, int)
                    or isinstance(value, float)
                    or isinstance(value, bool)):
                result[property] = value
        return result
