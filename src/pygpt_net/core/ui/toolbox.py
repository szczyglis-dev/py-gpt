#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Created Date: 2023.04.09 20:00:00                  #
# ================================================== #

from PySide6.QtGui import QStandardItemModel, Qt
from PySide6.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QSplitter, QWidget

from .widgets import NameInput, SelectMenu, SettingsSlider, SettingsTextarea, PresetSelectMenu
from ..utils import trans


class Toolbox:
    def __init__(self, window=None):
        """
        Toolbox UI

        :param window: main UI window object
        """
        self.window = window

    def setup(self):
        """
        Setups toolbox

        :return: QSplitter
        """
        # modes and models
        mode_widget = QWidget()
        model_widget = QWidget()
        mode_widget.setLayout(self.setup_list('prompt.mode', trans("toolbox.mode.label")))
        model_widget.setLayout(self.setup_list('prompt.model', trans("toolbox.model.label")))
        mode_widget.setMinimumHeight(150)

        modes_splitter = QSplitter(Qt.Horizontal)
        modes_splitter.addWidget(mode_widget)
        modes_splitter.addWidget(model_widget)

        # presets
        presets = self.setup_presets('preset.presets', trans("toolbox.presets.label"))
        self.window.models['preset.presets'] = self.create_model(self.window)
        self.window.data['preset.presets'].setModel(self.window.models['preset.presets'])

        presets_widget = QWidget()
        presets_widget.setLayout(presets)
        presets_widget.setMinimumHeight(150)

        # initial prompt text
        prompt = self.setup_prompt()

        prompt_widget = QWidget()
        prompt_widget.setLayout(prompt)

        layout = QSplitter(Qt.Vertical)
        layout.addWidget(modes_splitter)  # mode and model list
        layout.addWidget(presets_widget)  # prompts list
        layout.addWidget(prompt_widget)  # prompt text (editable)

        # AI and users names
        names_layout = QHBoxLayout()
        names_layout.addLayout(self.setup_name_input('preset.ai_name', trans("toolbox.name.ai")))
        names_layout.addLayout(self.setup_name_input('preset.user_name', trans("toolbox.name.user")))

        # bottom

        self.window.data['temperature.label'] = QLabel(trans("toolbox.temperature.label"))
        self.window.config_option['current_temperature'] = SettingsSlider(self.window, 'current_temperature',
                                                                          '', 0, 200,
                                                                          1, 100, False)

        self.window.data['img_variants.label'] = QLabel(trans("toolbox.img_variants.label"))
        self.window.config_option['img_variants'] = SettingsSlider(self.window, 'img_variants',
                                                                   '', 1, 4,
                                                                   1, 1, False)

        temp_layout = QVBoxLayout()
        temp_layout.addWidget(self.window.data['temperature.label'])
        temp_layout.addWidget(self.window.config_option['current_temperature'])
        temp_layout.addWidget(self.window.data['img_variants.label'])
        temp_layout.addWidget(self.window.config_option['img_variants'])
        temp_widget = QWidget()
        temp_widget.setLayout(temp_layout)

        bottom_layout = QVBoxLayout()
        bottom_layout.addLayout(names_layout)
        bottom_layout.addWidget(temp_widget)

        names_widget = QWidget()
        names_widget.setLayout(bottom_layout)

        layout.addWidget(names_widget)

        return layout

    def setup_prompt(self):
        """
        Setups preset prompt

        :return: QVBoxLayout
        """
        self.window.data['toolbox.prompt.label'] = QLabel(trans("toolbox.prompt"))
        self.window.data['toolbox.prompt.label'].setStyleSheet(self.window.controller.theme.get_style('text_bold'))
        self.window.data['preset.clear'] = QPushButton(trans('preset.clear'))
        self.window.data['preset.clear'].clicked.connect(
            lambda: self.window.controller.presets.clear())
        self.window.data['preset.use'] = QPushButton(trans('preset.use'))
        self.window.data['preset.use'].clicked.connect(
            lambda: self.window.controller.presets.use())
        self.window.data['preset.use'].setVisible(False)
        header = QHBoxLayout()
        header.addWidget(self.window.data['toolbox.prompt.label'])
        header.addWidget(self.window.data['preset.use'], alignment=Qt.AlignRight)
        header.addWidget(self.window.data['preset.clear'], alignment=Qt.AlignRight)

        self.window.data['preset.prompt'] = SettingsTextarea(self.window, 'preset.prompt', True)
        layout = QVBoxLayout()
        layout.addLayout(header)
        layout.addWidget(self.window.data['preset.prompt'])
        return layout

    def setup_list(self, id, title):
        """
        Setups list

        :param id: ID of the list
        :param title: Title of the list
        :return: QVBoxLayout
        """
        label_key = id + '.label'
        self.window.data[label_key] = QLabel(title)
        self.window.data[label_key].setStyleSheet(self.window.controller.theme.get_style('text_bold'))
        self.window.data[id] = SelectMenu(self.window, id)
        layout = QVBoxLayout()
        layout.addWidget(self.window.data[label_key])
        layout.addWidget(self.window.data[id])

        self.window.models[id] = self.create_model(self.window)
        self.window.data[id].setModel(self.window.models[id])
        return layout

    def setup_presets(self, id, title):
        """
        Setups list

        :param id: ID of the list
        :param title: Title of the list
        :return: QVBoxLayout
        """
        self.window.data['preset.presets.new'] = QPushButton(trans('preset.new'))
        self.window.data['preset.presets.new'].clicked.connect(
            lambda: self.window.controller.presets.edit())

        self.window.data['preset.presets.label'] = QLabel(title)
        self.window.data['preset.presets.label'].setStyleSheet(self.window.controller.theme.get_style('text_bold'))
        header = QHBoxLayout()
        header.addWidget(self.window.data['preset.presets.label'])
        header.addWidget(self.window.data['preset.presets.new'], alignment=Qt.AlignRight)
        header.setContentsMargins(0, 0, 0, 0)

        header_widget = QWidget()
        header_widget.setLayout(header)

        self.window.data[id] = PresetSelectMenu(self.window, id)
        layout = QVBoxLayout()
        layout.addWidget(header_widget)
        layout.addWidget(self.window.data[id])

        self.window.models[id] = self.create_model(self.window)
        self.window.data[id].setModel(self.window.models[id])
        return layout

    def setup_name_input(self, id, title):
        """
        Setups name input

        :param id: ID of the input
        :param title: Title of the input
        :return: QVBoxLayout
        """
        label_key = 'toolbox.' + id + '.label'
        self.window.data[label_key] = QLabel(title)
        self.window.data[id] = NameInput(self.window, id)
        layout = QVBoxLayout()
        layout.addWidget(self.window.data[label_key])
        layout.addWidget(self.window.data[id])
        return layout

    def create_model(self, parent):
        """
        Creates list model
        :param parent: parent widget
        :return: QStandardItemModel
        """
        model = QStandardItemModel(0, 1, parent)
        return model

    def update_list(self, id, data):
        """
        Updates list

        :param id: ID of the list
        :param data: Data to update
        """
        self.window.models[id].removeRows(0, self.window.models[id].rowCount())
        i = 0
        for n in data:
            if 'name' in data[n]:
                self.window.models[id].insertRow(i)
                name = data[n]['name']
                if id == 'preset.presets':
                    if not n.startswith('current.'):
                        name = data[n]['name'] + ' (' + str(n) + ')'
                self.window.models[id].setData(self.window.models[id].index(i, 0), name)
                i += 1
