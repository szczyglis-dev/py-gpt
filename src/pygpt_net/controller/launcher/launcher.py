#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.08.15 15:35:00                  #
# ================================================== #

from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_AGENT_LLAMA,
    MODE_EXPERT,
    MODE_LANGCHAIN,
    MODE_LLAMA_INDEX,
)
class Launcher:
    def __init__(self, window=None):
        """
        Launcher controller

        :param window: Window instance
        """
        self.window = window
        self._startup_checks_started = False

    def after_setup(self):
        """Schedule startup network checks after the first main-window paint."""
        # Launcher.run() calls controller.after_setup() after show(), but before
        # QApplication.exec(). MainWindow.appReady is emitted after the first
        # paint, which guarantees that an available-update dialog can never race
        # ahead of the actual application window.
        if getattr(self.window, "_app_ready_emitted", False):
            self._run_startup_checks()
            return
        try:
            self.window.appReady.connect(self._run_startup_checks)
        except (AttributeError, RuntimeError):
            self._run_startup_checks()

    def _run_startup_checks(self):
        """Start the asynchronous update check and banner synchronization once."""
        if self._startup_checks_started:
            return
        self._startup_checks_started = True

        if self.window.core.config.get('updater.check.launch'):
            self.window.core.updater.run_check(
                force=True,
                on_finished=self.window.core.banners.run_load,
                event="launch",
            )
        else:
            self.window.core.banners.run_load()

    def show_api_monit(self):
        """Show empty API KEY monit"""
        self.window.ui.dialogs.open('info.start')

    def check_updates(self):
        """Check for updates"""
        self.window.core.updater.check(True)

    def toggle_update_check(self, value):
        """Toggle update check on startup"""
        self.window.core.config.set('updater.check.launch', value)
        self.window.core.config.save()
