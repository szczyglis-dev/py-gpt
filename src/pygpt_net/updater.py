#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.25 21:00:00                  #
# ================================================== #

import copy
import os
import shutil
import json
import ssl

from urllib.request import urlopen, Request
from packaging.version import parse as parse_version

from pygpt_net.utils import trans


class Updater:
    def __init__(self, window=None):
        """
        Updater (config data patcher)

        :param window: Window instance
        """
        self.window = window

    def patch(self):
        """Patch config data to current version"""
        try:
            version = self.get_app_version()

            self.patch_config(version)
            self.patch_models(version)
            self.patch_presets(version)
            self.patch_ctx(version)
            self.patch_assistants(version)
            self.patch_attachments(version)
            self.patch_notepad(version)
        except Exception as e:
            self.window.app.debug.log(e)
            print("Failed to patch config data!")

    def patch_config(self, version):
        """
        Migrate config to current app version

        :param version: current app version
        """
        if self.window.app.config.patch(version):
            print("Migrated config. [OK]")

    def patch_models(self, version):
        """
        Migrate models to current app version

        :param version: current app version
        """
        if self.window.app.models.patch(version):
            print("Migrated models. [OK]")

    def patch_presets(self, version):
        """
        Migrate presets to current app version

        :param version: current app version
        """
        if self.window.app.presets.patch(version):
            print("Migrated presets. [OK]")

    def patch_ctx(self, version):
        """
        Migrate ctx to current app version

        :param version: current app version
        """
        if self.window.app.ctx.patch(version):
            print("Migrated ctx. [OK]")

    def patch_assistants(self, version):
        """
        Migrate assistants to current app version

        :param version: current app version
        """
        if self.window.app.assistants.patch(version):
            print("Migrated assistants. [OK]")

    def patch_attachments(self, version):
        """
        Migrate attachments to current app version

        :param version: current app version
        """
        if self.window.app.attachments.patch(version):
            print("Migrated attachments. [OK]")

    def patch_notepad(self, version):
        """
        Migrate notepad to current app version

        :param version: current app version
        """
        if self.window.app.notepad.patch(version):
            print("Migrated notepad. [OK]")

    def patch_dir(self, dirname="", force=False):
        """
        Patch directory (replace all files)

        :param dirname: directory name
        :param force: force update
        """
        try:
            # directory
            dst_dir = os.path.join(self.window.app.config.path, dirname)
            src = os.path.join(self.window.app.config.get_root_path(), 'data', 'config', dirname)
            for file in os.listdir(src):
                src_file = os.path.join(src, file)
                dst_file = os.path.join(dst_dir, file)
                if not os.path.exists(dst_file) or force:
                    shutil.copyfile(src_file, dst_file)
                    print("Patched file: {}.".format(dst_file))
        except Exception as e:
            self.window.app.debug.log(e)

    def patch_file(self, filename="", force=False):
        """
        Patch file

        :param filename: file name
        :param force: force update
        """
        try:
            # file
            dst = os.path.join(self.window.app.config.path, filename)
            if not os.path.exists(dst) or force:
                src = os.path.join(self.window.app.config.get_root_path(), 'data', 'config', filename)
                shutil.copyfile(src, dst)
                print("Patched file: {}.".format(dst))
        except Exception as e:
            self.window.app.debug.log(e)

    def get_app_version(self):
        """
        Get the current app version.

        :return: version
        :rtype: str
        """
        return parse_version(self.window.meta['version'])

    def check(self, force=False):
        """
        Check for updates

        :param force: force show version dialog
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
            self.window.app.debug.log(e)
            print("Failed to check for updates")
        return False

    def show_version_dialog(self, version, build, changelog, is_new=False):
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

    def post_check_config(self):
        """
        Check for missing config keys and add them.

        :return: true if updated
        :rtype: bool
        """
        base = self.window.app.config.get_base()
        data = self.window.app.config.all()
        updated = False

        # check for any missing keys
        for key in base:
            if key not in data:
                data[key] = copy.deepcopy(base[key])  # copy base value
                updated = True

        # update file
        if updated:
            data = dict(sorted(data.items()))
            self.window.app.config.data = data
            self.window.app.config.save()

        return updated
