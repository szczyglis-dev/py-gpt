#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.25 10:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QMenu
from PySide6.QtGui import QAction, QIcon

from pygpt_net.utils import trans
import pygpt_net.icons_rc


class ContextMenu:
    def __init__(self, window=None):
        """
        Context menu common

        :param window: main window
        """
        self.window = window

    def get_copy_to_menu(self, parent, selected_text: str = None, excluded: list = None) -> QMenu:
        """
        Get copy to menu

        :param parent: Parent widget
        :param selected_text: Selected text
        :param excluded: Excluded items
        :return: Menu
        """
        if excluded is None:
            excluded = []
        menu = QMenu(trans('text.context_menu.copy_to'), parent)

        # input
        if 'input' not in excluded:
            action = QAction(QIcon(":/icons/input.svg"), trans('text.context_menu.copy_to.input'), parent)
            action.triggered.connect(
                lambda: self.window.controller.chat.common.append_to_input(selected_text))
            menu.addAction(action)

        # calendar
        if 'calendar' not in excluded:
            action = QAction(QIcon(":/icons/schedule.svg"), trans('text.context_menu.copy_to.calendar'), parent)
            action.triggered.connect(
                lambda: self.window.controller.calendar.note.append_text(selected_text))
            menu.addAction(action)

        # notepad
        if 'notepad' not in excluded:
            num_notepads = self.window.controller.notepad.get_num_notepads()
            if num_notepads > 0:
                for i in range(1, num_notepads + 1):
                    excluded_id = "notepad_id_{}".format(i)
                    if excluded_id in excluded:
                        continue
                    name = self.window.controller.notepad.get_notepad_name(i)
                    action = QAction(QIcon(":/icons/paste.svg"), name, parent)
                    action.triggered.connect(lambda checked=False, i=i:
                                             self.window.controller.notepad.append_text(selected_text, i))
                    menu.addAction(action)

        # python interpreter
        if 'interpreter' not in excluded:
            menu.addSeparator()
            if 'interpreter_edit' not in excluded:
                action = QAction(QIcon(":/icons/code.svg"), trans('text.context_menu.copy_to.python.code'), parent)
                action.triggered.connect(
                    lambda: self.window.tools.get("interpreter").append_to_edit(selected_text))
                menu.addAction(action)

            if 'interpreter_input' not in excluded:
                action = QAction(QIcon(":/icons/code.svg"), trans('text.context_menu.copy_to.python.input'), parent)
                action.triggered.connect(
                    lambda: self.window.tools.get("interpreter").append_to_input(selected_text))
                menu.addAction(action)

        return menu
