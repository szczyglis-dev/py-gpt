#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.17 22:00:00                  #
# ================================================== #

from .dialog.about import About
from .dialog.assistant import Assistant
from .dialog.changelog import Changelog
from .dialog.debug import Debug
from .dialog.editor import Editor
from .dialog.image import Image
from .dialog.logger import Logger
from .dialog.plugins import Plugins
from .dialog.preset import Preset
from .dialog.rename import Rename
from .dialog.settings import Settings
from .dialog.start import Start
from .dialog.update import Update
from .widget.dialog import AlertDialog, ConfirmDialog


class Dialogs:
    def __init__(self, window=None):
        """
        Dialogs setup

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup dialogs"""
        # setup debug dialogs
        debug = Debug(self.window)
        for id in self.window.app.debug.ids:
            debug.setup(id)

        # setup info dialogs
        about = About(self.window)
        changelog = Changelog(self.window)
        about.setup()
        changelog.setup()

        # setup settings dialog
        settings = Settings(self.window)
        settings.setup()

        # setup preset editor dialog
        preset = Preset(self.window)
        preset.setup()

        # setup assistant editor dialog
        assistant = Assistant(self.window)
        assistant.setup()

        # setup editor dialog
        editor = Editor(self.window)
        editor.setup()

        # setup rename dialog
        rename = Rename(self.window)
        rename.setup()

        # setup start dialog
        start = Start(self.window)
        start.setup()

        # setup update dialog
        update = Update(self.window)
        update.setup()

        # setup image dialog
        image = Image(self.window)
        image.setup()

        # setup logger dialog
        logger = Logger(self.window)
        logger.setup()

        self.window.plugin_settings = Plugins(self.window)
        self.window.ui.dialog['alert'] = AlertDialog(self.window)
        self.window.ui.dialog['confirm'] = ConfirmDialog(self.window)

    def confirm(self, type, id, msg, parent_object=None):
        """
        Show confirm dialog

        :param type: confirm type
        :param id: confirm object id
        :param msg: message to show
        :param parent_object: parent object
        """
        self.window.ui.dialog['confirm'].type = type
        self.window.ui.dialog['confirm'].id = id
        self.window.ui.dialog['confirm'].message.setText(msg)
        self.window.ui.dialog['confirm'].parent_object = parent_object
        self.window.ui.dialog['confirm'].show()

    def alert(self, msg):
        """
        Show alert dialog

        :param msg: message to show
        """
        self.window.ui.dialog['alert'].message.setPlainText(msg)
        self.window.ui.dialog['alert'].show()

    def open_editor(self, id, data_id, width=400, height=400):
        """
        Open editor dialog

        :param id: debug dialog id
        :param data_id: data id
        :param width: dialog width
        :param height: dialog height
        """
        if id not in self.window.ui.dialog:
            return
        self.window.ui.dialog[id].resize(width, height)
        self.window.ui.dialog[id].data_id = data_id
        self.window.ui.dialog[id].show()

    def open(self, id, width=400, height=400):
        """
        Open debug/config dialog

        :param id: debug dialog id
        :param width: dialog width
        :param height: dialog height
        """
        if id not in self.window.ui.dialog:
            return
        self.window.ui.dialog[id].resize(width, height)
        qr = self.window.ui.dialog[id].frameGeometry()
        cp = self.window.screen().availableGeometry().center()
        qr.moveCenter(cp)
        self.window.ui.dialog[id].move(qr.topLeft())
        self.window.ui.dialog[id].show()

    def close(self, id):
        """
        Close debug/config dialog

        :param id: debug dialog id
        """
        if id not in self.window.ui.dialog:
            return
        self.window.ui.dialog[id].close()
