#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.25 12:00:00                  #
# ================================================== #

import os
from pathlib import Path

from PySide6.QtWidgets import QApplication

from pygpt_net.controller.settings.editor import Editor
from pygpt_net.utils import trans


class Settings:
    def __init__(self, window=None):
        """
        Settings controller

        :param window: Window instance
        """
        self.window = window
        self.editor = Editor(window)
        self.width = 800
        self.height = 500
        self.is_workdir_dialog = False
        self.migrating_workdir = False

    def setup(self):
        """Set up settings editor"""
        self.editor.setup()

    def load(self):
        """Load settings"""
        self.editor.load()

    def save_all(self):
        """Save all settings and data"""
        info = trans('info.settings.all.saved')
        self.window.core.config.save()
        self.window.core.presets.save_all()
        self.window.controller.notepad.save_all()
        self.window.controller.calendar.save_all()
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

    def change_workdir(self):
        """Change working directory (open dialog)"""
        if self.is_workdir_dialog:
            self.window.ui.dialogs.close('workdir.change')
            self.is_workdir_dialog = False
        else:
            size_needed = self.window.core.filesystem.get_directory_size(self.window.core.config.get_user_path())
            self.window.ui.nodes['workdir.change.info'].setText(trans("dialog.workdir.tip").format(size=size_needed))
            self.window.ui.nodes['workdir.change.path'].setText(self.window.core.config.get_user_path())
            self.window.ui.dialogs.open(
                'workdir.change',
                width=600,
                height=180,
            )
            self.is_workdir_dialog = True

    def update_workdir(self, path: str):
        """
        Switch working directory to the existing one

        :param path: existing working directory
        """
        lock_file = os.path.join(self.window.core.config.get_base_workdir(), 'path.lock')  # put "path.lock"
        lock_path = path.replace(str(Path.home()), "%HOME%")
        if path == self.window.core.config.get_base_workdir():
            lock_path = ""  # set empty if default dir
        with open(lock_file, 'w', encoding='utf-8') as f:
            f.write(lock_path)  # new path
        self.window.core.config.set_workdir(path, reload=True)

        # patch and reload
        self.window.core.db.close()  # close current database
        self.window.core.db.init(force=True)  # re-init database with new path
        self.window.core.patch()
        self.window.core.ctx.current = None
        self.window.core.presets.load()
        self.window.controller.ctx.setup()
        self.window.controller.ctx.update()
        self.window.controller.ctx.refresh()
        self.window.controller.presets.refresh()
        self.window.controller.assistant.setup()
        self.window.controller.attachment.setup()
        self.window.controller.idx.setup()
        self.window.controller.notepad.setup()
        self.window.controller.calendar.setup()
        self.window.controller.plugins.settings.setup()
        self.window.controller.painter.setup()

        # show result
        self.window.ui.nodes['workdir.change.status'].setText(trans("dialog.workdir.result.success").format(path=path))
        self.window.ui.dialogs.alert(trans("dialog.workdir.result.success").format(path=path))

    def migrate_workdir(self, path: str, force: bool = False):
        """
        Migrate working directory

        :param path: new working directory
        :param force: force migration
        """
        if self.migrating_workdir:
            self.window.ui.dialogs.alert("Workdir migration in progress...")
            return

        current = self.window.core.config.get_user_path()
        if current == path:
            self.window.ui.dialogs.alert(trans("dialog.workdir.result.same_directory"))
            self.migrating_workdir = False
            self.window.ui.nodes['workdir.change.status'].setVisible(False)
            return

        # check if path is not empty
        if self.window.core.filesystem.is_workdir_in_path(path):
            self.window.ui.dialogs.confirm(
                type='workdir.update',
                id=path,
                msg=trans("dialog.workdir.update.confirm").format(path=path)
            )
            return

        if not force:
            self.window.ui.dialogs.confirm(
                type='workdir.change',
                id=path,
                msg=trans("dialog.workdir.change.confirm").format(path=path)
            )
            return

        self.window.ui.nodes['workdir.change.status'].setText("")
        self.window.ui.nodes['workdir.change.status'].setVisible(False)
        self.migrating_workdir = True
        print("Migrating workdir from: ", current, " to: ", path)

        # check if path exists
        if not os.path.exists(path) or not os.path.isdir(path):
            self.window.ui.dialogs.alert(trans("dialog.workdir.result.directory_not_exists"))
            self.window.ui.nodes['workdir.change.status'].setVisible(False)
            self.migrating_workdir = False
            return

        # check free space
        space_required = self.window.core.filesystem.get_directory_size(current, human_readable=False)
        space_free = self.window.core.filesystem.get_free_disk_space(path, human_readable=False)
        space_required_human = self.window.core.filesystem.get_directory_size(current)
        space_free_human = self.window.core.filesystem.get_free_disk_space(path)
        if space_required > space_free:
            self.window.ui.dialogs.alert(trans("dialog.workdir.result.no_free_space").format(
                required=space_required_human,
                free=space_free_human,
            ))
            self.migrating_workdir = False
            self.window.ui.nodes['workdir.change.status'].setVisible(False)
            return

        self.window.ui.nodes['workdir.change.status'].setText(trans("dialog.workdir.result.wait"))
        self.window.ui.nodes['workdir.change.status'].setVisible(True)
        self.window.core.debug.info("Migrating workdir from: {} to: {}".format(current, path))
        QApplication.processEvents()

        # copy files
        try:
            result = self.window.core.filesystem.migrate_workdir(current, path)
        except Exception as e:
            self.window.core.debug.log(e)
            self.window.ui.dialogs.alert(e)
            print("Error migrating workdir: ", e)
            result = False

        if result:
            try:
                # remove old workdir
                self.window.core.debug.info("Clearing old workdir: {}".format(current))
                self.window.core.filesystem.clear_workdir(current)
                self.update_workdir(path)  # update workdir
            except Exception as e:
                self.window.core.debug.log(e)
                self.window.ui.dialogs.alert(e)
                print("Error migrating workdir: ", e)

                # restore current if failed
                lock_file = os.path.join(self.window.core.config.get_base_workdir(), 'path.lock')  # put "path.lock"
                lock_path = current.replace(str(Path.home()), "%HOME%")
                if path == self.window.core.config.get_base_workdir():
                    lock_path = ""  # set empty if default dir
                with open(lock_file, 'w', encoding='utf-8') as f:
                    f.write(lock_path)  # new path
        else:
            self.window.ui.nodes['workdir.change.status'].setText(trans("dialog.workdir.result.failed"))
            self.window.ui.dialogs.alert(trans("dialog.workdir.result.failed"))

            # restore current if failed
            lock_file = os.path.join(self.window.core.config.get_base_workdir(), 'path.lock')  # put "path.lock"
            lock_path = current.replace(str(Path.home()), "%HOME%")
            if path == self.window.core.config.get_base_workdir():
                lock_path = ""  # set empty if default dir
            with open(lock_file, 'w', encoding='utf-8') as f:
                f.write(lock_path)  # new path

        self.migrating_workdir = False
        self.window.core.debug.info("Finished migrating workdir from: {} to: {}".format(current, path))

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
        if id in self.window.core.settings.active and self.window.core.settings.active[id]:
            if current_file == file:
                self.window.ui.dialogs.close('config.' + id)
                self.window.core.settings.active[id] = False
            else:
                self.window.core.settings.load_editor(file)  # load file to editor
                self.window.ui.dialog['config.editor'].file = file
        else:
            self.window.core.settings.load_editor(file)  # load file to editor
            self.window.ui.dialogs.open(
                'config.' + id,
                width=self.width,
                height=self.height,
            )
            self.window.core.settings.active[id] = True

        # update menu
        self.update()

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
