#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.15 03:00:00                  #
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
        excluded = kwargs.get('excluded')
        stretch = kwargs.get('stretch', False)
        placeholder_apply = self.window.controller.config.placeholder.apply

        for key, option in options.items():
            if excluded and key in excluded:
                continue

            t = option.get('type')
            if t in ('text', 'int', 'float'):
                slider = option.get('slider', False)
                secret = option.get('secret', False)
                if slider and t in ('int', 'float'):
                    widgets[key] = OptionSlider(self.window, id, key, option)
                else:
                    widgets[key] = PasswordInput(self.window, id, key, option) if secret else OptionInput(self.window, id, key, option)

            elif t == 'textarea':
                w = OptionTextarea(self.window, id, key, option)
                w.setMinimumHeight(150)
                if stretch:
                    w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                widgets[key] = w

            elif t == 'bool':
                widgets[key] = OptionCheckbox(self.window, id, key, option)

            elif t == 'bool_list':
                placeholder_apply(option)
                widgets[key] = OptionCheckboxList(self.window, id, key, option)

            elif t == 'dict':
                placeholder_apply(option)
                w = OptionDict(self.window, id, key, option)
                w.setMinimumHeight(200)
                w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                widgets[key] = w

            elif t == 'combo':
                placeholder_apply(option)
                w = OptionCombo(self.window, id, key, option)
                w.fit_to_content()
                widgets[key] = w

        return widgets

    def add_option(self, widget: QWidget, option: dict) -> QHBoxLayout:
        """
        Add option

        :param widget: Option widget
        :param option: Option data
        :return: Option layout
        """
        label = option['label']
        desc = option.get('description')
        extra = option.get('extra') or {}
        label_key = label + '.label'
        nodes = self.window.ui.nodes

        if extra.get('bold'):
            nodes[label_key] = TitleLabel(trans(label))
        else:
            nodes[label_key] = QLabel(trans(label))
        nodes[label_key].setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        nodes[label_key].setMinimumWidth(120)
        nodes[label_key].setWordWrap(True)

        desc_key = None
        if desc is not None:
            desc_key = label + '.desc'
            nodes[desc_key] = self.add_description(desc)

        if option.get('type') == 'textarea':
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        layout = QHBoxLayout()
        layout.addWidget(nodes[label_key])
        layout.addWidget(widget)
        layout.setStretch(0, 1)

        if desc is not None:
            rows = QVBoxLayout()
            rows.addLayout(layout)
            rows.addWidget(nodes[desc_key])
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
        desc = option.get('description')
        extra = option.get('extra') or {}
        nodes = self.window.ui.nodes

        if extra.get('bold'):
            nodes[label_key] = TitleLabel(trans(label))
        else:
            nodes[label_key] = QLabel(trans(label))
        nodes[label_key].setMinimumHeight(30)
        nodes[label_key].setWordWrap(True)

        desc_key = None
        if desc is not None:
            desc_key = label + '.desc'
            nodes[desc_key] = self.add_description(desc)

        layout = QVBoxLayout()
        layout.addWidget(nodes[label_key])
        layout.addWidget(widget)

        if desc is not None:
            layout.addWidget(nodes[desc_key])

        urls = extra.get('urls')
        if urls:
            urls_widget = self.add_urls(urls)
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
        desc = option.get('description')
        extra = option.get('extra') or {}
        nodes = self.window.ui.nodes

        layout = QHBoxLayout()
        layout.addWidget(widget)

        desc_key = None
        if desc is not None:
            desc_key = label + '.desc'
            nodes[desc_key] = self.add_description(desc)

        urls = extra.get('urls')
        if urls:
            urls_widget = self.add_urls(urls)
            layout.addWidget(urls_widget)

        if desc is not None:
            rows = QVBoxLayout()
            rows.addLayout(layout)
            rows.addWidget(nodes[desc_key])
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
        label.setMaximumHeight(80)
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
            for name, url in urls.items():
                layout.addWidget(UrlLabel(name, url))
        elif isinstance(urls, list):
            for url in urls:
                layout.addWidget(UrlLabel("", url))
        elif isinstance(urls, str):
            layout.addWidget(UrlLabel("", urls))
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