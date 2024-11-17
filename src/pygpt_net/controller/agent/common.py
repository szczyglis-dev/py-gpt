#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.17 03:00:00                  #
# ================================================== #

class Common:
    def __init__(self, window=None):
        """
        Agent common controller

        :param window: Window instance
        """
        self.window = window

    def enable_auto_stop(self):
        """Enable auto stop"""
        self.window.core.config.set('agent.auto_stop', True)
        self.window.core.config.save()

    def disable_auto_stop(self):
        """Disable auto stop"""
        self.window.core.config.set('agent.auto_stop', False)
        self.window.core.config.save()

    def toggle_auto_stop(self, state: bool):
        """
        Toggle auto stop

        :param state: state of checkbox
        """
        if not state:
            self.disable_auto_stop()
        else:
            self.enable_auto_stop()

    def enable_continue(self):
        """Enable always continue"""
        self.window.core.config.set('agent.continue.always', True)
        self.window.core.config.save()

    def disable_continue(self):
        """Disable always continue"""
        self.window.core.config.set('agent.continue.always', False)
        self.window.core.config.save()

    def toggle_continue(self, state: bool):
        """
        Toggle always continue

        :param state: state of checkbox
        """
        if not state:
            self.disable_continue()
        else:
            self.enable_continue()

    def enable_loop(self):
        """Enable loop"""
        self.window.core.config.set('agent.llama.loop.enabled', True)
        self.window.core.config.save()

    def disable_loop(self):
        """Disable loop"""
        self.window.core.config.set('agent.llama.loop.enabled', False)
        self.window.core.config.save()

    def toggle_loop(self, state: bool):
        """
        Toggle loop

        :param state: state of checkbox
        """
        if not state:
            self.disable_loop()
        else:
            self.enable_loop()

    def show_status(self):
        """Show agent status"""
        self.window.ui.nodes['status.agent'].setVisible(True)

    def hide_status(self):
        """Hide agent status"""
        self.window.ui.nodes['status.agent'].setVisible(False)

    def toggle_status(self):
        """Toggle agent status"""
        mode = self.window.core.config.get('mode')
        if mode in ['agent'] or self.window.controller.agent.is_inline():
            self.show_status()
        else:
            self.hide_status()