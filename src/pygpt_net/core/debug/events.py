#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.05.05 12:00:00                  #
# ================================================== #

from pygpt_net.core.access.events import ControlEvent, AppEvent


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
        self.window.core.debug.add(self.id, 'App Events:', str(AppEvent.__dict__))
        self.window.core.debug.add(self.id, 'Control Events:', str(ControlEvent.__dict__))
        self.window.core.debug.add(self.id, 'Voice Cmds (all):', str(self.window.core.access.voice.commands))
        self.window.core.debug.add(self.id, 'Voice Cmds (allowed):', str(self.window.core.access.voice.get_commands()))
        self.window.core.debug.end(self.id)
