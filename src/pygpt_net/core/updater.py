#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.31 04:00:00                  #
# ================================================== #

import copy
import os
import shutil
import json
import ssl

from urllib.request import urlopen, Request
from packaging.version import parse as parse_version, Version

from pygpt_net.utils import trans


class Updater:
    def __init__(self, window=None):
        """
        Updater core (config data patcher)

        :param window: Window instance
        """
        self.window = window

    def patch(self):
        """Patch config data to current version"""
        try:
            version = self.get_app_version()

            # migrate DB
            self.migrate_db()

            self.patch_config(version)
            self.patch_models(version)
            self.patch_presets(version)
            self.patch_ctx(version)
            self.patch_indexes(version)
            self.patch_assistants(version)
            self.patch_attachments(version)
            self.patch_notepad(version)
        except Exception as e:
            self.window.core.debug.log(e)
            print("Failed to patch config data!")

    def migrate_db(self):
        """Migrate database"""
        try:
            self.window.core.db.migrate()
        except Exception as e:
            self.window.core.debug.log(e)
            print("Failed to migrate database!")

    def patch_config(self, version: Version):
        """
        Migrate config to current app version

        :param version: current app version
        """
        if self.window.core.config.patch(version):
            print("Migrated config. [OK]")

    def patch_models(self, version: Version):
        """
        Migrate models to current app version

        :param version: current app version
        """
        if self.window.core.models.patch(version):
            print("Migrated models. [OK]")

    def patch_presets(self, version: Version):
        """
        Migrate presets to current app version

        :param version: current app version
        """
        if self.window.core.presets.patch(version):
            print("Migrated presets. [OK]")

    def patch_ctx(self, version: Version):
        """
        Migrate ctx to current app version

        :param version: current app version
        """
        if self.window.core.ctx.patch(version):
            print("Migrated ctx. [OK]")

    def patch_assistants(self, version: Version):
        """
        Migrate assistants to current app version

        :param version: current app version
        """
        if self.window.core.assistants.patch(version):
            print("Migrated assistants. [OK]")

    def patch_attachments(self, version: Version):
        """
        Migrate attachments to current app version

        :param version: current app version
        """
        if self.window.core.attachments.patch(version):
            print("Migrated attachments. [OK]")

    def patch_indexes(self, version: Version):
        """
        Migrate indexes to current app version

        :param version: current app version
        """
        if self.window.core.idx.patch(version):
            print("Migrated indexes. [OK]")

    def patch_notepad(self, version: Version):
        """
        Migrate notepad to current app version

        :param version: current app version
        """
        if self.window.core.notepad.patch(version):
            print("Migrated notepad. [OK]")

    def patch_dir(self, dir_name: str = "", force: bool = False):
        """
        Patch directory (replace all files)

        :param dir_name: directory name
        :param force: force update
        """
        try:
            # directory
            dst_dir = os.path.join(self.window.core.config.path, dir_name)
            src = os.path.join(self.window.core.config.get_app_path(), 'data', 'config', dir_name)
            for file in os.listdir(src):
                src_file = os.path.join(src, file)
                dst_file = os.path.join(dst_dir, file)
                if not os.path.exists(dst_file) or force:
                    shutil.copyfile(src_file, dst_file)
                    print("Patched file: {}.".format(dst_file))
        except Exception as e:
            self.window.core.debug.log(e)

    def patch_file(self, filename: str = "", force: bool = False):
        """
        Patch file

        :param filename: file name
        :param force: force update
        """
        try:
            # file
            dst = os.path.join(self.window.core.config.path, filename)
            if not os.path.exists(dst) or force:
                src = os.path.join(self.window.core.config.get_app_path(), 'data', 'config', filename)
                # make backup of old file
                if os.path.exists(dst):
                    shutil.copyfile(dst, dst + '.bak')
                    print("Backup file: {}.".format(dst + '.bak'))
                shutil.copyfile(src, dst)
                print("Patched file: {}.".format(dst))
        except Exception as e:
            self.window.core.debug.log(e)

    def patch_css(self, filename: str = "", force: bool = False):
        """
        Patch css file

        :param filename: file name
        :param force: force update
        """
        try:
            # file
            dst = os.path.join(self.window.core.config.path, 'css', filename)
            if not os.path.exists(dst) or force:
                src = os.path.join(self.window.core.config.get_app_path(), 'data', 'css', filename)
                # make backup of old file
                if os.path.exists(dst):
                    shutil.copyfile(dst, dst + '.bak')
                    print("Backup css file: {}.".format(dst + '.bak'))
                shutil.copyfile(src, dst)
                print("Patched css file: {}.".format(dst))
        except Exception as e:
            self.window.core.debug.log(e)

    def get_app_version(self) -> Version:
        """
        Get the current app version.

        :return: version (packaging.version.Version)
        """
        return parse_version(self.window.meta['version'])

    def check(self, force: bool = False) -> bool:
        """
        Check for updates

        :param force: force show version dialog
        :return: True if update is available
        """
        print("Checking for updates...")
        url = self.window.meta['website'] + "/api/version?v=" + str(self.window.meta['version'])
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            req = Request(
                url=url,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            response = urlopen(req, context=ctx, timeout=3)
            data_json = json.loads(response.read())
            newest_version = data_json["version"]
            newest_build = data_json["build"]

            # changelog
            changelog = ""
            if "changelog" in data_json:
                changelog = data_json["changelog"]

            parsed_newest_version = parse_version(newest_version)
            parsed_current_version = parse_version(self.window.meta['version'])
            if parsed_newest_version > parsed_current_version or force:
                is_new = parsed_newest_version > parsed_current_version
                self.show_version_dialog(newest_version, newest_build, changelog, is_new)
                return True
            else:
                print("No updates available.")
            return False
        except Exception as e:
            self.window.core.debug.log(e)
            print("Failed to check for updates")
        return False

    def show_version_dialog(self, version: str, build: str, changelog: str, is_new: bool = False):
        """
        Display version dialog

        :param version: version number
        :param build: build date
        :param changelog: changelog
        :param is_new: is new version available
        """
        info = trans("update.info")
        if not is_new:
            info = trans('update.info.none')
        txt = trans('update.new_version') + ": " + str(version) + " (" + trans('update.released') + ": " + str(
            build) + ")"
        txt += "\n" + trans('update.current_version') + ": " + self.window.meta['version']
        self.window.ui.dialog['update'].info.setText(info)
        self.window.ui.dialog['update'].changelog.setPlainText(changelog)
        self.window.ui.dialog['update'].message.setText(txt)
        self.window.ui.dialogs.open('update')

    def post_check_config(self) -> bool:
        """
        Check for missing config keys and add them.

        :return: True if updated
        """
        base = self.window.core.config.get_base()
        data = self.window.core.config.all()
        updated = False

        # check for any missing keys
        for key in base:
            if key not in data:
                data[key] = copy.deepcopy(base[key])  # copy base value
                updated = True

        # update file
        if updated:
            data = dict(sorted(data.items()))
            self.window.core.config.data = data
            self.window.core.config.save()

        return updated
