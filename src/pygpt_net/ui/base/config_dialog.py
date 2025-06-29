#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.06.29 18:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QSizePolicy, QWidget, QFrame

from pygpt_net.ui.widget.element.labels import TitleLabel, UrlLabel
from pygpt_net.ui.widget.option.checkbox import OptionCheckbox
from pygpt_net.ui.widget.option.checkbox_list import OptionCheckboxList
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

    def build_widgets(self, id: str, options: dict, **kwargs) -> dict:
        """
        Build settings options widgets

        :param id: settings ID
        :param options: settings options
        :param kwargs: additional arguments
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
                if kwargs.get('stretch', False):
                    widgets[key].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            elif option['type'] == 'bool':
                widgets[key] = OptionCheckbox(self.window, id, key, option)  # checkbox
            elif option['type'] == 'bool_list':
                self.window.controller.config.placeholder.apply(option)
                widgets[key] = OptionCheckboxList(self.window, id, key, option)  # checkbox list
            elif option['type'] == 'dict':
                self.window.controller.config.placeholder.apply(option)
                widgets[key] = OptionDict(self.window, id, key, option)  # dictionary
                widgets[key].setMinimumHeight(200)
                widgets[key].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            elif option['type'] == 'combo':
                self.window.controller.config.placeholder.apply(option)
                widgets[key] = OptionCombo(self.window, id, key, option)  # combobox
                widgets[key].fit_to_content()

        return widgets

    def add_option(self, widget: QWidget, option: dict) -> QHBoxLayout:
        """
        Add option

        :param widget: Option widget
        :param option: Option data
        :return: Option layout
        """
        label = option['label']
        desc = None
        if "description" in option:
            desc = option['description']
        extra = {}
        if 'extra' in option:
            extra = option['extra']
        label_key = label + '.label'

        # label
        if 'bold' in extra and extra['bold']:
            self.window.ui.nodes[label_key] = TitleLabel(trans(label))
        else:
            self.window.ui.nodes[label_key] = QLabel(trans(label))
        self.window.ui.nodes[label_key].setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        self.window.ui.nodes[label_key].setMinimumWidth(120)
        self.window.ui.nodes[label_key].setWordWrap(True)

        # description
        desc_key = None
        if desc is not None:
            desc_key = label + '.desc'
            self.window.ui.nodes[desc_key] = self.add_description(desc)

        # set resizable if textarea
        if option['type'] == 'textarea':
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        layout = QHBoxLayout()
        layout.addWidget(self.window.ui.nodes[label_key])
        layout.addWidget(widget)
        layout.setStretch(0, 1)

        # add description if exists
        if desc is not None:
            rows = QVBoxLayout()
            rows.addLayout(layout)
            rows.addWidget(self.window.ui.nodes[desc_key])
            rows.setContentsMargins(0, 0, 0, 0)
            return rows

        return layout

    def add_row_option(self, widget: QWidget, option: dict, **kwargs) -> QHBoxLayout:
        """
        Add option row (label + option)

        :param widget: Widget
        :param option: Option
        :param kwargs: Additional arguments
        :return: QHBoxLayout
        """
        label = option['label']
        label_key = label + '.label'
        desc = None
        if "description" in option:
            desc = option['description']
        extra = {}
        if 'extra' in option:
            extra = option['extra']

        # label
        if extra is not None and 'bold' in extra and extra['bold']:
            self.window.ui.nodes[label_key] = TitleLabel(trans(label))
        else:
            self.window.ui.nodes[label_key] = QLabel(trans(label))
        self.window.ui.nodes[label_key].setMinimumHeight(30)
        self.window.ui.nodes[label_key].setWordWrap(True)

        # description
        desc_key = None
        if desc is not None:
            desc_key = label + '.desc'
            self.window.ui.nodes[desc_key] = self.add_description(desc)

        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.nodes[label_key])
        layout.addWidget(widget)

        if desc is not None:
            layout.addWidget(self.window.ui.nodes[desc_key])

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
        label = option['label']
        desc = None
        if "description" in option:
            desc = option['description']
        extra = {}
        if 'extra' in option:
            extra = option['extra']
        layout = QHBoxLayout()
        layout.addWidget(widget)

        # description
        desc_key = None
        if desc is not None:
            desc_key = label + '.desc'
            self.window.ui.nodes[desc_key] = self.add_description(desc)

        # append URLs
        if 'urls' in extra \
                and extra['urls'] is not None \
                and len(extra['urls']) > 0:
            urls_widget = self.add_urls(extra['urls'])
            layout.addWidget(urls_widget)

        # add description if exists
        if desc is not None:
            rows = QVBoxLayout()
            rows.addLayout(layout)
            rows.addWidget(self.window.ui.nodes[desc_key])
            rows.setContentsMargins(0, 0, 0, 0)
            return rows

        return layout

    def add_description(self, text: str) -> QLabel:
        """
        Add description

        :param text: text (to translate)
        :return: QLabel
        """
        desc = trans(text)
        label = QLabel(desc)
        label.setWordWrap(True)
        label.setMaximumHeight(40)
        label.setStyleSheet("font-size: 10px;")
        return label

    def add_urls(self, urls, align=Qt.AlignLeft) -> QWidget:
        """
        Add clickable urls to list

        :param urls: urls dict
        :param align: alignment
        """
        layout = QVBoxLayout()
        if isinstance(urls, dict):
            for name in urls:
                url = urls[name]
                label = UrlLabel(name, url)
                layout.addWidget(label)
        elif isinstance(urls, list):
            for url in urls:
                label = UrlLabel("", url)
                layout.addWidget(label)
        elif isinstance(urls, str):
            label = UrlLabel("", urls)
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
