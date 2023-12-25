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

from pathlib import Path


class Installer:

    def __init__(self, window=None):
        """
        Installer

        :param window: Window instance
        """
        self.window = window

    def install(self):
        """
        Install all config data and directories
        """
        try:
            # create user config directory
            path = Path(self.window.app.config.path)
            path.mkdir(parents=True, exist_ok=True)

            # install config
            self.window.app.config.install()

            # install models
            self.window.app.models.install()

            # install presets
            self.window.app.presets.install()

            # install history
            self.window.app.history.install()

            # install context
            self.window.app.ctx.install()

            # install notepad
            self.window.app.notepad.install()

            # install attachments
            self.window.app.attachments.install()

            # install assistants
            self.window.app.assistants.install()

            # install images
            self.window.app.image.install()

            # install filesystem
            self.window.app.filesystem.install()

            # install vision capture
            self.window.app.camera.install()

        except Exception as e:
            self.window.app.debug.log(e)
            print("Error installing config files:", e)
