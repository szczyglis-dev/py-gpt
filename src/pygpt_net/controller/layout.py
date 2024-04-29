#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.29 07:00:00                  #
# ================================================== #

import os

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QRect

from pygpt_net.utils import trans


class Layout:
    def __init__(self, window=None):
        """
        Layout controller

        :param window: Window instance
        """
        self.window = window
        # self.splitters = ["main", "main.output", "toolbox", "toolbox.mode", "toolbox.presets"]
        self.splitters = ["main", "main.output", "toolbox", "toolbox.mode", "calendar", "interpreter", "interpreter.columns"]
        self.text_nodes = ["input"]

    def setup(self):
        """Setup layout"""
        self.window.controller.theme.setup()

    def post_setup(self):
        """Post setup layout (after window initialization)"""
        self.text_nodes_restore()
        self.state_restore()
        self.splitters_restore()
        self.tabs_restore()
        self.groups_restore()
        self.scroll_restore()

        # restore plugin settings state
        self.window.controller.plugins.set_by_tab(
            self.window.ui.tabs['plugin.settings'].currentIndex()
        )
        self.window.controller.ui.update_tokens()  # update tokens

    def save(self):
        """Save layout state"""
        self.text_nodes_save()
        self.splitters_save()
        self.tabs_save()
        self.groups_save()
        self.scroll_save()
        self.state_save()

    def text_nodes_restore(self):
        """Restore nodes text"""
        if not self.window.core.config.has('layout.text_nodes'):
            return
        data = self.window.core.config.get('layout.text_nodes')
        for id in self.window.ui.nodes:
            if id in data:
                try:
                    self.window.ui.nodes[id].setText(data[id])
                except Exception as e:
                    print("Error while restoring field state: " + str(e))
                    self.window.core.debug.log(e)

    def text_nodes_save(self):
        """Save nodes text"""
        data = {}
        for id in self.text_nodes:
            data[id] = self.window.ui.nodes[id].toPlainText()
        self.window.core.config.set('layout.text_nodes', data)

    def tabs_save(self):
        """Save tabs state"""
        data = {}
        for tab in self.window.ui.tabs:
            if not isinstance(self.window.ui.tabs[tab], dict):
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
            # do not save main splitter state if notepad was not opened yet
            if splitter == "calendar" and not self.window.controller.notepad.opened_once:
                continue
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
        if hasattr(self.window.ui.nodes['output'], 'verticalScrollBar'):
            data['output'] = self.window.ui.nodes['output'].verticalScrollBar().value()

        # notepads
        for id in self.window.ui.notepad:
            scroll_id = "notepad." + str(id)
            data[scroll_id] = self.window.ui.notepad[id].textarea.verticalScrollBar().value()
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
                        self.window.ui.notepad[id].textarea.verticalScrollBar().setValue(data[scroll_id])
                    except Exception as e:
                        print("Error while restoring scroll state: " + str(e))
                        self.window.core.debug.log(e)
        if 'output' in data:
            try:
                if hasattr(self.window.ui.nodes['output'], 'verticalScrollBar'):
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
            screen = QApplication.primaryScreen()
            available_geometry = screen.availableGeometry()

            if 'geometry' in data:
                geometry_data = data['geometry']
                x, y, width, height = (geometry_data['x'],
                                       geometry_data['y'],
                                       geometry_data['width'],
                                       geometry_data['height'])

                window_rect = QRect(x, y, width, height)
                adjusted_rect = available_geometry.intersected(window_rect)

                if not available_geometry.contains(window_rect):
                    adjusted_rect.adjust(0, 0, -20, -20)  # Adjust to fit within the screen

                self.window.move(adjusted_rect.x(), adjusted_rect.y())
                self.window.resize(adjusted_rect.width(), adjusted_rect.height())

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
        self.window.core.config.set('layout.window', data)

        # ------------------

        # output zoom save (Chromium, web engine only)
        if hasattr(self.window.ui.nodes['output'], 'get_zoom_value'):
            self.window.core.config.set('zoom', self.window.ui.nodes['output'].get_zoom_value())

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

    def restore_settings(self):
        """Restore groups state"""
        if not self.window.core.config.has('layout.groups'):
            return
        data = self.window.core.config.get('layout.groups')
        for id in self.window.ui.groups:
            if id in data and id.startswith('settings.advanced.'):
                try:
                    self.window.ui.groups[id].collapse(data[id])
                except Exception as e:
                    print("Error while restoring group state: " + str(e))
                    self.window.core.debug.log(e)

    def restore_default_css(self, force: bool = False):
        """
        Restore app CSS to default

        :param force: Force restore
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='restore.css',
                id=0,
                msg=trans('dialog.css.restore.confirm'),
            )
            return

        # restore css
        self.window.core.debug.info("Restoring CSS...")
        self.window.core.filesystem.backup_custom_css()
        self.window.core.filesystem.install_css(force=True)
        self.window.core.debug.info("CSS restored.")

        # update editor if opened
        current_file = self.window.ui.dialog['config.editor'].file
        if current_file is not None:
            if current_file.endswith('.css') and self.window.core.settings.active['editor']:
                self.window.core.settings.load_editor(current_file)

        # show success message
        self.window.ui.dialogs.alert(trans('dialog.css.restore.confirm.success'))
        self.window.core.debug.info("Reloading theme...")
        self.window.controller.theme.reload(force=True)  # reload theme
        self.window.core.debug.info("Theme reloaded.")

    def reload(self):
        """Reload layout"""
        self.post_setup()
