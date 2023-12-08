#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.08 22:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLineEdit, QDialog, QLabel, QCheckBox, QHBoxLayout, QWidget, QSlider, QTextEdit

from .select import SelectMenu


class SettingsSlider(QWidget):
    def __init__(self, window=None, id=None, title=None, min=None, max=None, step=None, value=None, max_width=True,
                 section=None):
        """
        Settings slider

        :param window: main window
        :param id: option id
        :param title: option title
        :param min: min value
        :param max: max value
        :param step: value step
        :param value: current value
        :param max_width: max width
        :param section: settings section
        """
        super(SettingsSlider, self).__init__(window)
        self.window = window
        self.id = id
        self.title = title
        self.min = min
        self.max = max
        self.step = step
        self.value = value
        self.section = section

        self.label = QLabel(title)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(min)
        self.slider.setMaximum(max)
        self.slider.setSingleStep(step)
        self.slider.setValue(value)
        self.slider.valueChanged.connect(
            lambda: self.window.controller.settings.apply(self.id, self.slider.value(), 'slider', self.section))

        if max_width:
            self.slider.setMaximumWidth(240)

        self.input = SettingsInputInline(self.window, self.id, self.section)
        self.input.setText(str(value))

        self.layout = QHBoxLayout()
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.slider)
        self.layout.addWidget(self.input)

        self.setLayout(self.layout)


class SettingsCheckbox(QWidget):
    def __init__(self, window=None, id=None, title=None, value=False, section=None):
        """
        Settings checkbox

        :param window: main window
        :param id: option id
        :param title: option title
        :param value: current value
        :param section: settings section
        """
        super(SettingsCheckbox, self).__init__(window)
        self.window = window
        self.id = id
        self.title = title
        self.value = value
        self.section = section

        self.box = QCheckBox(title, self.window)
        self.box.setChecked(value)
        self.box.stateChanged.connect(
            lambda: self.window.controller.settings.toggle(self.id, self.box.isChecked(), self.section))

        # windows style fix (without this checkboxes are invisible!)
        self.box.setStyleSheet(self.window.controller.theme.get_style('checkbox'))

        self.layout = QHBoxLayout()
        self.layout.addWidget(self.box)

        self.setLayout(self.layout)


class SettingsInputInline(QLineEdit):
    def __init__(self, window=None, id=None, section=None):
        """
        Settings input inline

        :param window: main window
        :param id: option id
        :param section: settings section
        """
        super(SettingsInputInline, self).__init__(window)
        self.window = window
        self.id = id
        self.section = section
        self.setMaximumWidth(60)
        self.setStyleSheet(self.window.controller.theme.get_style('line_edit'))

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key event
        """
        super(SettingsInputInline, self).keyPressEvent(event)
        self.window.controller.settings.apply(self.id, self.text(), 'input', self.section)


class SettingsInput(QLineEdit):
    def __init__(self, window=None, id=None, autoupdate=False, section=None):
        """
        Settings input

        :param window: main window
        :param id: option id
        :param autoupdate: auto update
        :param section: settings section
        """
        super(SettingsInput, self).__init__(window)
        self.window = window
        self.id = id
        self.section = section
        self.autoupdate = autoupdate
        self.setStyleSheet(self.window.controller.theme.get_style('line_edit'))

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key event
        """
        super(SettingsInput, self).keyPressEvent(event)
        if not self.autoupdate:
            return
        self.window.controller.ui.update()
        self.window.controller.settings.change(self.id, self.text(), self.section)


class SettingsTextarea(QTextEdit):
    def __init__(self, window=None, id=None, autoupdate=False, section=None):
        """
        Settings input

        :param window: main window
        :param id: option id
        :param autoupdate: auto update
        :param section: settings section
        """
        super(SettingsTextarea, self).__init__(window)
        self.window = window
        self.id = id
        self.section = section
        self.autoupdate = autoupdate

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key event
        """
        super(SettingsTextarea, self).keyPressEvent(event)
        if not self.autoupdate:
            return
        self.window.controller.ui.update()
        self.window.controller.settings.change(self.id, self.toPlainText(), self.section)


class SettingsDialog(QDialog):
    def __init__(self, window=None, id=None):
        """
        Settings dialog

        :param window: main window
        :param id: settings id
        """
        super(SettingsDialog, self).__init__(window)
        self.window = window
        self.id = id

    def closeEvent(self, event):
        """
        Close event

        :param event: close event
        """
        self.window.settings.active[self.id] = False
        self.window.controller.settings.close(self.id)
        self.window.controller.settings.update()


class PluginSettingsDialog(QDialog):
    def __init__(self, window=None, id=None):
        """
        Plugin settings dialog

        :param window: main window
        :param id: settings id
        """
        super(PluginSettingsDialog, self).__init__(window)
        self.window = window
        self.id = id

    def closeEvent(self, event):
        """
        Close event

        :param event: close event
        """
        self.window.controller.plugins.config_dialog = False
        self.window.controller.plugins.update()


class PluginSelectMenu(SelectMenu):
    def __init__(self, window=None, id=None):
        """
        Plugin select menu (in settings dialog)

        :param window: main window
        :param id: input id
        """
        super(PluginSelectMenu, self).__init__(window)
        self.window = window
        self.id = id

        self.doubleClicked.connect(self.dblclick)

    def click(self, val):
        idx = val.row()
        self.window.tabs['plugin.settings'].setCurrentIndex(idx)
        self.window.controller.plugins.set_plugin_by_tab(idx)

    def dblclick(self, val):
        """
        Double click event

        :param val: double click event
        """
        self.window.controller.presets.edit(val.row())