#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.14 18:00:00                  #
# ================================================== #

import os
from pathlib import Path

from PySide6.QtWidgets import QApplication

from pygpt_net.utils import trans


class Workdir:
    def __init__(self, window=None):
        """
        Workdir migration controller

        :param window: Window instance
        """
        self.window = window
        self.is_dialog = False
        self.busy = False

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

    def update(self, path: str, force: bool = False):
        """
        Switch working directory to the existing one

        :param path: existing working directory
        :param force: force update (confirm)
        """
        print("\n====================")
        print("Changing workdir to: ", path)
        print("====================\n")
        current_path = self.window.core.config.get_user_path()
        default_path = self.window.core.config.get_base_workdir()
        if force:
            self.window.ui.dialogs.workdir.show_status(trans("dialog.workdir.result.wait"))
            QApplication.processEvents()

        lock_file = os.path.join(default_path, 'path.cfg')  # put "path.cfg"
        lock_path = path.replace(str(Path.home()), "%HOME%")
        if path == default_path:
            lock_path = ""  # set empty if default dir
        with open(lock_file, 'w', encoding='utf-8') as f:
            f.write(lock_path)  # new path

        # update path in current profile
        self.window.core.config.profile.update_current_workdir(path)

        # reload config
        self.window.core.config.set_workdir(path, reload=True)
        self.window.core.config.set('license.accepted', True)  # accept license to prevent show dialog again

        # reload components
        if force:
            try:
                self.window.controller.reload()
                self.window.ui.dialogs.workdir.show_status(trans("dialog.workdir.result.success").format(path=path))
                self.window.ui.dialogs.alert(trans("dialog.workdir.result.success").format(path=path))
            except Exception as e:
                self.window.core.debug.log(e)
                self.window.ui.dialogs.alert(e)
                print("Error reloading components: ", e)
                self.restore(current_path)
                self.window.controller.reloading = False  # unlock
        else:
            self.window.controller.reload()

    def migrate(self, path: str, force: bool = False):
        """
        Migrate working directory

        :param path: new working directory
        :param force: force migration (confirm)
        """
        if self.busy:
            self.window.ui.dialogs.alert("Workdir migration in progress...")
            return

        # check if not the same directory
        current = self.window.core.config.get_user_path()
        if current == path:
            self.window.ui.dialogs.alert(trans("dialog.workdir.result.same_directory"))
            self.busy = False
            self.window.ui.dialogs.workdir.hide_status()
            return

        # check if path is not already a workdir
        if self.window.core.filesystem.is_workdir_in_path(path):
            self.window.ui.dialogs.confirm(
                type='workdir.update',
                id=path,
                msg=trans("dialog.workdir.update.confirm").format(path=path)
            )
            return

        # check if path is empty
        if not self.window.core.filesystem.is_directory_empty(path):
            self.window.ui.dialogs.alert(trans("dialog.workdir.change.empty.alert"))
            return

        # confirm move
        if not force:
            self.window.ui.dialogs.confirm(
                type='workdir.change',
                id=path,
                msg=trans("dialog.workdir.change.confirm").format(path=path)
            )
            return

        self.window.ui.dialogs.workdir.hide_status()
        self.busy = True
        print("Migrating workdir from: ", current, " to: ", path)

        # check if path exists
        if not os.path.exists(path) or not os.path.isdir(path):
            self.window.ui.dialogs.alert(trans("dialog.workdir.result.directory_not_exists"))
            self.window.ui.dialogs.workdir.hide_status()
            self.busy = False
            return

        # check free space
        space_required = self.window.core.filesystem.get_directory_size(current, human_readable=False)
        space_free = self.window.core.filesystem.get_free_disk_space(path, human_readable=False)
        if space_required > space_free:
            self.window.ui.dialogs.alert(trans("dialog.workdir.result.no_free_space").format(
                required=self.window.core.filesystem.get_directory_size(current),
                free=self.window.core.filesystem.get_free_disk_space(path),
            ))
            self.busy = False
            self.window.ui.dialogs.workdir.hide_status()
            return

        self.window.ui.dialogs.workdir.show_status(trans("dialog.workdir.result.wait"))
        QApplication.processEvents()

        # copy workdir
        try:
            result = self.window.core.filesystem.copy_workdir(current, path)
        except Exception as e:
            self.window.core.debug.log(e)
            self.window.ui.dialogs.alert(e)
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
                self.update(path)  # update workdir to new path
                self.window.ui.dialogs.workdir.show_status(trans("dialog.workdir.result.success").format(path=path))
                self.window.ui.dialogs.alert(trans("dialog.workdir.result.success").format(path=path))
            except Exception as e:
                self.window.core.debug.log(e)
                self.window.ui.dialogs.alert(e)
                print("Error migrating workdir: ", e)
                self.restore(current)  # restore current if failed
                self.window.controller.reloading = False  # unlock
        else:
            self.window.ui.dialogs.workdir.show_status(trans("dialog.workdir.result.failed"))
            self.window.ui.dialogs.alert(trans("dialog.workdir.result.failed"))
            self.restore(current)  # restore current if failed
            self.window.controller.reloading = False  # unlock

        self.busy = False
        self.window.core.debug.info("Finished migrating workdir from: {} to: {}".format(current, path))

    def restore(self, current: str):
        """
        Restore default working directory

        :param current: current working directory
        """
        print("Reverting workdir to: ", current)
        self.window.core.config.set_workdir(current, reload=True)
        default_path = self.window.core.config.get_base_workdir()
        lock_file = os.path.join(default_path, 'path.cfg')
        lock_path = current.replace(str(Path.home()), "%HOME%")
        if current == default_path:
            lock_path = ""  # set empty if default dir
        with open(lock_file, 'w', encoding='utf-8') as f:
            f.write(lock_path)  # new path
        self.window.ui.dialogs.workdir.set_path(current)
        self.window.ui.dialogs.workdir.show_status("Failed. Reverted to current workdir: {}".format(current))
        self.window.controller.reload()
        self.window.core.config.profile.update_current_workdir(current)  # update profile
