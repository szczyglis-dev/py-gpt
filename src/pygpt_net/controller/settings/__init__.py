#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.05 23:00:00                  #
# ================================================== #

import os

from .editor import Editor
from .profile import Profile
from .workdir import Workdir

from pygpt_net.utils import trans


class Settings:
    def __init__(self, window=None):
        """
        Settings controller

        :param window: Window instance
        """
        self.window = window
        self.editor = Editor(window)
        self.profile = Profile(window)
        self.workdir = Workdir(window)
        self.width = 800
        self.height = 500

    def setup(self):
        """Set up settings editor"""
        self.profile.setup()
        self.editor.setup()

    def load(self):
        """Load settings"""
        self.editor.load()

    def save_all(self, force: bool = False):
        """
        Save all settings and data

        :param force: force save
        """
        info = trans('info.settings.all.saved')
        self.window.core.tabs.save()
        self.window.core.config.save()
        self.window.core.presets.save_all()
        self.window.controller.notepad.save_all()
        self.window.controller.calendar.save_all()
        self.window.controller.painter.save()
        if not force:
            self.window.ui.dialogs.alert(info)
            self.window.ui.status(info)
        self.window.controller.ui.update()

    def update(self):
        """Update settings"""
        self.update_menu()

    def update_menu(self):
        """Update menu"""
        for id in self.window.core.settings.ids:
            key = 'config.' + id
            if key in self.window.ui.menu:
                if id in self.window.core.settings.active and self.window.core.settings.active[id]:
                    self.window.ui.menu['config.' + id].setChecked(True)
                else:
                    self.window.ui.menu['config.' + id].setChecked(False)

    def open_section(self, section: str):
        """
        Open settings section

        :param section: section id
        """
        id = 'settings'
        tab = self.get_tab_idx(section)
        if tab is not None:
            self.set_by_tab(tab)

        self.window.ui.dialogs.open(
            'config.' + id,
            width=self.width,
            height=self.height,
        )
        self.editor.init(id)
        self.window.core.settings.active[id] = True
        self.window.controller.layout.restore_settings()

        # update menu
        self.update()

    def toggle_editor(self, id: str):
        """
        Toggle settings dialog

        :param id: settings id
        """
        if id in self.window.core.settings.active and self.window.core.settings.active[id]:
            self.close_window(id)
        else:
            self.window.ui.dialogs.open('config.' + id, width=self.width, height=self.height)
            self.editor.init(id)
            self.window.core.settings.active[id] = True

            # if no API key, focus on API key input
            if self.window.core.config.get('api_key') is None or self.window.core.config.get('api_key') == '':
                self.window.ui.config['config']['api_key'].setFocus()

            self.window.controller.layout.restore_settings()  # restore previous selected settings tab

        # update menu
        self.update()

    def set_by_tab(self, idx: int):
        """
        Set current section by tab index

        :param idx: tab index
        """
        section_idx = 0
        for section_id in self.editor.get_sections():
            if section_idx == idx:
                break
            section_idx += 1
        current = self.window.ui.models['settings.section.list'].index(idx, 0)
        self.window.ui.nodes['settings.section.list'].setCurrentIndex(current)
        self.window.ui.tabs['settings.section'].setCurrentIndex(idx)

    def get_tab_idx(self, section_id: str) -> int:
        """
        Get section tab index

        :param section_id: plugin id
        :return: tab index
        """
        section_idx = None
        i = 0
        for id in self.editor.get_sections():
            if id == section_id:
                section_idx = i
                break
            i += 1
        return section_idx

    def toggle_file_editor(self, file: str = None):
        """
        Toggle file editor

        :param file: JSON file to load
        """
        id = 'editor'
        current_file = self.window.ui.dialog['config.editor'].file

        # show/hide restart required label
        if file.endswith('.css'):
            self.window.ui.nodes['dialog.editor.label'].setVisible(False)
        else:
            self.window.ui.nodes['dialog.editor.label'].setVisible(True)

        if id in self.window.core.settings.active and self.window.core.settings.active[id]:
            if current_file == file:
                self.window.ui.dialogs.close('config.' + id)
                self.window.core.settings.active[id] = False
            else:
                self.window.core.settings.load_editor(file)  # load file to editor
                self.window.ui.dialog['config.editor'].file = file
                self.prepare_file_editor(file)
        else:
            self.window.core.settings.load_editor(file)  # load file to editor
            self.prepare_file_editor(file)
            self.window.ui.dialogs.open(
                'config.' + id,
                width=self.width,
                height=self.height,
            )
            self.window.core.settings.active[id] = True

        # update menu
        self.update()

    def prepare_file_editor(self, file: str):
        """
        Prepare file editor

        :param file: JSON/CSS file to load
        """
        return  # allow defaults to all files
        if file.endswith('.css'):
            self.window.ui.nodes['editor.btn.default'].setVisible(True)
        else:
            self.window.ui.nodes['editor.btn.default'].setVisible(False)

    def close(self, id: str):
        """
        Close menu

        :param id: settings window id
        """
        if id in self.window.ui.menu:
            self.window.ui.menu[id].setChecked(False)

        allowed_settings = ['settings']
        if id in allowed_settings and id in self.window.ui.menu:
            self.window.ui.menu[id].setChecked(False)

    def close_window(self, id: str):
        """
        Close window

        :param id: settings window id
        """
        if id in self.window.core.settings.active and self.window.core.settings.active[id]:
            self.window.ui.dialogs.close('config.' + id)
            self.window.core.settings.active[id] = False

    def open_config_dir(self):
        """Open user config directory"""
        if os.path.exists(self.window.core.config.path):
            self.window.controller.files.open_dir(self.window.core.config.path)
        else:
            self.window.ui.status('Config directory not exists: {}'.format(self.window.core.config.path))

    def welcome_settings(self):
        """Open settings at first launch (if no API key yet)"""
        self.open_section("general")
        self.window.ui.config['config']['api_key'].setFocus()
        self.window.ui.dialogs.close('info.start')

    def reload(self):
        """Reload settings"""
        self.setup()
        self.window.ui.dialogs.app_log.update()
