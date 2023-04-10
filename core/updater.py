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

from urllib.request import urlopen, Request
from packaging.version import parse as parse_version
import json
import ssl
from core.utils import trans


class Updater:
    def __init__(self, window=None):
        """
        Updater

        :param window: main window
        """
        self.window = window

    def check(self):
        """Check for updates"""
        print("Checking for updates...")
        url = self.window.website + "/api/version?v=" + str(self.window.version)
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
            parsed_current_version = parse_version(self.window.version)
            if parsed_newest_version > parsed_current_version:
                self.show_version_dialog(newest_version, newest_build, changelog)
        except Exception as e:
            print("Failed to check for updates")
            print(e)

    def show_version_dialog(self, version, build, changelog):
        """
        Show new version dialog

        :param version: version number
        :param build: build date
        :param changelog: changelog
        """
        txt = trans('update.new_version') + ": " + str(version) + " (" + trans('update.released') + ": " + str(
            build) + ")"
        txt += "\n" + trans('update.current_version') + ": " + self.window.version
        self.window.dialog['update'].changelog.setPlainText(changelog)
        self.window.dialog['update'].message.setText(txt)
        self.window.ui.dialogs.open('update')
