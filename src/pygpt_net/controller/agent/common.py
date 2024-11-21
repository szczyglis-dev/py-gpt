#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.21 20:00:00                  #
# ================================================== #

from pygpt_net.core.types import (
    MODE_AGENT,
)
from pygpt_net.utils import trans


class Common:
    def __init__(self, window=None):
        """
        Agent common controller

        :param window: Window instance
        """
        self.window = window

    def enable_auto_stop(self):
        """Enable auto stop (Legacy)"""
        self.window.core.config.set('agent.auto_stop', True)
        self.window.core.config.save()

    def disable_auto_stop(self):
        """Disable auto stop (Legacy)"""
        self.window.core.config.set('agent.auto_stop', False)
        self.window.core.config.save()

    def toggle_auto_stop(self, state: bool):
        """
        Toggle auto stop (Legacy)

        :param state: state of checkbox
        """
        if not state:
            self.disable_auto_stop()
        else:
            self.enable_auto_stop()

    def enable_continue(self):
        """Enable always continue (Legacy)"""
        self.window.core.config.set('agent.continue.always', True)
        self.window.core.config.save()

    def disable_continue(self):
        """Disable always continue (Legacy)"""
        self.window.core.config.set('agent.continue.always', False)
        self.window.core.config.save()

    def toggle_continue(self, state: bool):
        """
        Toggle always continue (Legacy)

        :param state: state of checkbox
        """
        if not state:
            self.disable_continue()
        else:
            self.enable_continue()

    def is_infinity_loop(self, mode: str) -> bool:
        """
        Check if infinity loop is active

        :param mode: current mode
        :return: True if infinity loop is enabled
        """
        # legacy
        if (mode == MODE_AGENT and self.window.core.config.get('agent.iterations') == 0) or \
            (self.window.controller.plugins.is_enabled("agent")
             and self.window.core.plugins.get_option("agent", "iterations") == 0):
            return True
        return False

    def display_infinity_loop_confirm(self):
        """Show infinity run confirm dialog"""
        self.window.ui.dialogs.confirm(
            type="agent.infinity.run",
            id=0,
            msg=trans("agent.infinity.confirm.content"),
        )

    def show_status(self):
        """Show agent status (Legacy)"""
        self.window.ui.nodes['status.agent'].setVisible(True)

    def hide_status(self):
        """Hide agent status (Legacy)"""
        self.window.ui.nodes['status.agent'].setVisible(False)

    def toggle_status(self):
        """Toggle agent status (Legacy)"""
        mode = self.window.core.config.get('mode')
        if mode in [MODE_AGENT] or self.window.controller.agent.legacy.is_inline():
            self.show_status()
        else:
            self.hide_status()

    def enable_loop(self):
        """Enable loop (Llama)"""
        self.window.core.config.set('agent.llama.loop.enabled', True)
        self.window.core.config.save()

    def disable_loop(self):
        """Disable loop (Llama)"""
        self.window.core.config.set('agent.llama.loop.enabled', False)
        self.window.core.config.save()

    def toggle_loop(self, state: bool):
        """
        Toggle loop (Llama)

        :param state: state of checkbox
        """
        if not state:
            self.disable_loop()
        else:
            self.enable_loop()