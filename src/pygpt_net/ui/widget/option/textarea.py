#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.26 23:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QTextEdit


class OptionTextarea(QTextEdit):
    def __init__(
            self,
            window=None,
            parent_id: str = None,
            id: str = None,
            option: dict = None
    ):
        """
        Settings textarea

        :param window: main window
        :param id: option id
        :param parent_id: parent option id
        :param option: option data
        """
        super(OptionTextarea, self).__init__(window)
        self.window = window
        self.id = id
        self.parent_id = parent_id
        self.option = option
        self.value = False
        self.title = ""
        self.real_time = False
        self.update_ui = True
        self.setAcceptRichText(False)
        self.context_options = []

        # init from option data
        if self.option is not None:
            if "label" in self.option:
                self.title = self.option["label"]
            if "value" in self.option:
                self.value = self.option["value"]
            if "real_time" in self.option:
                self.real_time = self.option["real_time"]
            if "context_options" in self.option:
                self.context_options = self.option["context_options"]
            if "read_only" in self.option and self.option["read_only"]:
                self.setReadOnly(True)

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: Event
        """
        menu = self.createStandardContextMenu()
        if "prompt.template.paste" in self.context_options:
            self.window.core.prompt.template.to_menu_options(menu, "editor")
        menu.exec_(event.globalPos())

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key event
        """
        super(OptionTextarea, self).keyPressEvent(event)
        if not self.real_time:
            return

        # hook update
        self.window.controller.config.input.on_update(
            self.parent_id,
            self.id,
            self.option,
            self.toPlainText()
        )
        if self.update_ui:
            self.window.controller.ui.update()
