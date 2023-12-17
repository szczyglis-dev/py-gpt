#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.14 19:00:00                  #
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
        self.scrolls = ["notepad1", "notepad2", "notepad3", "notepad4", "notepad5"]

    def setup(self):
        """Setups layout"""
        self.window.controller.theme.setup()

    def post_setup(self):
        """Post setups layout (after window initialization)"""
        self.state_restore()
        self.splitters_restore()
        self.tabs_restore()
        self.groups_restore()
        self.scroll_restore()

        # restore plugin settings state
        self.window.controller.plugins.set_plugin_by_tab(self.window.tabs['plugin.settings'].currentIndex())

    def save(self):
        """Save layout state"""
        self.splitters_save()
        self.tabs_save()
        self.groups_save()
        self.scroll_save()
        self.state_save()

    def tabs_save(self):
        """Save tabs state"""
        data = {}
        for tab in self.window.tabs:
            data[tab] = self.window.tabs[tab].currentIndex()
        self.window.config.set('layout.tabs', data)

    def groups_save(self):
        """Save groups state"""
        data = {}
        for id in self.window.groups:
            data[id] = self.window.groups[id].box.isChecked()
        self.window.config.set('layout.groups', data)

    def tabs_restore(self):
        """Restore tabs state"""
        if not self.window.config.has('layout.tabs'):
            return
        data = self.window.config.get('layout.tabs')
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
        self.window.config.set('layout.splitters', data)

    def splitters_restore(self):
        """Restore splitters state"""
        if not self.window.config.has('layout.splitters'):
            return
        data = self.window.config.get('layout.splitters')
        for splitter in self.splitters:
            if splitter in data:
                try:
                    self.window.splitters[splitter].setSizes(data[splitter])
                except Exception as e:
                    print("Error while restoring splitter state: " + str(e))

    def groups_restore(self):
        """Restore groups state"""
        if not self.window.config.has('layout.groups'):
            return
        data = self.window.config.get('layout.groups')
        for id in self.window.groups:
            if id in data:
                try:
                    self.window.groups[id].collapse(data[id])
                except Exception as e:
                    print("Error while restoring group state: " + str(e))

    def scroll_save(self):
        """Save scroll state"""
        data = {}
        for scroll in self.scrolls:
            data[scroll] = self.window.data[scroll].verticalScrollBar().value()
        self.window.config.set('layout.scroll', data)

    def scroll_restore(self):
        """Restore scroll state"""
        if not self.window.config.has('layout.scroll'):
            return
        data = self.window.config.get('layout.scroll')
        for scroll in self.scrolls:
            if scroll in data:
                try:
                    self.window.data[scroll].verticalScrollBar().setValue(data[scroll])
                except Exception as e:
                    print("Error while restoring scroll state: " + str(e))

    def state_restore(self):
        """Restore window state"""
        if not self.window.config.has('layout.window'):
            return
        data = self.window.config.get('layout.window')
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
        self.window.config.set('layout.window', data)

    def restore_plugin_settings(self):
        """Restore groups state"""
        if not self.window.config.has('layout.groups'):
            return
        data = self.window.config.get('layout.groups')
        for id in self.window.groups:
            if id in data and id.startswith('plugin.settings.'):
                try:
                    self.window.groups[id].collapse(data[id])
                except Exception as e:
                    print("Error while restoring group state: " + str(e))
