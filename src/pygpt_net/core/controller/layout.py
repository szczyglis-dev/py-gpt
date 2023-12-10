#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.07 10:00:00                  #
# ================================================== #


from ..utils import trans


class Layout:
    def __init__(self, window=None):
        """
        Layout controller

        :param window: main window object
        """
        self.window = window
        # self.splitters = ["main", "main.output", "toolbox", "toolbox.mode", "toolbox.presets"]
        self.splitters = ["main", "main.output", "toolbox", "toolbox.mode"]  # prevent assistants column disappearing

    def setup(self):
        """Setups layout"""
        self.window.controller.theme.setup()

    def post_setup(self):
        """Post setups layout (after window initialization)"""
        self.state_restore()
        self.splitters_restore()
        self.tabs_restore()

        # restore plugin settings state
        self.window.controller.plugins.set_plugin_by_tab(self.window.tabs['plugin.settings'].currentIndex())

    def save(self):
        """Save layout state"""
        self.splitters_save()
        self.tabs_save()
        self.state_save()

    def tabs_save(self):
        """Save tabs state"""
        data = {}
        for tab in self.window.tabs:
            data[tab] = self.window.tabs[tab].currentIndex()
        self.window.config.data['layout.tabs'] = data

    def tabs_restore(self):
        """Restore tabs state"""
        if 'layout.tabs' not in self.window.config.data:
            return
        data = self.window.config.data['layout.tabs']
        for tab in self.window.tabs:
            if tab in data:
                try:
                    self.window.tabs[tab].setCurrentIndex(data[tab])
                except Exception as e:
                    print("Error while restoring tab state: " + str(e))

    def splitters_save(self):
        """Save splitters state"""
        data = {}
        for splitter in self.splitters:
            data[splitter] = self.window.splitters[splitter].sizes()
        self.window.config.data['layout.splitters'] = data

    def splitters_restore(self):
        """Restore splitters state"""
        if 'layout.splitters' not in self.window.config.data:
            return
        data = self.window.config.data['layout.splitters']
        for splitter in self.splitters:
            if splitter in data:
                try:
                    self.window.splitters[splitter].setSizes(data[splitter])
                except Exception as e:
                    print("Error while restoring splitter state: " + str(e))

    def state_restore(self):
        """Restore window state"""
        if 'layout.window' not in self.window.config.data:
            return
        data = self.window.config.data['layout.window']
        try:
            if 'geometry' in data:
                geometry_data = data['geometry']
                self.window.move(geometry_data['x'], geometry_data['y'])
                self.window.resize(geometry_data['width'], geometry_data['height'])
            if 'maximized' in data and data['maximized']:
                self.window.showMaximized()
        except Exception as e:
            print("Error while restoring window state: " + str(e))

    def state_save(self):
        """Save window state"""
        data = {}
        geometry_data = {}
        geometry = self.window.geometry()
        geometry_data['x'] = geometry.x()
        geometry_data['y'] = geometry.y()
        geometry_data['width'] = geometry.width()
        geometry_data['height'] = geometry.height()
        data['geometry'] = geometry_data
        data['maximized'] = self.window.isMaximized()
        self.window.config.data['layout.window'] = data
