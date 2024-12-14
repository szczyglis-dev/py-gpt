#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 22:00:00                  #
# ================================================== #

from pathlib import Path


class Installer:

    def __init__(self, window=None):
        """
        Installer core

        :param window: Window instance
        """
        self.window = window

    def install(self):
        """Install db, config data and directories"""
        try:
            # create user config directory
            path = Path(self.window.core.config.path)
            path.mkdir(parents=True, exist_ok=True)

            # install config files and database
            self.window.core.config.install()

            # install models
            self.window.core.models.install()

            # install presets
            self.window.core.presets.install()

            # install indexes
            self.window.core.idx.install()

            # install history
            self.window.core.history.install()

            # install context
            self.window.core.ctx.install()

            # install notepad
            self.window.core.notepad.install()

            # install attachments
            self.window.core.attachments.install()

            # install assistants
            self.window.core.assistants.install()

            # install images
            self.window.core.image.install()

            # install filesystem
            self.window.core.filesystem.install()

            # install vision capture
            self.window.core.camera.install()

        except Exception as e:
            self.window.core.debug.log(e)
            print("Error installing config files:", e)
