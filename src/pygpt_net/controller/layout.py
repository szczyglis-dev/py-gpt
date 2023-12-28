#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.25 21:00:00                  #
# ================================================== #


class Layout:
    def __init__(self, window=None):
        """
        Layout controller

        :param window: Window instance
        """
        self.window = window
        # self.splitters = ["main", "main.output", "toolbox", "toolbox.mode", "toolbox.presets"]
        self.splitters = ["main", "main.output", "toolbox", "toolbox.mode"]  # prevent assistants column disappearing

    def setup(self):
        """Setup layout"""
        self.window.controller.theme.setup()

    def post_setup(self):
        """Post setup layout (after window initialization)"""
        self.state_restore()
        self.splitters_restore()
        self.tabs_restore()
        self.groups_restore()
        self.scroll_restore()

        # restore plugin settings state
        self.window.controller.plugins.set_by_tab(self.window.ui.tabs['plugin.settings'].currentIndex())
        self.window.controller.ui.update_tokens()  # update tokens

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
        for tab in self.window.ui.tabs:
            data[tab] = self.window.ui.tabs[tab].currentIndex()
        self.window.core.config.set('layout.tabs', data)

    def groups_save(self):
        """Save groups state"""
        data = {}
        for id in self.window.ui.groups:
            data[id] = self.window.ui.groups[id].box.isChecked()
        self.window.core.config.set('layout.groups', data)

    def tabs_restore(self):
        """Restore tabs state"""
        if not self.window.core.config.has('layout.tabs'):
            return
        data = self.window.core.config.get('layout.tabs')
        for tab in self.window.ui.tabs:
            if tab in data:
                try:
                    self.window.ui.tabs[tab].setCurrentIndex(data[tab])
                except Exception as e:
                    print("Error while restoring tab state: " + str(e))
                    self.window.core.debug.log(e)

    def splitters_save(self):
        """Save splitters state"""
        data = {}
        for splitter in self.splitters:
            data[splitter] = self.window.ui.splitters[splitter].sizes()
        self.window.core.config.set('layout.splitters', data)

    def splitters_restore(self):
        """Restore splitters state"""
        if not self.window.core.config.has('layout.splitters'):
            return
        data = self.window.core.config.get('layout.splitters')
        for splitter in self.splitters:
            if splitter in data:
                try:
                    self.window.ui.splitters[splitter].setSizes(data[splitter])
                except Exception as e:
                    print("Error while restoring splitter state: " + str(e))
                    self.window.core.debug.log(e)

    def groups_restore(self):
        """Restore groups state"""
        if not self.window.core.config.has('layout.groups'):
            return
        data = self.window.core.config.get('layout.groups')
        for id in self.window.ui.groups:
            if id in data:
                try:
                    self.window.ui.groups[id].collapse(data[id])
                except Exception as e:
                    print("Error while restoring group state: " + str(e))
                    self.window.core.debug.log(e)

    def scroll_save(self):
        """Save scroll state"""
        data = {}
        data['output'] = self.window.ui.nodes['output'].verticalScrollBar().value()
        # notepads
        for id in self.window.ui.notepad:
            scroll_id = "notepad." + str(id)
            data[scroll_id] = self.window.ui.notepad[id].verticalScrollBar().value()
        self.window.core.config.set('layout.scroll', data)

    def scroll_restore(self):
        """Restore scroll state"""
        if not self.window.core.config.has('layout.scroll'):
            return
        data = self.window.core.config.get('layout.scroll')
        for scroll_id in data:
            # notepads
            if scroll_id.startswith("notepad."):
                id = int(scroll_id.replace("notepad.", ""))
                if id in self.window.ui.notepad:
                    try:
                        self.window.ui.notepad[id].verticalScrollBar().setValue(data[scroll_id])
                    except Exception as e:
                        print("Error while restoring scroll state: " + str(e))
                        self.window.core.debug.log(e)
        if 'output' in data:
            try:
                self.window.ui.nodes['output'].verticalScrollBar().setValue(data['output'])
            except Exception as e:
                print("Error while restoring scroll state: " + str(e))
                self.window.core.debug.log(e)

    def state_restore(self):
        """Restore window state"""
        if not self.window.core.config.has('layout.window'):
            return
        data = self.window.core.config.get('layout.window')
        try:
            if 'geometry' in data:
                geometry_data = data['geometry']
                self.window.move(geometry_data['x'], geometry_data['y'])
                self.window.resize(geometry_data['width'], geometry_data['height'])
            if 'maximized' in data and data['maximized']:
                self.window.showMaximized()
        except Exception as e:
            print("Error while restoring window state: " + str(e))
            self.window.core.debug.log(e)

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
        self.window.core.config.set('layout.window', data)

    def restore_plugin_settings(self):
        """Restore groups state"""
        if not self.window.core.config.has('layout.groups'):
            return
        data = self.window.core.config.get('layout.groups')
        for id in self.window.ui.groups:
            if id in data and id.startswith('plugin.settings.'):
                try:
                    self.window.ui.groups[id].collapse(data[id])
                except Exception as e:
                    print("Error while restoring group state: " + str(e))
                    self.window.core.debug.log(e)
