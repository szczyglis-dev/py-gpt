#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.10 10:00:00                  #
# ================================================== #
# 
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QSizePolicy, QWidget, QFrame

from pygpt_net.ui.widget.element.url import UrlLabel
from pygpt_net.ui.widget.option.checkbox import OptionCheckbox
from pygpt_net.ui.widget.option.combo import OptionCombo
from pygpt_net.ui.widget.option.dictionary import OptionDict
from pygpt_net.ui.widget.option.input import OptionInput, PasswordInput
from pygpt_net.ui.widget.option.slider import OptionSlider
from pygpt_net.ui.widget.option.textarea import OptionTextarea
from pygpt_net.utils import trans


class BaseConfigDialog:
    def __init__(self, window=None, *args, **kwargs):
        """
        Base config dialog

        :param window: Window instance
        """
        self.window = window

    def build_widgets(self, id: str, options: dict) -> dict:
        """
        Build settings options widgets

        :param id: settings ID
        :param options: settings options
        :return: settings widgets
        """
        widgets = {}

        for key in options:
            option = options[key]

            # create widget by option type
            if option['type'] == 'text' or option['type'] == 'int' or option['type'] == 'float':
                if 'slider' in option and option['slider'] and (option['type'] == 'int' or option['type'] == 'float'):
                    widgets[key] = OptionSlider(self.window, id, key, option)  # slider + text input
                else:
                    if 'secret' in option and option['secret']:
                        widgets[key] = PasswordInput(self.window, id, key, option)  # password input
                    else:
                        widgets[key] = OptionInput(self.window, id, key, option)  # text input

            elif option['type'] == 'textarea':
                widgets[key] = OptionTextarea(self.window, id, key, option)  # textarea
                widgets[key].setMinimumHeight(150)
            elif option['type'] == 'bool':
                widgets[key] = OptionCheckbox(self.window, id, key, option)  # checkbox
            elif option['type'] == 'dict':
                self.window.controller.config.placeholder.apply(option)
                widgets[key] = OptionDict(self.window, id, key, option)  # dictionary
                widgets[key].setMinimumHeight(200)
                widgets[key].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            elif option['type'] == 'combo':
                self.window.controller.config.placeholder.apply(option)
                widgets[key] = OptionCombo(self.window, id, key, option)  # combobox

        return widgets

    def add_option(self, widget: QWidget, option: dict) -> QHBoxLayout:
        """
        Add option

        :param widget: Option widget
        :param option: Option data
        :return: Option layout
        """
        label = option['label']
        extra = {}
        if 'extra' in option:
            extra = option['extra']
        label_key = label + '.label'

        self.window.ui.nodes[label_key] = QLabel(trans(label))
        self.window.ui.nodes[label_key].setMinimumWidth(120)
        if 'bold' in extra and extra['bold']:
            self.window.ui.nodes[label_key].setStyleSheet(self.window.controller.theme.get_style('text_bold'))
        self.window.ui.nodes[label_key].setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        # set resizable if textarea
        if option['type'] == 'textarea':
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        layout = QHBoxLayout()
        layout.addWidget(self.window.ui.nodes[label_key])
        layout.addWidget(widget)
        layout.setStretch(0, 1)
        return layout

    def add_row_option(self, widget: QWidget, option: dict) -> QHBoxLayout:
        """
        Add option row (label + option)

        :param widget: Widget
        :param option: Option
        :return: QHBoxLayout
        """
        label = option['label']
        label_key = label + '.label'
        extra = {}
        if 'extra' in option:
            extra = option['extra']

        self.window.ui.nodes[label_key] = QLabel(trans(label))
        self.window.ui.nodes[label_key].setMinimumHeight(30)
        if extra is not None and 'bold' in extra and extra['bold']:
            self.window.ui.nodes[label_key].setStyleSheet(self.window.controller.theme.get_style('text_bold'))

        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.nodes[label_key])
        layout.addWidget(widget)

        # append URLs
        if 'urls' in extra \
                and extra['urls'] is not None \
                and len(extra['urls']) > 0:
            urls_widget = self.add_urls(extra['urls'])
            layout.addWidget(urls_widget)
            
        return layout

    def add_raw_option(self, widget: QWidget, option: dict) -> QHBoxLayout:
        """
        Add raw option row

        :param widget: Widget
        :param option: Option
        :return: QHBoxLayout
        """
        extra = {}
        if 'extra' in option:
            extra = option['extra']
        layout = QHBoxLayout()
        layout.addWidget(widget)

        # append URLs
        if 'urls' in extra \
                and extra['urls'] is not None \
                and len(extra['urls']) > 0:
            urls_widget = self.add_urls(extra['urls'])
            layout.addWidget(urls_widget)

        return layout

    def add_urls(self, urls, align=Qt.AlignLeft) -> QWidget:
        """
        Add clickable urls to list

        :param urls: urls dict
        :param align: alignment
        """
        layout = QVBoxLayout()
        for name in urls:
            url = urls[name]
            label = UrlLabel(name, url)
            layout.addWidget(label)
        layout.setAlignment(align)

        widget = QWidget()
        widget.setLayout(layout)
        widget.setContentsMargins(0, 0, 0, 0)
        return widget

    def add_line(self) -> QFrame:
        """
        Make line
        """
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        return line
