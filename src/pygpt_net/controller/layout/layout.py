#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.12.31 16:00:00                  #
# ================================================== #

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
        self.splitters = [
            "main",
            "main.output",
            "toolbox",
            "toolbox.mode",
            "calendar",
            "interpreter",
            "interpreter.columns",
            "columns",
        ]
        self.text_nodes = ["input", "input_extra"]

    def setup(self):
        """Setup layout"""
        self.window.controller.theme.setup()

    def post_setup(self):
        """Post setup layout (after window initialization)"""
        self.text_nodes_restore()
        self.state_restore()
        self.splitters_restore()
        #  self.tabs_restore()
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
        config = self.window.core.config
        if not config.has('layout.text_nodes'):
            return
        data = config.get('layout.text_nodes')
        nodes = self.window.ui.nodes
        for node_id, value in data.items():
            widget = nodes.get(node_id)
            if widget is None:
                continue
            try:
                widget.setText(value)
            except Exception as e:
                print("Error while restoring field state: " + str(e))
                self.window.core.debug.log(e)

    def text_nodes_save(self):
        """Save nodes text"""
        ui_nodes = self.window.ui.nodes
        data = {}
        for node_id in self.text_nodes:
            widget = ui_nodes.get(node_id)
            if widget is None:
                continue
            data[node_id] = widget.toPlainText()
        self.window.core.config.set('layout.text_nodes', data)

    def tabs_save(self):
        """Save tabs state"""
        tabs = self.window.ui.tabs
        data = {}
        for name, widget in tabs.items():
            if not isinstance(widget, dict):
                try:
                    data[name] = widget.currentIndex()
                except Exception:
                    pass
        self.window.core.config.set('layout.tabs', data)

    def groups_save(self):
        """Save groups state"""
        groups = self.window.ui.groups
        data = {}
        for gid, group in groups.items():
            data[gid] = group.box.isChecked()
        self.window.core.config.set('layout.groups', data)

    def tabs_restore(self):
        """Restore tabs state"""
        config = self.window.core.config
        if not config.has('layout.tabs'):
            return
        data = config.get('layout.tabs')
        tabs = self.window.ui.tabs
        for name, index in data.items():
            widget = tabs.get(name)
            if widget is None:
                continue
            try:
                if getattr(widget, "currentIndex", None) is not None and widget.currentIndex() != index:
                    widget.setCurrentIndex(index)
            except Exception as e:
                print("Error while restoring tab state: " + str(e))
                self.window.core.debug.log(e)

    def splitters_save(self):
        """Save splitters state"""
        data = {}
        ui_splitters = self.window.ui.splitters
        for splitter in self.splitters:
            if splitter == "calendar" and not self.window.controller.notepad.opened_once:
                continue
            splitter_widget = ui_splitters.get(splitter)
            if splitter_widget is None:
                continue
            try:
                data[splitter] = splitter_widget.sizes()
            except Exception:
                pass
        self.window.core.config.set('layout.splitters', data)

    def splitters_restore(self):
        """Restore splitters state"""
        config = self.window.core.config
        if not config.has('layout.splitters'):
            return
        data = config.get('layout.splitters')
        ui_splitters = self.window.ui.splitters
        for splitter, sizes in data.items():
            splitter_widget = ui_splitters.get(splitter)
            if splitter_widget is None:
                continue
            try:
                current = splitter_widget.sizes()
                if current != sizes:
                    splitter_widget.setSizes(sizes)
            except Exception as e:
                print("Error while restoring splitter state: " + str(e))
                self.window.core.debug.log(e)

    def groups_restore(self):
        """Restore groups state"""
        config = self.window.core.config
        if not config.has('layout.groups'):
            return
        data = config.get('layout.groups')
        groups = self.window.ui.groups
        for gid, state in data.items():
            group = groups.get(gid)
            if group is None:
                continue
            try:
                if group.box.isChecked() != state:
                    group.collapse(state)
            except Exception as e:
                print("Error while restoring group state: " + str(e))
                self.window.core.debug.log(e)

    def scroll_save(self):
        """Save scroll state"""
        data = {}
        nodes = self.window.ui.nodes
        output = nodes.get('output')
        if output is not None and hasattr(output, 'verticalScrollBar'):
            data['output'] = output.verticalScrollBar().value()

        for nid, notepad in self.window.ui.notepad.items():
            try:
                scroll_id = f"notepad.{nid}"
                data[scroll_id] = notepad.textarea.verticalScrollBar().value()
            except Exception:
                pass
        self.window.core.config.set('layout.scroll', data)

    def scroll_restore(self):
        """Restore scroll state"""
        config = self.window.core.config
        if not config.has('layout.scroll'):
            return
        data = config.get('layout.scroll')
        notepads = self.window.ui.notepad
        for scroll_id, value in data.items():
            if scroll_id.startswith("notepad."):
                try:
                    nid = int(scroll_id.replace("notepad.", ""))
                except Exception:
                    continue
                npad = notepads.get(nid)
                if npad is None:
                    continue
                try:
                    sb = npad.textarea.verticalScrollBar()
                    if sb.value() != value:
                        sb.setValue(value)
                except Exception as e:
                    print("Error while restoring scroll state: " + str(e))
                    self.window.core.debug.log(e)
        if 'output' in data:
            try:
                output = self.window.ui.nodes.get('output')
                if output is not None and hasattr(output, 'verticalScrollBar'):
                    sb = output.verticalScrollBar()
                    if sb.value() != data['output']:
                        sb.setValue(data['output'])
            except Exception as e:
                print("Error while restoring scroll state: " + str(e))
                self.window.core.debug.log(e)

    def state_restore(self):
        """Restore window state"""
        config = self.window.core.config
        if not config.has('layout.window'):
            return
        data = config.get('layout.window')
        try:
            screen = QApplication.primaryScreen()
            if screen is None:
                return
            available_geometry = screen.availableGeometry()

            geometry_data = data.get('geometry')
            if geometry_data:
                x = geometry_data.get('x', 0)
                y = geometry_data.get('y', 0)
                width = geometry_data.get('width', self.window.width())
                height = geometry_data.get('height', self.window.height())

                window_rect = QRect(x, y, width, height)
                adjusted_rect = available_geometry.intersected(window_rect)

                if not available_geometry.contains(window_rect):
                    adjusted_rect.adjust(0, 0, -20, -20)

                self.window.move(adjusted_rect.x(), adjusted_rect.y())
                self.window.resize(adjusted_rect.width(), adjusted_rect.height())

            if data.get('maximized'):
                self.window.showMaximized()
        except Exception as e:
            print("Error while restoring window state: " + str(e))

    def state_save(self):
        """Save window state"""
        data = {}
        geometry = self.window.geometry()
        data['geometry'] = {
            'x': geometry.x(),
            'y': geometry.y(),
            'width': geometry.width(),
            'height': geometry.height(),
        }
        data['maximized'] = self.window.isMaximized()
        self.window.core.config.set('layout.window', data)

        # ------------------

        # output zoom save (Chromium, web engine only)
        output = self.window.ui.nodes.get('output')
        if output is not None and hasattr(output, 'get_zoom_value'):
            self.window.core.config.set('zoom', output.get_zoom_value())

    def restore_plugin_settings(self):
        """Restore groups state"""
        config = self.window.core.config
        if not config.has('layout.groups'):
            return
        data = config.get('layout.groups')
        groups = self.window.ui.groups
        for gid, state in data.items():
            if not gid.startswith('plugin.settings.'):
                continue
            group = groups.get(gid)
            if group is None:
                continue
            try:
                if group.box.isChecked() != state:
                    group.collapse(state)
            except Exception as e:
                print("Error while restoring group state: " + str(e))
                self.window.core.debug.log(e)

    def restore_settings(self):
        """Restore groups state"""
        config = self.window.core.config
        if not config.has('layout.groups'):
            return
        data = config.get('layout.groups')
        groups = self.window.ui.groups
        for gid, state in data.items():
            if not gid.startswith('settings.advanced.'):
                continue
            group = groups.get(gid)
            if group is None:
                continue
            try:
                if group.box.isChecked() != state:
                    group.collapse(state)
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