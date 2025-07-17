#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.18 00:00:00                  #
# ================================================== #

import copy
import os
from pathlib import Path
from typing import Optional
from uuid import uuid4

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from pygpt_net.utils import trans


class WorkerSignals(QObject):
    """
    Signals for worker to communicate with main thread.
    """
    finished = Signal()  # when worker is finished
    deleted = Signal(str)  # after deleting profile
    duplicated = Signal(str, str)  # after duplicating profile (str: new_uuid, str: new_name)
    error = Signal(str)  # when error occurs
    hideStatus = Signal()  # hide status in dialog
    updateStatus = Signal(str)    # update status in dialog
    updateGlobalStatus = Signal(str)  # update global status
    alert = Signal(object)        # dialog alert
    reload = Signal()             # on reload components (e.g. after workdir change)
    confirm = Signal(str, str, str)  # confirm dialog (action, path, message)
    restored = Signal(str)        # after restoring workdir
    updated = Signal(str)         # after updating workdir
    switch = Signal(str)       # switch to profile (after reset)


class WorkdirWorker(QObject, QRunnable):
    """Worker for handling workdir operations in a separate thread."""
    def __init__(
            self,
            window,
            action: str,
            path: str = None,
            force: bool = False,
            current: Optional[str] = None,
            profile_name: Optional[str] = None,
            profile_uuid: Optional[str] = None,
            profile_new_name: Optional[str] = None,
            profile_new_path: Optional[str] = None,
    ):
        QObject.__init__(self)
        QRunnable.__init__(self)
        self.window = window
        self.action = action
        self.path = path
        self.force = force
        self.current = current
        self.profile_name = profile_name
        self.profile_uuid = profile_uuid
        self.profile_new_name = profile_new_name
        self.profile_new_path = profile_new_path
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        try:
            if self.action == "update":
                self.worker_update()
            elif self.action == "migrate":
                self.worker_migrate()
            elif self.action == "restore":
                self.worker_restore()
            elif self.action == "delete":
                self.worker_delete_files()
            elif self.action == "duplicate":
                self.worker_duplicate()
            elif self.action == "reset":
                self.worker_reset()
            else:
                self.signals.error.emit(f"Unknown action: {self.action}")
        except Exception as e:
            self.window.core.debug.log(e)
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()

    def worker_delete_files(self):
        """Delete files and directories associated with the profile"""
        uuid = self.profile_uuid
        profiles = self.window.controller.settings.profile.get_profiles()
        remove_datadir = True
        remove_db = True
        if uuid in profiles:
            profile = profiles[uuid]
            name = profile['name']
            path = profile['workdir'].replace("%HOME%", str(Path.home()))
            # remove profile
            if self.window.core.config.profile.remove(uuid):
                if not os.path.exists(path) or not os.path.isdir(path):
                    self.signals.alert.emit(trans("dialog.profile.alert.path.not_exists"))
                    return
                print("Clearing workdir: ", path)
                self.window.core.filesystem.clear_workdir(
                    path,
                    remove_db=remove_db,
                    remove_datadir=remove_datadir,
                )
                self.signals.deleted.emit(name)

    def worker_duplicate(self):
        """Duplicate profile"""
        uuid = self.profile_uuid
        new_name = self.profile_new_name
        new_path = self.profile_new_path

        profiles = self.window.controller.settings.profile.get_profiles()
        if uuid not in profiles:
            self.signals.alert.emit("Profile not found!")
            return
        profile = profiles[uuid]

        copy_datadir = self.window.controller.settings.profile.is_include_datadir()
        copy_db = self.window.controller.settings.profile.is_include_db()

        # make copy
        duplicate = copy.deepcopy(profile)
        new_uuid = str(uuid4())
        duplicate['name'] = new_name
        duplicate['workdir'] = new_path
        self.window.core.config.profile.append(new_uuid, duplicate)

        # copy files from workdir
        path_from = profile['workdir'].replace("%HOME%", str(Path.home()))
        path_to = new_path
        print("Copying all files from {} to: {}".format(path_from, path_to))
        self.signals.updateGlobalStatus.emit("Copying files...")
        result = self.window.core.filesystem.copy_workdir(
            path_from,
            path_to,
            copy_db=copy_db,
            copy_datadir=copy_datadir,
        )
        if not result:
            self.signals.alert.emit("Error copying files!")
            self.signals.updateGlobalStatus.emit("Error copying files!")
            return
        print("[OK] All files copied successfully.")
        self.signals.duplicated.emit(new_uuid, new_name)

    def worker_reset(self):
        """Reset profile"""
        uuid = self.profile_uuid
        profiles = self.window.controller.settings.profile.get_profiles()
        current = self.window.core.config.profile.get_current()
        remove_datadir = False
        remove_db = True
        if uuid in profiles:
            profile = profiles[uuid]
            path = profile['workdir'].replace("%HOME%", str(Path.home()))
            if not os.path.exists(path) or not os.path.isdir(path):
                self.signals.alert.emit("Directory not exists!")
                return
            print("Clearing workdir: ", path)
            self.window.core.db.close()
            self.window.core.filesystem.clear_workdir(
                path,
                remove_db=remove_db,
                remove_datadir=remove_datadir,
            )
            if uuid == current:
                self.signals.switch.emit(uuid)  # switch to profile
            self.signals.updateGlobalStatus.emit("Profile cleared: " + profile['name'])

    def worker_update(self):
        """Switch working directory to the existing one"""
        print("\n====================")
        print("Changing workdir to: ", self.path)
        print("====================\n")
        current_path = self.window.core.config.get_user_path()
        default_path = self.window.core.config.get_base_workdir()

        if self.force:
            self.signals.updateStatus.emit(trans("dialog.workdir.result.wait"))

        lock_file = os.path.join(default_path, 'path.cfg')  # put "path.cfg"
        lock_path = self.path.replace(str(Path.home()), "%HOME%")
        if self.path == default_path:
            lock_path = ""  # set empty if default dir
        with open(lock_file, 'w', encoding='utf-8') as f:
            f.write(lock_path)

         # update path in current profile
        self.window.core.config.profile.update_current_workdir(self.path)

        # reload config
        self.window.core.config.set_workdir(self.path, reload=True)
        self.window.core.config.set('license.accepted', True)  # accept license to prevent show dialog again

        # reload components
        if self.force:
            try:
                self.signals.reload.emit()
                success_msg = trans("dialog.workdir.result.success").format(path=self.path)
                self.signals.updateStatus.emit(success_msg)
                self.signals.alert.emit(success_msg)
            except Exception as e:
                self.window.core.debug.log(e)
                self.signals.alert.emit(str(e))
                print("Error reloading components: ", e)
                self.worker_restore(custom_current=current_path)
                self.window.controller.reloading = False  # unlock
        else:
            # always reload
            self.signals.reload.emit()

        # update profile after workdir change
        if self.profile_name:
            self.signals.updated.emit(self.profile_name)

    def worker_migrate(self):
        """Migrate working directory"""
        if self.window.controller.settings.workdir.busy:
            self.signals.alert.emit("Workdir migration in progress...")
            return

        # check if not the same directory
        current = self.window.core.config.get_user_path()
        if current == self.path:
            self.signals.alert.emit(trans("dialog.workdir.result.same_directory"))
            self.window.controller.settings.workdir.busy = False
            self.signals.hideStatus.emit()
            return

        # check if path is not already a workdir
        if self.window.core.filesystem.is_workdir_in_path(self.path):
            msg = trans("dialog.workdir.update.confirm").format(path=self.path)
            self.signals.confirm.emit("workdir.update", self.path, msg)
            return

        # check if path is empty
        if not self.window.core.filesystem.is_directory_empty(self.path):
            self.signals.alert.emit(trans("dialog.workdir.change.empty.alert"))
            return

        # confirm move
        if not self.force:
            msg = trans("dialog.workdir.change.confirm").format(path=self.path)
            self.signals.confirm.emit("workdir.change", self.path, msg)
            return

        self.signals.hideStatus.emit()
        self.window.controller.settings.workdir.busy = True
        print("Migrating workdir from: ", current, " to: ", self.path)

        # check if path exists
        if not os.path.exists(self.path) or not os.path.isdir(self.path):
            self.signals.alert.emit(trans("dialog.workdir.result.directory_not_exists"))
            self.signals.hideStatus.emit()
            self.window.controller.settings.workdir.busy = False
            return

        # check free space
        space_required = self.window.core.filesystem.get_directory_size(current, human_readable=False)
        space_free = self.window.core.filesystem.get_free_disk_space(self.path, human_readable=False)
        if space_required > space_free:
            self.signals.alert.emit(trans("dialog.workdir.result.no_free_space").format(
                required=self.window.core.filesystem.get_directory_size(current),
                free=self.window.core.filesystem.get_free_disk_space(self.path),
            ))
            self.window.controller.settings.workdir.busy = False
            self.signals.hideStatus.emit()
            return

        # copy workdir
        try:
            result = self.window.core.filesystem.copy_workdir(current, self.path)
        except Exception as e:
            self.window.core.debug.log(e)
            self.signals.alert.emit(str(e))
            print("Error migrating workdir: ", e)
            result = False

        if result:
            try:
                # remove old workdir
                self.window.core.debug.info("Clearing old workdir: {}".format(current))
                try:
                    # allow errors here
                    self.window.core.filesystem.clear_workdir(current)
                except Exception as e:
                    self.window.core.debug.log(e)
                    print("Error clearing old workdir: ", e)

                  # update workdir to new path
                self.worker_update()
                success_msg = trans("dialog.workdir.result.success").format(path=self.path)
                print(success_msg)
                self.signals.updateStatus.emit(success_msg)
                self.signals.alert.emit(success_msg)
            except Exception as e:
                self.window.core.debug.log(e)
                self.signals.alert.emit(str(e))
                print("Error migrating workdir: ", e)
                self.worker_restore(custom_current=current)
                self.window.controller.reloading = False
        else:
            self.signals.updateStatus.emit(trans("dialog.workdir.result.failed"))
            self.signals.alert.emit(trans("dialog.workdir.result.failed"))
            self.worker_restore(custom_current=current)
            self.window.controller.reloading = False

        self.window.controller.settings.workdir.busy = False
        self.window.core.debug.info("Finished migrating workdir from: {} to: {}".format(current, self.path))

    def worker_restore(self, custom_current: str = None):
        """
        Restore default working directory

        :param custom_current: custom current working directory (optional)
        """
        current = custom_current if custom_current is not None else self.current
        print("Reverting workdir to: ", current)
        self.window.core.config.set_workdir(current, reload=True)
        default_path = self.window.core.config.get_base_workdir()
        lock_file = os.path.join(default_path, 'path.cfg')
        lock_path = current.replace(str(Path.home()), "%HOME%")
        if current == default_path:
            lock_path = ""
        with open(lock_file, 'w', encoding='utf-8') as f:
            f.write(lock_path)
        self.signals.restored.emit(current)
        self.signals.updateStatus.emit("Failed. Reverted to current workdir: {}".format(current))
        self.signals.reload.emit()
        self.window.core.config.profile.update_current_workdir(current)


class Workdir:
    def __init__(self, window=None):
        """
        Workdir controller

        :param window: window instance
        """
        self.window = window
        self.is_dialog = False
        self.busy = False
        self.worker = None

    def change(self):
        """Change working directory (open dialog)"""
        if self.is_dialog:
            self.window.ui.dialogs.close('workdir.change')
            self.is_dialog = False
        else:
            self.window.ui.dialogs.workdir.prepare()
            self.window.ui.dialogs.workdir.set_path(self.window.core.config.get_user_path())
            self.window.ui.dialogs.workdir.hide_status()
            self.window.ui.dialogs.open(
                'workdir.change',
                width=600,
                height=180,
            )
            self.is_dialog = True

    def run_action(
            self,
            action: str,
            path: str = None,
            force: bool = False,
            current: str = None,
            profile_name: Optional[str] = None,
            profile_uuid: Optional[str] = None,
            profile_new_name: Optional[str] = None,
            profile_new_path: Optional[str] = None,
    ):
        """
        Run action in thread

        :param action: action to perform (update, migrate, restore)
        :param path: path for update or migrate
        :param force: force action (confirm)
        :param current: current working directory (for restore action)
        :param profile_name: profile name (optional, for after update callback)
        :param profile_uuid: profile UUID (optional, for delete files action)
        :param profile_new_name: new profile name (optional, for duplicate action)
        :param profile_new_path: new profile path (optional, for duplicate action)
        """
        self.worker = WorkdirWorker(
            window=self.window,
            action=action,
            path=path,
            force=force,
            current=current,
            profile_name=profile_name,
            profile_uuid=profile_uuid,
            profile_new_name=profile_new_name,
            profile_new_path=profile_new_path,
        )

        # connect signals
        self.worker.signals.updateGlobalStatus.connect(self.window.update_status)
        self.worker.signals.updateStatus.connect(self.window.ui.dialogs.workdir.show_status)
        self.worker.signals.hideStatus.connect(self.window.ui.dialogs.workdir.hide_status)
        self.worker.signals.alert.connect(self.window.ui.dialogs.alert)
        self.worker.signals.reload.connect(self.window.controller.reload)
        self.worker.signals.error.connect(lambda err: self.window.core.debug.log(f"Worker error: {err}"))
        self.worker.signals.confirm.connect(self.window.ui.dialogs.confirm)
        self.worker.signals.restored.connect(lambda current: self.window.ui.dialogs.workdir.set_path(current))
        self.worker.signals.updated.connect(self.window.controller.settings.profile.after_update)
        self.worker.signals.deleted.connect(self.window.controller.settings.profile.after_delete)
        self.worker.signals.duplicated.connect(self.window.controller.settings.profile.after_duplicate)
        self.worker.signals.switch.connect(self.window.controller.settings.profile.switch_current)

        # start worker in thread pool
        self.window.threadpool.start(self.worker)

    def update(
            self,
            path: str,
            force: bool = False,
            profile_name: str = None
    ):
        """
        Switch working directory to the existing one

        :param path: existing working directory
        :param force: force update (confirm)
        :param profile_name: profile name (optional, for future use)
        """
        self.run_action(
            action="update",
            path=path,
            force=force,
            profile_name=profile_name,
        )

    def migrate(
            self,
            path: str,
            force: bool = False
    ):
        """
        Migrate working directory

        :param path: new working directory
        :param force: force migration (confirm)
        """
        self.run_action(
            action="migrate",
            path=path,
            force=force,
        )

    def restore(
            self,
            current: str
    ):
        """
        Restore default working directory

        :param current: current working directory
        """
        self.run_action(
            action="restore",
            current=current,
        )

    def delete_files(
            self,
            profile_uuid: str
    ):
        """
        Delete files and directories associated with the profile

        :param profile_uuid: profile UUID
        """
        self.run_action(
            action="delete",
            profile_uuid=profile_uuid,
        )

    def duplicate(
            self,
            profile_uuid: str,
            new_name: str,
            new_path: str
    ):
        """
        Duplicate profile

        :param profile_uuid: profile UUID to duplicate
        :param new_name: new profile name
        :param new_path: new profile path
        """
        self.run_action(
            action="duplicate",
            profile_uuid=profile_uuid,
            profile_new_name=new_name,
            profile_new_path=new_path,
        )

    def reset(
            self,
            profile_uuid: str
    ):
        """
        Reset profile

        :param profile_uuid: profile UUID to reset
        """
        self.run_action(
            action="reset",
            profile_uuid=profile_uuid,
        )