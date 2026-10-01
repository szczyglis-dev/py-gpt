#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.12.26 12:00:00                  #
# ================================================== #

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices


class Info:
    def __init__(self, window=None):
        """
        Info dialogs controller

        :param window: Window instance
        """
        self.window = window

        # prepare info ids
        self.ids = ['about', 'changelog', 'license', 'system_info']
        self.active = {}

        # prepare active
        for id in self.ids:
            self.active[id] = False

    def setup(self):
        pass

    def toggle(
            self,
            id: str,
            width: int = 400,
            height: int = 400
    ):
        """
        Toggle info dialog

        :param id: dialog to toggle
        :param width: dialog width
        :param height: dialog height
        """
        if id in self.active and self.active[id]:
            self.window.ui.dialogs.close('info.' + id)
            self.active[id] = False
        else:
            if id == 'about':
                self.window.ui.dialogs.about.prepare()
            elif id == 'system_info':
                self.window.ui.dialogs.system_info.prepare()
            self.window.ui.dialogs.open(
                'info.' + id,
                width=width,
                height=height,
            )
            self.active[id] = True

        # update menu
        self.update_menu()

    def open_url(self, url: str):
        """
        Open URL in the default web browser

        :param url: URL to open
        """
        if url:
            if self.window.core.config.get("ctx.urls.internal", False):
                self.window.tools.get("web_browser").set_url(url)
            else:
                QDesktopServices.openUrl(QUrl(url))

    def open_external_url(self, url: str):
        """Open URL in the system default browser, ignoring internal URL settings."""
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def open_docs_url(self, url: str):
        """Open documentation in Canvas and always reveal/focus its surface."""
        if not url:
            return
        browser = self.window.tools.get("web_browser")
        if browser is not None:
            # set_url() is an explicit/manual Canvas open path: it creates the
            # canonical tab when needed, enables split screen even when global
            # Canvas auto-open is disabled, focuses Canvas, and loads the URL.
            browser.set_url(url)
        else:
            QDesktopServices.openUrl(QUrl(url))

    def goto_website(self):
        """Open project website in the system browser."""
        self.open_external_url(self.window.meta['website'])

    def goto_docs(self):
        """Open docs in the internal Canvas/browser and force it visible."""
        self.open_docs_url(self.window.meta['docs'])

    def goto_pypi(self):
        """Open PyPi in the system browser."""
        self.open_external_url(self.window.meta['pypi'])

    def goto_github(self):
        """Open GitHub page in the system browser."""
        self.open_external_url(self.window.meta['github'])

    def goto_snap(self):
        """Open Snapcraft page in the system browser."""
        self.open_external_url(self.window.meta['snap'])

    def goto_ms_store(self):
        """Open MS Store page in the system browser."""
        self.open_external_url(self.window.meta['ms_store'])

    def goto_update(self):
        """Open update URL in the system browser."""
        self.open_external_url(self.window.meta['website'])

    def goto_donate(self):
        """Open donate page in the system browser."""
        self.open_external_url(self.window.meta['donate'])

    def goto_discord(self):
        """Open Discord page in the system browser."""
        self.open_external_url(self.window.meta['discord'])

    def goto_report(self):
        """Open report-a-bug page in the system browser."""
        self.open_external_url(self.window.meta['report'])

    def donate(self, id: str):
        """
        Donate action

        :param id: donate id
        """
        if id == 'coffee':
            self.open_external_url(self.window.meta['donate_coffee'])
        elif id == 'paypal':
            self.open_external_url(self.window.meta['donate_paypal'])
        elif id == 'github':
            self.open_external_url(self.window.meta['donate_github'])

    def update_menu(self):
        """Update info menu"""
        for id in self.ids:
            item = 'info.' + id
            if item in self.window.ui.menu:
                if id in self.active and self.active[id]:
                    self.window.ui.menu[item].setChecked(True)
                else:
                    self.window.ui.menu[item].setChecked(False)
