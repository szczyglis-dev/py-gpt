#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.17 22:00:00                  #
# ================================================== #
import os

from PySide6.QtCore import QSize
from PySide6.QtGui import QStandardItemModel, Qt, QIcon
from PySide6.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QSplitter, QWidget, QCheckBox, QSizePolicy

from .widget.textarea import NameInput
from .widget.settings import SettingsSlider, SettingsTextarea
from .widget.select import SelectMenu, PresetSelectMenu, AssistantSelectMenu
from ..utils import trans


class Toolbox:
    def __init__(self, window=None):
        """
        Toolbox UI

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """
        Setup toolbox

        :return: QSplitter
        :rtype: QSplitter
        """
        # modes and models
        mode_widget = QWidget()
        model_widget = QWidget()
        mode_widget.setLayout(self.setup_list('prompt.mode', trans("toolbox.mode.label")))
        model_widget.setLayout(self.setup_list('prompt.model', trans("toolbox.model.label")))
        mode_widget.setMinimumHeight(150)

        self.window.ui.splitters['toolbox.mode'] = QSplitter(Qt.Horizontal)
        self.window.ui.splitters['toolbox.mode'].addWidget(mode_widget)
        self.window.ui.splitters['toolbox.mode'].addWidget(model_widget)

        # presets
        presets = self.setup_presets('preset.presets', trans("toolbox.presets.label"))
        self.window.ui.models['preset.presets'] = self.create_model(self.window)
        self.window.ui.nodes['preset.presets'].setModel(self.window.ui.models['preset.presets'])

        self.window.ui.nodes['presets.widget'] = QWidget()
        self.window.ui.nodes['presets.widget'].setLayout(presets)
        self.window.ui.nodes['presets.widget'].setMinimumHeight(150)

        # assistants
        assistants = self.setup_assistants('assistants', trans("toolbox.assistants.label"))
        self.window.ui.models['assistants'] = self.create_model(self.window)
        self.window.ui.nodes['assistants'].setModel(self.window.ui.models['assistants'])

        self.window.ui.nodes['assistants.widget'] = QWidget()
        self.window.ui.nodes['assistants.widget'].setLayout(assistants)
        self.window.ui.nodes['assistants.widget'].setMinimumHeight(150)

        # initial prompt text
        prompt = self.setup_prompt()
        prompt_widget = QWidget()
        prompt_widget.setLayout(prompt)

        self.window.ui.splitters['toolbox.presets'] = QSplitter(Qt.Horizontal)
        self.window.ui.splitters['toolbox.presets'].addWidget(self.window.ui.nodes['presets.widget'])  # prompts list
        self.window.ui.splitters['toolbox.presets'].addWidget(self.window.ui.nodes['assistants.widget'])  # assistants list

        self.window.ui.splitters['toolbox'] = QSplitter(Qt.Vertical)
        self.window.ui.splitters['toolbox'].addWidget(self.window.ui.splitters['toolbox.mode'])  # mode and model list
        self.window.ui.splitters['toolbox'].addWidget(self.window.ui.splitters['toolbox.presets'])  # presets/assistants list
        self.window.ui.splitters['toolbox'].addWidget(prompt_widget)  # prompt text (editable)

        # AI and users names
        names_layout = QHBoxLayout()
        names_layout.addLayout(self.setup_name_input('preset.ai_name', trans("toolbox.name.ai")))
        names_layout.addLayout(self.setup_name_input('preset.user_name', trans("toolbox.name.user")))

        # bottom
        self.window.ui.nodes['temperature.label'] = QLabel(trans("toolbox.temperature.label"))
        self.window.ui.config_option['current_temperature'] = SettingsSlider(self.window, 'current_temperature',
                                                                          '', 0, 200,
                                                                          1, 100, False)

        self.window.ui.nodes['img_variants.label'] = QLabel(trans("toolbox.img_variants.label"))
        self.window.ui.config_option['img_variants'] = SettingsSlider(self.window, 'img_variants',
                                                                   '', 1, 4,
                                                                   1, 1, False)

        self.window.ui.config_option['img_raw'] = QCheckBox(trans("img.raw"))
        self.window.ui.config_option['img_raw'].stateChanged.connect(
            lambda: self.window.controller.image.toggle_raw(self.window.ui.config_option['img_raw'].isChecked()))

        dalle_label = QLabel(trans("toolbox.img_variants.label"))

        # DALL-E layout
        dalle_opts_layout = QHBoxLayout()
        dalle_opts_layout.addWidget(self.window.ui.config_option['img_raw'])
        dalle_opts_layout.addWidget(self.window.ui.config_option['img_variants'])

        dalle_layout = QVBoxLayout()
        dalle_layout.addWidget(dalle_label)
        dalle_layout.addLayout(dalle_opts_layout)

        self.window.ui.nodes['dalle.options'] = QWidget()
        self.window.ui.nodes['dalle.options'].setLayout(dalle_layout)
        self.window.ui.nodes['dalle.options'].setContentsMargins(0, 0, 0, 0)

        self.window.ui.nodes['vision.capture.enable'] = QCheckBox(trans("vision.capture.enable"))
        self.window.ui.nodes['vision.capture.enable'].stateChanged.connect(
            lambda: self.window.controller.camera.toggle(self.window.ui.nodes['vision.capture.enable'].isChecked()))
        self.window.ui.nodes['vision.capture.enable'].setToolTip(trans('vision.capture.enable.tooltip'))

        self.window.ui.nodes['vision.capture.auto'] = QCheckBox(trans("vision.capture.auto"))
        self.window.ui.nodes['vision.capture.auto'].stateChanged.connect(
            lambda: self.window.controller.camera.toggle_auto(self.window.ui.nodes['vision.capture.auto'].isChecked()))
        self.window.ui.nodes['vision.capture.auto'].setToolTip(trans('vision.capture.auto.tooltip'))

        self.window.ui.nodes['vision.capture.label'] = QLabel(trans('vision.capture.options.title'))

        # cap layout
        cap_layout = QHBoxLayout()
        cap_layout.addWidget(self.window.ui.nodes['vision.capture.enable'])
        cap_layout.addWidget(self.window.ui.nodes['vision.capture.auto'])

        # cap
        cap_vlayout = QVBoxLayout()
        cap_vlayout.addWidget(self.window.ui.nodes['vision.capture.label'])
        cap_vlayout.addLayout(cap_layout)

        # cap widget
        self.window.ui.nodes['vision.capture.options'] = QWidget()
        self.window.ui.nodes['vision.capture.options'].setLayout(cap_vlayout)
        self.window.ui.nodes['vision.capture.options'].setContentsMargins(0, 0, 0, 0)

        temp_layout = QVBoxLayout()
        temp_layout.addWidget(self.window.ui.nodes['temperature.label'])
        temp_layout.addWidget(self.window.ui.config_option['current_temperature'])
        temp_layout.addWidget(self.window.ui.nodes['dalle.options'])
        temp_layout.addWidget(self.window.ui.nodes['vision.capture.options'])

        path = os.path.abspath(os.path.join(self.window.config.get_root_path(), 'data', 'logo.png'))

        logo_button = QPushButton()
        logo_button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        logo_button.setIcon(QIcon(path))
        logo_button.setIconSize(QSize(100, 28))
        logo_button.setFlat(True)
        logo_button.clicked.connect(lambda: self.window.controller.info.goto_website())

        bottom = QHBoxLayout()
        bottom.addLayout(temp_layout, 80)
        bottom.addWidget(logo_button, 20)
        bottom.setStretchFactor(logo_button, 1)
        bottom.setAlignment(logo_button, Qt.AlignRight | Qt.AlignBottom)

        temp_widget = QWidget()
        temp_widget.setLayout(bottom)

        bottom_layout = QVBoxLayout()
        bottom_layout.addLayout(names_layout)
        bottom_layout.addWidget(temp_widget)

        names_widget = QWidget()
        names_widget.setLayout(bottom_layout)

        self.window.ui.splitters['toolbox'].addWidget(names_widget)

        return self.window.ui.splitters['toolbox']

    def setup_prompt(self):
        """
        Setup preset prompt

        :return: QVBoxLayout
        :rtype: QVBoxLayout
        """
        self.window.ui.nodes['cmd.enabled'] = QCheckBox(trans('cmd.enabled'))
        self.window.ui.nodes['cmd.enabled'].stateChanged.connect(
            lambda: self.window.controller.input.toggle_cmd(self.window.ui.nodes['cmd.enabled'].isChecked()))

        self.window.ui.nodes['toolbox.prompt.label'] = QLabel(trans("toolbox.prompt"))
        self.window.ui.nodes['toolbox.prompt.label'].setStyleSheet(self.window.controller.theme.get_style('text_bold'))

        self.window.ui.nodes['preset.clear'] = QPushButton(trans('preset.clear'))
        self.window.ui.nodes['preset.clear'].clicked.connect(
            lambda: self.window.controller.presets.clear())
        self.window.ui.nodes['preset.use'] = QPushButton(trans('preset.use'))
        self.window.ui.nodes['preset.use'].clicked.connect(
            lambda: self.window.controller.presets.use())
        self.window.ui.nodes['preset.use'].setVisible(False)

        header = QHBoxLayout()
        header.addWidget(self.window.ui.nodes['toolbox.prompt.label'])
        header.addWidget(self.window.ui.nodes['cmd.enabled'])
        header.addWidget(self.window.ui.nodes['preset.use'], alignment=Qt.AlignRight)
        header.addWidget(self.window.ui.nodes['preset.clear'], alignment=Qt.AlignRight)

        self.window.ui.nodes['preset.prompt'] = SettingsTextarea(self.window, 'preset.prompt', True)
        self.window.ui.nodes['preset.prompt'].update_ui = False
        layout = QVBoxLayout()
        layout.addLayout(header)
        layout.addWidget(self.window.ui.nodes['preset.prompt'])
        return layout

    def setup_list(self, id, title):
        """
        Setup list

        :param id: ID of the list
        :param title: Title of the list
        :return: QVBoxLayout
        :rtype: QVBoxLayout
        """
        label_key = id + '.label'
        self.window.ui.nodes[label_key] = QLabel(title)
        self.window.ui.nodes[label_key].setStyleSheet(self.window.controller.theme.get_style('text_bold'))
        self.window.ui.nodes[id] = SelectMenu(self.window, id)

        if id == 'prompt.mode':
            self.window.ui.nodes[id].selection_locked = self.window.controller.model.mode_change_locked
        elif id == 'prompt.model':
            self.window.ui.nodes[id].selection_locked = self.window.controller.model.model_change_locked

        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.nodes[label_key])
        layout.addWidget(self.window.ui.nodes[id])

        self.window.ui.models[id] = self.create_model(self.window)
        self.window.ui.nodes[id].setModel(self.window.ui.models[id])

        # prevent focus out selection leave
        self.window.ui.nodes[id].selectionModel().selectionChanged.connect(self.window.ui.nodes[id].lockSelection)
        return layout

    def setup_presets(self, id, title):
        """
        Setup list

        :param id: ID of the list
        :param title: Title of the list
        :return: QVBoxLayout
        :rtype: QVBoxLayout
        """
        self.window.ui.nodes['preset.presets.new'] = QPushButton(trans('preset.new'))
        self.window.ui.nodes['preset.presets.new'].clicked.connect(
            lambda: self.window.controller.presets.edit())

        self.window.ui.nodes['preset.presets.label'] = QLabel(title)
        self.window.ui.nodes['preset.presets.label'].setStyleSheet(self.window.controller.theme.get_style('text_bold'))
        header = QHBoxLayout()
        header.addWidget(self.window.ui.nodes['preset.presets.label'])
        header.addWidget(self.window.ui.nodes['preset.presets.new'], alignment=Qt.AlignRight)
        header.setContentsMargins(0, 0, 0, 0)

        header_widget = QWidget()
        header_widget.setLayout(header)

        self.window.ui.nodes[id] = PresetSelectMenu(self.window, id)
        self.window.ui.nodes[id].selection_locked = self.window.controller.model.preset_change_locked
        layout = QVBoxLayout()
        layout.addWidget(header_widget)
        layout.addWidget(self.window.ui.nodes[id])

        self.window.ui.models[id] = self.create_model(self.window)
        self.window.ui.nodes[id].setModel(self.window.ui.models[id])
        return layout

    def setup_assistants(self, id, title):
        """
        Setup list of assistants

        :param id: ID of the list
        :param title: Title of the list
        :return: QVBoxLayout
        :rtype: QVBoxLayout
        """
        self.window.ui.nodes['assistants.new'] = QPushButton(trans('assistant.new'))
        self.window.ui.nodes['assistants.new'].clicked.connect(
            lambda: self.window.controller.assistant.edit())

        self.window.ui.nodes['assistants.import'] = QPushButton(trans('assistant.import'))
        self.window.ui.nodes['assistants.import'].clicked.connect(
            lambda: self.window.controller.assistant.import_assistants())

        self.window.ui.nodes['assistants.label'] = QLabel(title)
        self.window.ui.nodes['assistants.label'].setStyleSheet(self.window.controller.theme.get_style('text_bold'))

        header = QHBoxLayout()
        header.addWidget(self.window.ui.nodes['assistants.label'])
        header.addWidget(self.window.ui.nodes['assistants.import'], alignment=Qt.AlignRight)
        header.addWidget(self.window.ui.nodes['assistants.new'], alignment=Qt.AlignRight)
        header.setContentsMargins(0, 0, 0, 0)

        header_widget = QWidget()
        header_widget.setLayout(header)

        self.window.ui.nodes[id] = AssistantSelectMenu(self.window, id)
        self.window.ui.nodes[id].selection_locked = self.window.controller.assistant.assistant_change_locked
        layout = QVBoxLayout()
        layout.addWidget(header_widget)
        layout.addWidget(self.window.ui.nodes[id])

        self.window.ui.models[id] = self.create_model(self.window)
        self.window.ui.nodes[id].setModel(self.window.ui.models[id])
        return layout

    def setup_name_input(self, id, title):
        """
        Setup name input

        :param id: ID of the input
        :param title: Title of the input
        :return: QVBoxLayout
        :rtype: QVBoxLayout
        """
        label_key = 'toolbox.' + id + '.label'
        self.window.ui.nodes[label_key] = QLabel(title)
        self.window.ui.nodes[id] = NameInput(self.window, id)
        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.nodes[label_key])
        layout.addWidget(self.window.ui.nodes[id])
        return layout

    def create_model(self, parent):
        """
        Create list model
        :param parent: parent widget
        :return: QStandardItemModel
        :rtype: QStandardItemModel
        """
        model = QStandardItemModel(0, 1, parent)
        return model

    def update_list(self, id, data):
        """
        Update list

        :param id: ID of the list
        :param data: Data to update
        """
        # store previous selection
        self.window.ui.nodes[id].backup_selection()

        self.window.ui.models[id].removeRows(0, self.window.ui.models[id].rowCount())
        i = 0
        for n in data:
            if 'name' in data[n]:
                self.window.ui.models[id].insertRow(i)
                name = data[n]['name']
                if id == 'preset.presets':
                    if not n.startswith('current.'):
                        name = data[n]['name'] + ' (' + str(n) + ')'
                elif id == 'prompt.mode':
                    name = trans(name)
                self.window.ui.models[id].setData(self.window.ui.models[id].index(i, 0), name)
                i += 1
        # restore previous selection
        self.window.ui.nodes[id].restore_selection()

    def update_list_assistants(self, id, data):
        """
        Update list of assistants

        :param id: ID of the list
        :param data: Data to update
        """
        # store previous selection
        self.window.ui.nodes[id].backup_selection()

        self.window.ui.models[id].removeRows(0, self.window.ui.models[id].rowCount())
        i = 0
        for n in data:
            self.window.ui.models[id].insertRow(i)
            name = data[n].name
            self.window.ui.models[id].setData(self.window.ui.models[id].index(i, 0), name)
            i += 1

        # restore previous selection
        self.window.ui.nodes[id].restore_selection()
