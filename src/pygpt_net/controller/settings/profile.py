#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.12.28 04:00:00                  #
# ================================================== #

import os
from pathlib import Path
from typing import Optional, Dict, Any, Union

from PySide6.QtCore import Slot, QTimer
from PySide6.QtGui import QAction

from pygpt_net.core.types import MODE_CHAT
from pygpt_net.utils import trans


class Profile:
    def __init__(self, window=None):
        """
        Profile controller

        :param window: Window instance
        """
        self.window = window
        self.dialog = False
        self.width = 500
        self.height = 500
        self.initialized = False
        self.dialog_initialized = False
        self.before_theme = None
        self.before_language = None

    def setup(self):
        """Setup profile"""
        self.setup_menu()
        if not self.dialog_initialized:
            self.window.profiles.setup()  # widget dialog
            self.dialog_initialized = True

    def switch_current(self, uuid: str):
        """
        Switch to current profile (force reload)

        :param uuid: Profile UUID
        """
        self.switch(uuid, force=True, save_current=False)

    def switch(
            self,
            uuid: str,
            force: bool = False,
            save_current: bool = True,
            on_finish: Optional[callable] = None,
            is_create: bool = False,
    ):
        """
        Switch profile

        :param uuid: Profile UUID
        :param force: Force switch
        :param save_current: Save current profile
        :param on_finish: Callback function to call after switch
        :param is_create: Is called from create profile
        """
        current = self.window.core.config.profile.get_current()
        if uuid == current and not force:
            self.update_menu()
            return

        profile = self.window.core.config.profile.get(uuid)
        if profile is None:
            self.window.ui.dialogs.alert("Profile not found!")
            return
        self.window.update_status("Please wait...")

        if save_current:
            print("Saving all settings in current profile...")
            self.window.controller.settings.save_all(force=True)
        self.window.core.config.profile.set_current(uuid)

        path = self.window.core.config.profile.get_current_workdir()
        if path and os.path.exists(path):
            self.window.controller.settings.workdir.update(
                path,
                force=True,
                profile_name=profile['name'],
                is_create=is_create,
            )
        else:
            self.after_update(profile['name'])

    def after_update(
            self,
            name: str,
    ):
        """
        After profile switch

        :param name: Profile name
        """
        self.update_menu()
        self.update_list()
        self.window.ui.update_title()
        self.window.update_status(trans("dialog.profile.status.changed") + ": " + name)
        self.window.ui.dialogs.close('profile.item')
        self.select_current_on_list()

    def select_current_on_list(self):
        """Select current profile on list"""
        current = self.window.core.config.profile.get_current()
        profiles = self.get_profiles()
        for idx, uuid in enumerate(profiles):
            if uuid == current:
                index = self.window.ui.models['profile.list'].index(idx, 0)
                self.window.ui.nodes['profile.list'].setCurrentIndex(index)
                break

    def get_profiles(self) -> Dict[str, Dict[str, Any]]:
        """
        Get profiles

        :return: profiles dict
        """
        return self.window.core.config.profile.get_all()

    def new(self):
        """New profile dialog"""
        ui = self.window.ui
        ui.nodes['dialog.profile.checkbox.switch'].setVisible(True)
        ui.dialog['profile.item'].checkboxes.setVisible(False)
        ui.dialog['profile.item'].id = 'profile'
        ui.dialog['profile.item'].uuid = None
        ui.dialog['profile.item'].mode = 'create'
        ui.dialog['profile.item'].path = ""
        ui.dialog['profile.item'].input.setText("")
        ui.dialog['profile.item'].prepare()
        ui.dialog['profile.item'].show()

    def edit(self, uuid: str):
        """
        Edit profile dialog

        :param uuid: profile UUID
        """
        ui = self.window.ui
        ui.nodes['dialog.profile.checkbox.switch'].setVisible(False)
        profile = self.window.core.config.profile.get(uuid)
        ui.dialog['profile.item'].checkboxes.setVisible(False)
        if profile is None:
            ui.dialogs.alert("Profile not found!")
            return
        ui.dialog['profile.item'].id = 'profile'
        ui.dialog['profile.item'].uuid = uuid
        ui.dialog['profile.item'].mode = 'edit'
        ui.dialog['profile.item'].path = profile['workdir'].replace("%HOME%", str(Path.home()))
        ui.dialog['profile.item'].input.setText(profile['name'])
        ui.dialog['profile.item'].prepare()
        ui.dialog['profile.item'].show()

    def open(self, force: bool = False):
        """
        Open profiles editor

        :param force: force open
        """
        if not self.initialized:
            self.setup()
            self.initialized = True
        if not self.dialog or force:
            self.update_menu()
            self.update_list()
            self.window.ui.dialogs.open(
                'profile.editor',
                width=self.width,
                height=self.height,
            )
            self.dialog = True
            self.select_current_on_list()

    def close(self):
        """Close profile dialog"""
        if self.dialog:
            self.window.ui.dialogs.close('profile.editor')
            self.dialog = False

    def toggle_editor(self):
        """Toggle profile dialog"""
        if self.dialog:
            self.close()
        else:
            self.open()

    def handle_update(
            self,
            mode: str,
            name: str,
            path: str,
            uuid: Optional[str] = None
    ):
        """
        Handle new/edit profile dialog

        :param mode: mode (create | update | duplicate)
        :param name: profile name
        :param path: profile workdir path
        :param uuid: profile UUID (update and duplicate only)
        """
        ui = self.window.ui
        fs = self.window.core.filesystem
        cfg = self.window.core.config.profile
        current = cfg.get_current()
        name_stripped = name.strip()
        path_stripped = path.strip()
        if name_stripped == "":
            ui.dialogs.alert(trans("dialog.profile.alert.name.empty"))
            return
        if path_stripped == "":
            ui.dialogs.alert(trans("dialog.profile.alert.path.empty"))
            return

        p = Path(path_stripped)
        if not p.is_dir():
            ui.dialogs.alert(trans("dialog.profile.alert.path.not_exists"))
            return

        if not fs.is_directory_empty(path_stripped):
            if not fs.is_workdir_in_path(path_stripped):
                ui.dialogs.alert(trans("dialog.profile.alert.duplicate.not_empty"))
                return

        if mode == 'create':
            uuid = cfg.add(name_stripped, path_stripped)
            self.window.update_status(trans("dialog.profile.status.created"))
            if ui.nodes['dialog.profile.checkbox.switch'].isChecked():
                QTimer.singleShot(100, lambda: self.after_create(uuid))
                return

        elif mode == 'edit':
            profile = cfg.get(uuid)
            old_path = profile['workdir'].replace("%HOME%", str(Path.home()))
            cfg.update_profile(uuid, name_stripped, path_stripped)
            self.window.update_status(trans("dialog.profile.status.updated"))
            if uuid == current:
                self.window.ui.update_title()
                if old_path != path_stripped:
                    self.switch(uuid, force=True)

        elif mode == 'duplicate':
            if not fs.is_directory_empty(path_stripped):
                ui.dialogs.alert(trans("dialog.workdir.change.empty.alert"))
                return

            profiles = self.get_profiles()
            if uuid not in profiles:
                ui.dialogs.alert(trans("dialog.profile.alert.src.empty"))
                return
            profile = profiles[uuid]

            if profile['workdir'].replace("%HOME%", str(Path.home())) == path_stripped:
                ui.dialogs.alert(trans("dialog.profile.alert.path.same"))
                return

            include_datadir = self.is_include_datadir()
            include_db = self.is_include_db()
            src_path = profile['workdir'].replace("%HOME%", str(Path.home()))
            space_required = fs.get_directory_size(src_path, human_readable=False)
            if not include_datadir:
                space_required -= fs.get_datadir_size(src_path, human_readable=False)
            if not include_db:
                space_required -= fs.get_db_size(src_path, human_readable=False)
            space_free = fs.get_free_disk_space(path_stripped, human_readable=False)
            if space_required > space_free:
                ui.dialogs.alert(trans("dialog.workdir.result.no_free_space").format(
                    required=fs.sizeof_fmt(space_required),
                    free=fs.sizeof_fmt(space_free),
                ))
                return

            self.duplicate(uuid, name_stripped, path_stripped)
            self.window.update_status(trans("dialog.profile.status.duplicated"))

        self.window.ui.dialogs.close('profile.item')
        self.update_menu()
        self.update_list()

    def after_create(self, uuid: str):
        """
        After profile creation

        :param uuid: profile UUID
        """
        self.before_theme = self.window.core.config.get("theme")
        self.before_language = self.window.core.config.get("lang")
        self.switch(
            uuid,
            force=True,
            on_finish=self.after_create_finish,
            is_create=True
        )

    def after_create_finish(self, uuid: str):
        """
        After profile creation

        :param uuid: profile UUID
        """
        self.window.ui.dialogs.close('profile.item')
        self.update_menu()
        self.update_list()
        self.window.ui.update_title()
        self.window.controller.mode.select(MODE_CHAT)

    def dismiss_update(self):
        """Dismiss update dialog"""
        self.window.ui.dialogs.close('profile.item')

    def edit_by_idx(self, idx: int):
        """
        Rename profile by index

        :param idx: profile index
        """
        uuid = self.get_id_by_idx(idx)
        self.edit(uuid)

    def select_by_idx(self, idx: int):
        """
        Select profile by index

        :param idx: profile index
        """
        uuid = self.get_id_by_idx(idx)
        self.switch(uuid)

    def delete_by_idx(self, idx: Union[int, list], force: bool = False):
        """
        Delete profile by index

        :param idx: profile index or list of indexes
        :param force: force delete
        """
        uuids = []
        ids = idx if isinstance(idx, list) else [idx]
        for i in ids:
            uuid = self.get_id_by_idx(i)
            uuids.append(uuid)
        current = self.window.core.config.profile.get_current()
        for uuid in list(uuids):
            if uuid == current:
                if len(uuids) == 1:
                    self.window.ui.dialogs.alert(trans("dialog.profile.alert.delete.current"))
                    return
                else:
                    uuids.remove(uuid)  # skip current
        if not force:
            self.window.ui.dialogs.confirm(
                type='profile.delete',
                id=idx,
                msg=trans('confirm.profile.delete'),
            )
            return
        self.delete(uuids)

    def delete(self, uuid: Union[str, list]):
        """
        Delete profile (remove only)

        :param uuid: profile ID or list of IDs
        """
        profiles = self.get_profiles()
        updated = False
        ids = uuid if isinstance(uuid, list) else [uuid]
        for uuid in ids:
            if uuid in profiles:
                profile = profiles[uuid]
                name = profile['name']
                if self.window.core.config.profile.remove(uuid):
                    updated = True
                    self.window.update_status(trans("dialog.profile.status.removed") + ": " + name)
        if updated:
            self.update_list()
            self.update_menu()

    def delete_all_by_idx(self, idx: Union[int, list], force: bool = False):
        """
        Delete profile with files by index

        :param idx: profile index or list of indexes
        :param force: force delete
        """
        uuids = []
        ids = idx if isinstance(idx, list) else [idx]
        for i in ids:
            uuid = self.get_id_by_idx(i)
            uuids.append(uuid)
        current = self.window.core.config.profile.get_current()
        for uuid in list(uuids):
            if uuid == current:
                if len(uuids) == 1:
                    self.window.ui.dialogs.alert(trans("dialog.profile.alert.delete.current"))
                    return
                else:
                    uuids.remove(uuid)  # skip current
        if not force:
            self.window.ui.dialogs.confirm(
                type='profile.delete.all',
                id=idx,
                msg=trans('confirm.profile.delete_all'),
            )
            return
        self.delete_all(uuids)

    def duplicate_by_idx(self, idx: int):
        """
        Duplicate profile by index

        :param idx: profile index
        """
        uuid = self.get_id_by_idx(idx)
        profile = self.window.core.config.profile.get(uuid)
        dialog = self.window.ui.dialog['profile.item']
        dialog.checkboxes.setVisible(True)
        if profile is None:
            self.window.ui.dialogs.alert("Profile not found!")
            return
        self.window.ui.nodes['dialog.profile.checkbox.switch'].setVisible(True)

        dialog.id = 'profile'
        dialog.uuid = uuid
        dialog.mode = 'duplicate'
        dialog.path = ""
        dialog.input.setText(profile['name'] + " - copy")
        dialog.prepare()
        dialog.show()

    def delete_all(self, uuid: Union[str, list]):
        """
        Delete profile with files

        :param uuid: profile ID or list of IDs
        """
        ids = uuid if isinstance(uuid, list) else [uuid]
        batch = False
        if len(ids) > 1:
            batch = True
        if not batch:
            self.window.controller.settings.workdir.delete_files(uuid)
        else:
            self.window.controller.settings.workdir.delete_files(ids, batch=batch)

    @Slot(str)
    def after_delete(self, name: str):
        """
        After files deletion (called from worker)

        :param name: profile name
        """
        self.window.update_status(trans("dialog.profile.status.deleted") + ": " + name)
        self.update_list()
        self.update_menu()

    def duplicate(
            self,
            uuid: str,
            new_name: str,
            new_path: str
    ):
        """
        Duplicate profile

        :param uuid: profile ID
        :param new_name: new profile name
        :param new_path: new profile path
        """
        self.window.controller.settings.workdir.duplicate(
            profile_uuid=uuid,
            new_name=new_name,
            new_path=new_path,
        )

    @Slot(str, str)
    def after_duplicate(self, uuid: str, name: str):
        """
        After profile duplication (called from worker)

        :param uuid: new profile ID
        :param name: new profile name
        """
        self.window.update_status("Files copied to new profile: " + name)
        self.update_list()
        self.update_menu()
        if self.window.ui.nodes['dialog.profile.checkbox.switch'].isChecked():
            self.switch(uuid, force=True)

    def reset(self, uuid: Union[str, list]):
        """
        Reset profile

        :param uuid: profile ID or list of IDs
        """
        ids = uuid if isinstance(uuid, list) else [uuid]
        batch = False
        if len(ids) > 1:
            batch = True
        if not batch:
            self.window.controller.settings.workdir.reset(uuid)
        else:
            self.window.controller.settings.workdir.reset(ids, batch=batch)

    def reset_by_idx(self, idx: Union[int, list], force: bool = False):
        """
        Reset profile by index

        :param idx: profile index or list of indexes
        :param force: force reset
        """
        uuids = []
        ids = idx if isinstance(idx, list) else [idx]
        for i in ids:
            uuid = self.get_id_by_idx(i)
            uuids.append(uuid)
        if not force:
            self.window.ui.dialogs.confirm(
                type='profile.reset',
                id=idx,
                msg=trans('confirm.profile.reset'),
            )
            return
        self.reset(uuids)

    def is_include_db(self):
        """Get include db"""
        return self.window.ui.nodes['dialog.profile.checkbox.db'].isChecked()

    def is_include_datadir(self):
        """Get include datadir"""
        return self.window.ui.nodes['dialog.profile.checkbox.data'].isChecked()

    def get_id_by_idx(self, idx: int) -> str:
        """
        Get profile id by index

        :param idx: profile index
        """
        profiles = self.get_profiles()
        if len(profiles) > idx:
            return list(profiles.keys())[idx]

    def update_list(self):
        """Reload profile list"""
        items = self.get_profiles()
        self.window.profiles.update_list("profile.list", items)

    def setup_menu(self):
        """Setup profile menu"""
        profiles = self.window.core.config.profile.get_all()
        current = self.window.core.config.profile.get_current()
        ui_menu = self.window.ui.menu
        suffix = trans("profile.current.suffix")
        for uuid, profile in profiles.items():
            if uuid not in ui_menu['config.profiles']:
                name = profile['name']
                checked = uuid == current
                text = f"{name} {suffix}" if checked else name
                action = QAction(text, self.window, checkable=True)
                action.setChecked(checked)
                action.triggered.connect(lambda checked=False, u=uuid: self.window.controller.settings.profile.switch(u))
                ui_menu['config.profiles'][uuid] = action
                ui_menu['config.profile'].addAction(action)

    def update_menu(self):
        """Update menu"""
        profiles = self.window.core.config.profile.get_all()
        current = self.window.core.config.profile.get_current()
        ui_menu = self.window.ui.menu
        profile_actions = ui_menu['config.profiles']
        suffix = trans("profile.current.suffix")

        for uuid in list(profile_actions.keys()):
            if uuid in profiles:
                name = profiles[uuid]['name']
                is_current = uuid == current
                text = f"{name} {suffix}" if is_current else name
                action = profile_actions[uuid]
                action.setText(text)
                action.setChecked(is_current)

        for uuid, profile in profiles.items():
            if uuid not in profile_actions:
                name = profile['name']
                is_current = uuid == current
                text = f"{name} {suffix}" if is_current else name
                action = QAction(text, self.window, checkable=True)
                action.setChecked(is_current)
                action.triggered.connect(lambda checked=False, u=uuid: self.window.controller.settings.profile.switch(u))
                profile_actions[uuid] = action
                ui_menu['config.profile'].addAction(action)

        for uuid in list(profile_actions.keys()):
            if uuid not in profiles:
                ui_menu['config.profile'].removeAction(profile_actions[uuid])
                del profile_actions[uuid]