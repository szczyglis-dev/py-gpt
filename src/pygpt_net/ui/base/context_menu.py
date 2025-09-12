#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.24 23:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QMenu
from PySide6.QtGui import QAction, QIcon

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.utils import trans


class ContextMenu:

    _ICON_INPUT = QIcon(":/icons/input.svg")
    _ICON_SCHEDULE = QIcon(":/icons/schedule.svg")
    _ICON_PASTE = QIcon(":/icons/paste.svg")
    _ICON_CODE = QIcon(":/icons/code.svg")
    _ICON_TEXT = QIcon(":/icons/text.svg")
    _ICON_TRANSLATOR = QIcon(":/icons/translate.svg")

    def __init__(self, window=None):
        """
        Context menu common

        :param window: main window
        """
        self.window = window

    def get_copy_to_menu(
            self,
            parent,
            selected_text: str = None,
            excluded: list = None
    ) -> QMenu:
        """
        Get copy to menu

        :param parent: Parent menu
        :param selected_text: Selected text
        :param excluded: Excluded items
        :return: Menu
        """
        excluded = set(excluded) if excluded else set()
        menu = QMenu(trans('text.context_menu.copy_to'), parent)
        window = self.window
        ctrl = window.controller
        tools = window.tools

        if 'input' not in excluded:
            action = QAction(self._ICON_INPUT, trans('text.context_menu.copy_to.input'), menu)
            action.triggered.connect(lambda checked=False: ctrl.chat.common.append_to_input(selected_text))
            menu.addAction(action)

        if 'calendar' not in excluded:
            action = QAction(self._ICON_SCHEDULE, trans('text.context_menu.copy_to.calendar'), menu)
            action.triggered.connect(lambda checked=False: ctrl.calendar.note.append_text(selected_text))
            menu.addAction(action)

        if 'notepad' not in excluded:
            tabs = window.core.tabs.get_tabs_by_type(Tab.TAB_NOTEPAD)
            if tabs:
                for tab in tabs:
                    action = QAction(self._ICON_PASTE, tab.title, menu)
                    action.triggered.connect(
                        lambda checked=False, tab=tab: ctrl.notepad.append_text(selected_text, tab.data_id)
                    )
                    menu.addAction(action)

        if 'interpreter' not in excluded:
            add_edit = 'interpreter_edit' not in excluded
            add_input = 'interpreter_input' not in excluded
            if add_edit or add_input:
                menu.addSeparator()
                interpreter = tools.get("interpreter")
                if add_edit:
                    action = QAction(self._ICON_CODE, trans('text.context_menu.copy_to.python.code'), menu)
                    action.triggered.connect(lambda checked=False: interpreter.append_to_edit(selected_text))
                    menu.addAction(action)
                if add_input:
                    action = QAction(self._ICON_CODE, trans('text.context_menu.copy_to.python.input'), menu)
                    action.triggered.connect(lambda checked=False: interpreter.append_to_input(selected_text))
                    menu.addAction(action)

        if 'translator' not in excluded:
            add_left = 'translator_left' not in excluded
            add_right = 'translator_right' not in excluded
            if add_left or add_right:
                menu.addSeparator()
                translator = tools.get("translator")
                if add_left:
                    action = QAction(self._ICON_TRANSLATOR, trans('text.context_menu.copy_to.translator_left'), menu)
                    action.triggered.connect(lambda checked=False: translator.append_content("left", selected_text))
                    menu.addAction(action)
                if add_right:
                    action = QAction(self._ICON_TRANSLATOR, trans('text.context_menu.copy_to.translator_right'), menu)
                    action.triggered.connect(lambda checked=False: translator.append_content("right", selected_text))
                    menu.addAction(action)

        return menu