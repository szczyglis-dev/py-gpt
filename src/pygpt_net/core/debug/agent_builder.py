#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.19 00:00:00                  #
# ================================================== #

class AgentBuilderDebug:
    def __init__(self, window=None):
        """
        Agent debug

        :param window: Window instance
        """
        self.window = window
        self.id = 'agent_builder'

    def update(self):
        """Update debug window"""
        debug = self.window.core.debug
        editor = self.window.ui.editor["agent.builder"]

        debug.begin(self.id)
        debug.add(self.id, 'nodes', str(editor.debug_state()))
        debug.end(self.id)
