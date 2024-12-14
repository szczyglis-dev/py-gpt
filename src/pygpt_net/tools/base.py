#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 22:00:00                  #
# ================================================== #

from typing import Optional, Dict

from PySide6.QtCore import QObject
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QWidget

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.ui.widget.dialog.base import BaseDialog

class BaseTool(QObject):
    def __init__(self, *args, **kwargs):
        """
        Base Tool

        :param window: Window instance
        :param args: arguments
        :param kwargs: keyword arguments
        """
        super(BaseTool, self).__init__()
        self.window = None
        self.id = ""
        self.has_tab = False
        self.tab_title = ""
        self.tab_icon = ":/icons/build.svg"

    def setup(self):
        """Setup tool"""
        pass

    def post_setup(self):
        """Post-setup (window), after plugins are loaded"""
        pass

    def on_update(self):
        """On app main loop update"""
        pass

    def on_post_update(self):
        """On app main loop update"""
        pass

    def on_exit(self):
        """On app exit"""
        pass

    def on_reload(self):
        """On app profile reload"""
        pass

    def attach(self, window):
        """
        Attach window to plugin

        :param window: Window instance
        """
        self.window = window

    def setup_menu(self) -> Dict[str, QAction]:
        """
        Setup main menu

        :return dict with menu actions
        """
        return {}

    def setup_dialogs(self):
        """Setup dialogs (static)"""
        pass

    def setup_theme(self):
        """Setup theme"""
        pass

    def get_instance(
            self,
            type_id: str,
            dialog_id: Optional[str] = None
    ) -> Optional[BaseDialog]:
        """
        Spawn and return dialog instance

        :param type_id: dialog instance ID
        :param dialog_id: dialog instance ID
        """
        return None

    def as_tab(self, tab: Tab) -> Optional[QWidget]:
        """
        Spawn and return tab instance

        :param tab: Parent tab instance
        :return: Tab widget instance
        """
        return None

    def get_lang_mappings(self) -> Dict[str, Dict]:
        """
        Get language mappings

        :return: dict with language mappings
        """
        return {}