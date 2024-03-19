#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.19 01:00:00                  #
# ================================================== #

import hashlib
import os

from pygpt_net.utils import trans


class Editor:
    def __init__(self, window=None):
        """
        File editor controller

        :param window: Window instance
        """
        self.window = window
        self.width = 800
        self.height = 500

    def setup(self):
        """Set up editor"""
        pass

    def update(self):
        """Update"""
        pass

    def toggle(self, file: str = None):
        """
        Toggle file editor

        :param file: File to load
        """
        id = 'file_editor_' + hashlib.md5(file.encode('utf-8')).hexdigest()  # unique id
        self.window.ui.dialogs.open_instance(
            id,
            width=self.width,
            height=self.height,
        )
        self.window.ui.dialog[id].file = file
        self.window.core.filesystem.editor.load(id, file)  # load file to editor
        self.window.ui.dialog[id].setWindowTitle(os.path.basename(file))  # set window title

        # update menu
        self.update()
