#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.04 00:00:00                  #
# ================================================== #
"""Editor actions and menus."""
from PySide6.QtGui import QAction, QIcon, QKeySequence
from pygpt_net.utils import trans

class EditorMenus:
    def __init__(self, editor):
        self.editor = editor

    def context(self, event):
        """
        Context menu event

        :param event: Event
        """
        menu = self.editor.createStandardContextMenu()
        cursor = self.editor.textCursor()
        selected_text = cursor.selectedText()
        has_selection = bool(selected_text)

        # Mark / Unmark actions for selection
        if has_selection:
            start = min(cursor.selectionStart(), cursor.selectionEnd())
            end = max(cursor.selectionStart(), cursor.selectionEnd())
            overlap = self.editor.markers.overlaps(start, end)

            action_mark = QAction(QIcon(":/icons/edit.svg"), trans("action.mark"), self.editor)
            action_mark.triggered.connect(self.editor.markers.mark)
            menu.addAction(action_mark)

            action_unmark = QAction(QIcon(":/icons/close.svg"), trans("action.unmark"), self.editor)
            action_unmark.setEnabled(overlap)
            action_unmark.triggered.connect(self.editor.markers.unmark)
            menu.addAction(action_unmark)

        if selected_text:
            plain_text = cursor.selection().toPlainText()

            action = QAction(QIcon(":/icons/volume.svg"), trans('text.context_menu.audio.read'), self.editor)
            action.triggered.connect(self.editor.audio_read_selection)
            menu.addAction(action)

            excluded_id = f"notepad_id_{self.editor.id}"
            copy_to_menu = self.editor.window.ui.context_menu.get_copy_to_menu(menu, selected_text, excluded=[excluded_id])
            menu.addMenu(copy_to_menu)

            action = QAction(QIcon(":/icons/save.svg"), trans('action.save_selection_as'), self.editor)
            action.triggered.connect(
                lambda: self.editor.window.controller.chat.common.save_text(plain_text))
            menu.addAction(action)
        else:
            action = QAction(QIcon(":/icons/save.svg"), trans('action.save_as'), self.editor)
            action.triggered.connect(
                lambda: self.editor.window.controller.chat.common.save_text(self.editor.toPlainText()))
            menu.addAction(action)

        # Add insert date/time submenu
        datetime_menu = self.editor.window.ui.context_menu.get_insert_datetime_menu(menu, self.editor)
        menu.addMenu(datetime_menu)

        # Add zoom submenu
        zoom_menu = self.editor.window.ui.context_menu.get_zoom_menu(self.editor, "font_size", self.editor.value, self.editor.on_zoom_changed)
        menu.addMenu(zoom_menu)

        action = QAction(QIcon(":/icons/search.svg"), trans('text.context_menu.find'), self.editor)
        action.triggered.connect(self.editor.find_open)
        action.setShortcut(QKeySequence("Ctrl+F"))
        menu.addAction(action)

        menu.exec(event.globalPos())

