#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.08 22:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QTextEdit


class PromptTextarea(QTextEdit):
    def __init__(
            self,
            window=None,
            parent_id: str = None,
            id: str = None,
            option: dict = None
    ):
        """
        Global prompt textarea

        :param window: main window
        :param id: option id
        :param parent_id: parent option id
        :param option: option data
        """
        super(PromptTextarea, self).__init__(window)
        self.window = window
        self.id = id
        self.parent_id = parent_id
        self.option = option
        self.value = False
        self.title = ""
        self.update_ui = True
        self.setAcceptRichText(False)
        self.textChanged.connect(
            lambda: self.on_prompt_changed())

        # init from option data
        if self.option is not None:
            if "label" in self.option:
                self.title = self.option["label"]
            if "value" in self.option:
                self.value = self.option["value"]
            if "real_time" in self.option:
                self.real_time = self.option["real_time"]

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key event
        """
        super(PromptTextarea, self).keyPressEvent(event)

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: Event
        """
        menu = self.createStandardContextMenu()
        try:
            self.window.core.prompt.template.to_menu_options(menu, "global")
            self.window.core.prompt.custom.to_menu_options(menu, "global")
        except Exception as e:
            self.window.core.debug.log(e)
        menu.exec_(event.globalPos())

    def on_prompt_changed(self):
        """On prompt changed"""
        # hook update
        if self.window.controller.mode.locked:
            return

        self.window.controller.config.input.on_update(
            self.window.ui.nodes['preset.prompt'].parent_id,
            self.window.ui.nodes['preset.prompt'].id,
            self.window.ui.nodes['preset.prompt'].option,
            self.window.ui.nodes['preset.prompt'].toPlainText(),
        )
        self.window.controller.ui.update_tokens()
