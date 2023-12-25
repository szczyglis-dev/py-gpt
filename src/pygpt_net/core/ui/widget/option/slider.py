#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.22 19:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QHBoxLayout, QWidget, QSlider

from pygpt_net.core.ui.widget.option.input import OptionInputInline


class NoScrollSlider(QSlider):
    def __init__(self, orientation, parent=None):
        super(NoScrollSlider, self).__init__(orientation, parent)

    def wheelEvent(self, event):
        event.ignore()  # disable mouse wheel


class OptionSlider(QWidget):
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
        super(OptionSlider, self).__init__(window)
        self.window = window
        self.id = id
        self.title = title
        self.min = min
        self.max = max
        self.step = step
        self.value = value
        self.section = section

        self.label = QLabel(title)
        self.slider = NoScrollSlider(Qt.Horizontal)
        self.slider.setMinimum(min)
        self.slider.setMaximum(max)
        self.slider.setSingleStep(step)
        self.slider.setValue(value)
        self.slider.valueChanged.connect(
            lambda: self.window.controller.settings.apply(self.id, self.slider.value(), 'slider', self.section))

        if max_width:
            self.slider.setMaximumWidth(240)

        self.input = OptionInputInline(self.window, self.id, self.section)
        self.input.setText(str(value))

        self.layout = QHBoxLayout()
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.slider)
        self.layout.addWidget(self.input)

        self.setLayout(self.layout)
