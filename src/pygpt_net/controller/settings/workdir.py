#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.26 13:00:00                  #
# ================================================== #

import copy
import os
from pathlib import Path
from typing import Optional
from uuid import uuid4

from PySide6.QtCore import QObject, QRunnable, Signal, Slot
from PySide6.QtWidgets import QApplication

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
    after_migrate = Signal(bool, str, str, str)  # result, profile_name, current_path, new_path
    confirm = Signal(str, str, str)  # confirm dialog (action, path, message)
    restored = Signal(str)        # after restoring workdir
    updated = Signal(str)         # after updating workdir
    switch = Signal(str)       # switch to profile (after reset)


class WorkdirWorker(QRunnable):
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
        super().__init__()
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
            if self.action == "migrate":
                self.worker_migrate()
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
            self.cleanup()

    def cleanup(self):
        """Cleanup resources after worker execution."""
        sig = self.signals
        self.signals = None
        if sig is not None:
            try:
                sig.deleteLater()
            except RuntimeError:
                pass

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
                print(f"Clearing workdir: {path}")
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
        print(f"Copying all files from {path_from} to: {path_to}")
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
                self.signals.alert.emit(f"Directory not exists: {path}")
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
            self.signals.updateGlobalStatus.emit(f"Profile cleared: {profile['name']}")

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
        print(f"Migrating workdir from: {current} to: {self.path}...")

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
        self.signals.updateGlobalStatus.emit(trans("dialog.workdir.result.wait"))
        QApplication.processEvents()  # process events to update UI
        try:
            result = self.window.core.filesystem.copy_workdir(current, self.path)
        except Exception as e:
            self.window.core.debug.log(e)
            self.signals.alert.emit(str(e))
            print("Error migrating workdir: ", e)
            result = False

        # reload UI, config, etc.
        self.signals.after_migrate.emit(result, self.profile_name, current, self.path)


class Workdir:
    def __init__(self, window=None):
        """
        Workdir controller

        :param window: window instance
        """
        self.window = window
        self.is_dialog = False
        self.busy = False

    def rollback(self, current: str = None):
        """
        Rollback to the previous working directory

        :param current: current working directory (optional)
        """
        print(f"Reverting workdir to: {current}...")
        self.window.core.config.set_workdir(current, reload=True)
        default_path = self.window.core.config.get_base_workdir()
        lock_file = os.path.join(default_path, 'path.cfg')
        lock_path = current.replace(str(Path.home()), "%HOME%")
        if current == default_path:
            lock_path = ""
        with open(lock_file, 'w', encoding='utf-8') as f:
            f.write(lock_path)
        self.window.ui.dialogs.workdir.set_path(current)
        self.window.ui.dialogs.workdir.show_status(f"Failed. Reverted to previous workdir: {current}.")
        self.window.controller.reload()
        self.window.core.config.profile.update_current_workdir(current)

    def update_workdir(
            self,
            force: bool = False,
            path: str = None,
            is_create: bool = False,
    ):
        """
        Update working directory

        :param force: boolean indicating if update should be forced (confirm)
        :param path: new working directory to set
        :param is_create: True if called on profile creation
        """
        print("\n====================")
        print(f"Changing workdir to: {path}")
        print("====================\n")
        default_path = self.window.core.config.get_base_workdir()
        if force:
            self.window.ui.dialogs.workdir.show_status(trans("dialog.workdir.result.wait"))

        lock_file = os.path.join(default_path, 'path.cfg')  # put "path.cfg"
        lock_path = path.replace(str(Path.home()), "%HOME%")
        if path == default_path:
            lock_path = ""  # set empty if default dir
        with open(lock_file, 'w', encoding='utf-8') as f:
            f.write(lock_path)

        # update path in current profile
        self.window.core.config.profile.update_current_workdir(path)

        # save previous theme and language to retain them after workdir change
        prev_theme = None
        prev_lang = None
        if is_create:
            prev_theme = self.window.core.config.get('theme')
            prev_lang = self.window.core.config.get('lang')

        # reload config
        self.window.core.config.set_workdir(path, reload=True)

        # if profile is just created, use current theme and language
        if is_create:
            print("Using current theme and language: ", prev_theme, prev_lang)
            if prev_theme is not None:
                self.window.core.config.set('theme', prev_theme)
            if prev_lang is not None:
                self.window.core.config.set('lang', prev_lang)
            self.window.core.config.save()

        self.window.core.config.set('license.accepted', True)  # accept license to prevent show dialog again

    @Slot(bool, str, str, str)
    def do_update(
            self,
            force: bool,
            profile_name: str,
            current_path: str,
            new_path: str,
            is_create: bool = False
    ) -> bool:
        """
        Update working directory

        :param force: boolean indicating if update should be forced (confirm)
        :param profile_name: profile name to update after workdir change
        :param current_path: current working directory before update
        :param new_path: new working directory to set
        :param is_create: if True, skip check for existing workdir in path
        :return: boolean indicating if update was successful
        """
        self.update_workdir(
            force=force,
            path=new_path,
            is_create=is_create,
        )
        rollback = False
        success = False
        if force:
            try:
                self.window.ui.dialogs.workdir.show_status(trans("dialog.workdir.result.wait"))
                self.window.controller.reload()  # reload all
                self.window.ui.dialogs.workdir.show_status(trans("dialog.workdir.result.wait"))
                msg = trans("dialog.workdir.result.success").format(path=new_path)
                self.window.ui.dialogs.workdir.show_status(msg)
                self.window.ui.dialogs.alert(msg)
                success = True
            except Exception as e:
                rollback = True
                self.window.core.debug.log(e)
                self.window.ui.dialogs.alert(str(e))
                print("Error reloading components: ", e)
                self.window.controller.reloading = False  # unlock
        else:
            self.window.controller.reload()  # reload only

        if rollback:  # if failed
            self.rollback(current=current_path)  # revert to previous workdir
        else:
            # update profile after workdir change
            if profile_name:
                self.window.controller.settings.profile.after_update(profile_name)
        return success

    @Slot(bool, str, str, str)
    def do_migrate(
            self,
            result: bool,
            profile_name: str,
            current_path: str,
            new_path: str
    ) -> bool:
        """
        Handle migration result

        :param result: boolean indicating if migration was successful
        :param profile_name: profile name to update after migration
        :param current_path: current working directory before migration
        :param new_path: new working directory after migration
        :return: boolean indicating if migration was successful
        """
        success = False
        if result:
            try:
                # update workdir to new path
                success = self.do_update(
                    force=True,
                    profile_name=profile_name,
                    current_path=current_path,
                    new_path=new_path,
                )  # with rollback if failed

                if not success:
                    raise Exception("Migration failed, workdir not updated.")

                msg = trans("dialog.workdir.result.success").format(path=new_path)
                self.window.ui.dialogs.workdir.show_status(msg)
                self.window.ui.dialogs.alert(msg)

                # remove old workdir only if success
                self.window.core.debug.info(f"Clearing old workdir: {current_path}...")
                try:
                    self.window.core.filesystem.clear_workdir(current_path)  # allow errors here
                    self.window.core.debug.info(f"Old workdir cleared: {current_path}.")
                except Exception as e:
                    self.window.core.debug.log(e)
                    print("Error clearing old workdir: ", e)

            except Exception as e:
                self.window.core.debug.log(e)
                self.window.ui.dialogs.alert(str(e))
                print("Error migrating workdir: ", e)
                self.window.controller.reloading = False
        else:
            # if migration failed
            self.window.ui.dialogs.workdir.show_status(trans("dialog.workdir.result.failed"))
            self.window.ui.dialogs.alert(trans("dialog.workdir.result.failed"))
            self.window.controller.reloading = False

        self.window.controller.settings.workdir.busy = False
        if success:
            self.window.core.debug.info(f"Finished migrating workdir from: {current_path} to: {new_path}.")
        return success

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
        worker = WorkdirWorker(
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
        worker.signals.updateGlobalStatus.connect(self.window.update_status)
        worker.signals.updateStatus.connect(self.window.ui.dialogs.workdir.show_status)
        worker.signals.hideStatus.connect(self.window.ui.dialogs.workdir.hide_status)
        worker.signals.alert.connect(self.window.ui.dialogs.alert)
        worker.signals.error.connect(lambda err: self.window.core.debug.log(f"Worker error: {err}"))
        worker.signals.confirm.connect(self.window.ui.dialogs.confirm)
        worker.signals.restored.connect(lambda current: self.window.ui.dialogs.workdir.set_path(current))
        worker.signals.updated.connect(self.window.controller.settings.profile.after_update)
        worker.signals.deleted.connect(self.window.controller.settings.profile.after_delete)
        worker.signals.duplicated.connect(self.window.controller.settings.profile.after_duplicate)
        worker.signals.switch.connect(self.window.controller.settings.profile.switch_current)
        worker.signals.after_migrate.connect(self.do_migrate)

        # start worker in thread pool
        self.window.threadpool.start(worker)

    def update(
            self,
            path: str,
            force: bool = False,
            profile_name: str = None,
            is_create: bool = False,
    ):
        """
        Switch working directory to the existing one

        :param path: existing working directory
        :param force: force update (confirm)
        :param profile_name: profile name (optional, for future use)
        :param is_create: if True, skip check for existing workdir in path
        """
        self.do_update(
            force=force,
            profile_name=profile_name,
            current_path=self.window.core.config.get_user_path(),
            new_path=path,
            is_create=is_create,
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
        self.rollback(current=current)

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