#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.03 00:00:00                  #
# ================================================== #
from typing import Union

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
    _ICON_ZOOM_IN = QIcon(":/icons/zoom_in.svg")
    _ICON_ZOOM_OUT = QIcon(":/icons/zoom_out.svg")

    def __init__(self, window=None):
        """
        Context menu common

        :param window: main window
        """
        self.window = window

    def get_zoom_menu(self, parent, parent_type: str, current_zoom: Union[int, float], callback = None) -> QMenu:
        """
        Get zoom menu (Zoom In/Out)

        :param parent: Parent menu
        :param parent_type: Type of textarea ('chat', 'notepad', etc.)
        :param current_zoom: Current zoom level
        :param callback: Callback function on zoom change
        :return: Menu
        """
        menu = QMenu(trans('context_menu.zoom'), parent)
        if parent_type in ("font_size.input", "font_size", "editor"):
            action_zoom_in = QAction(self._ICON_ZOOM_IN, trans('context_menu.zoom.in'), menu)
            new_zoom = current_zoom + 2
            action_zoom_in.triggered.connect(
                lambda checked=False, new_zoom=new_zoom: callback(new_zoom)
            )
            menu.addAction(action_zoom_in)
            action_zoom_out = QAction(self._ICON_ZOOM_OUT, trans('context_menu.zoom.out'), menu)
            new_zoom = current_zoom - 2
            action_zoom_out.triggered.connect(
                lambda checked=False, new_zoom=new_zoom: callback(new_zoom)
            )
            menu.addAction(action_zoom_out)
        elif parent_type in ("zoom"):
            action_zoom_in = QAction(self._ICON_ZOOM_IN, trans('context_menu.zoom.in'), menu)
            new_zoom = current_zoom + 0.1
            action_zoom_in.triggered.connect(
                lambda checked=False, new_zoom=new_zoom: callback(new_zoom)
            )
            menu.addAction(action_zoom_in)
            action_zoom_out = QAction(self._ICON_ZOOM_OUT, trans('context_menu.zoom.out'), menu)
            new_zoom = current_zoom - 0.1
            action_zoom_out.triggered.connect(
                lambda checked=False, new_zoom=new_zoom: callback(new_zoom)
            )
            menu.addAction(action_zoom_out)

        return menu

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