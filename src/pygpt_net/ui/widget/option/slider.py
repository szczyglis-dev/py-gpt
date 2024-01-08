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

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QHBoxLayout, QWidget, QSlider

from pygpt_net.ui.widget.option.input import OptionInputInline


class NoScrollSlider(QSlider):
    def __init__(self, orientation, parent=None):
        super(NoScrollSlider, self).__init__(orientation, parent)

    def wheelEvent(self, event):
        event.ignore()  # disable mouse wheel


class OptionSlider(QWidget):
    def __init__(self, window=None, parent_id: str = None, id: str = None, option: dict = None):
        """
        Settings slider

        :param window: main window
        :param id: option id
        :param parent_id: parent option id
        :param option: option data
        """
        super(OptionSlider, self).__init__(window)
        self.window = window
        self.id = id
        self.parent_id = parent_id
        self.option = option
        self.value = 0
        self.title = ""
        self.min = 0
        self.max = 1
        self.step = 1
        self.multiplier = 1

        # from option data
        if self.option is not None:
            if 'min' in self.option:
                self.min = self.option['min']
            if 'max' in self.option:
                self.max = self.option['max']
            if 'step' in self.option:
                self.step = self.option['step']
            self.value = self.min
            if 'value' in self.option:
                self.value = self.option['value']
            if 'multiplier' in self.option:
                self.multiplier = self.option['multiplier']
            if 'label' in self.option:
                self.title = self.option['label']
            if 'type' in self.option:
                if self.option['type'] == 'float':
                    self.value = self.value * self.multiplier  # multiplier makes effect only on float
                    self.min = self.min * self.multiplier
                    self.max = self.max * self.multiplier
                    # step = step * multiplier
                elif self.option['type'] == 'int':
                    self.value = int(self.value)

        # self.label = QLabel(self.title)  # TODO: check this
        self.label = QLabel('')
        self.slider = NoScrollSlider(Qt.Horizontal)
        self.slider.setMinimum(self.min)
        self.slider.setMaximum(self.max)
        self.slider.setSingleStep(self.step)
        self.slider.setValue(self.value)
        self.slider.valueChanged.connect(
            lambda: self.window.controller.config.slider.on_update(
                self.parent_id, self.id, self.option, self.slider.value(), 'slider'))

        # if max_width:
            # self.slider.setMaximumWidth(240)

        self.input = OptionInputInline(self.window, self.parent_id, self.id, self.option)
        self.input.setText(str(self.value))
        self.input.slider = True  # set is slider connected

        self.layout = QHBoxLayout()
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.slider)
        self.layout.addWidget(self.input)

        self.setLayout(self.layout)
