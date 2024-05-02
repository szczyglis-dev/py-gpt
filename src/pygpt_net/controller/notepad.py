#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.05.02 19:00:00                  #
# ================================================== #

from PySide6.QtGui import QIcon, QTextCursor

from pygpt_net.item.notepad import NotepadItem
from pygpt_net.ui.widget.textarea.notepad import NotepadWidget
from pygpt_net.utils import trans
import pygpt_net.icons_rc


class Notepad:
    def __init__(self, window=None):
        """
        Notepad controller

        :param window: Window instance
        """
        self.window = window
        self.default_num_notepads = 1
        self.start_tab_idx = 4  # tab idx from notepad starts
        self.opened_once = False

    def setup_tabs(self):
        """Setup notepad tabs"""
        # create notepads
        num_notepads = self.get_num_notepads()
        if num_notepads > 0:
            for i in range(1, num_notepads + 1):
                self.window.ui.notepad[i] = NotepadWidget(self.window)
                self.window.ui.notepad[i].id = i
                self.window.ui.notepad[i].textarea.id = i

        # append notepads
        if num_notepads > 0:
            for i in range(1, num_notepads + 1):
                tab = i + (self.start_tab_idx - 1)
                title = trans('output.tab.notepad')
                if num_notepads > 1:
                    title += " " + str(i)
                self.window.ui.tabs['output'].addTab(self.window.ui.notepad[i], title)
                self.window.ui.tabs['output'].setTabIcon(tab, QIcon(":/icons/paste.svg"))

    def update_tabs(self):
        """Update notepad tabs"""
        # backup selected tab
        selected_tab = self.window.ui.tabs['output'].currentIndex()
        # remove current tabs and recreate
        for i in range(1, len(self.window.ui.notepad) + 1):
            self.window.ui.notepad[i].on_destroy()
            self.window.ui.notepad[i].close()
            self.window.ui.notepad[i].deleteLater()
        self.window.ui.notepad = {}

        # remove only notepad tabs
        for i in range(self.start_tab_idx, self.window.ui.tabs['output'].count()):
            self.window.ui.tabs['output'].removeTab(self.start_tab_idx)

        self.setup_tabs()
        self.load()

        # restore selected tab if notepad tab was selected
        if selected_tab >= self.start_tab_idx:
            # if selected tab is out of range, select last tab
            if selected_tab >= self.window.ui.tabs['output'].count():
                selected_tab = self.window.ui.tabs['output'].count() - 1
            self.window.ui.tabs['output'].setCurrentIndex(selected_tab)

    def load(self):
        """Load all notepads contents"""
        self.window.core.notepad.load_all()
        items = self.window.core.notepad.get_all()
        num_notepads = self.get_num_notepads()
        if len(items) == 0:
            if num_notepads > 0:
                for idx in range(1, num_notepads + 1):
                    item = NotepadItem()
                    item.idx = idx
                    items[idx] = item

        if num_notepads > 0:
            for idx in range(1, num_notepads + 1):
                if idx not in items:
                    item = NotepadItem()
                    item.idx = idx
                    items[idx] = item
                if idx in self.window.ui.notepad:
                    title = items[idx].title
                    self.window.ui.notepad[idx].setText(items[idx].content)
                    if items[idx].initialized and title is not None and len(title) > 0:
                        self.update_name(idx, items[idx].title, False)

    def reload_tab_names(self):
        """Reload tab names (after lang change)"""
        num_notepads = self.get_num_notepads()
        items = self.window.core.notepad.get_all()
        if num_notepads > 0:
            for i in range(1, num_notepads + 1):
                if i not in items or not items[i].initialized:
                    tab = i + (self.start_tab_idx - 1)
                    if num_notepads > 1:
                        self.window.ui.tabs['output'].setTabText(
                            tab,
                            trans('output.tab.notepad') + " " + str(i),
                        )
                    else:
                        self.window.ui.tabs['output'].setTabText(
                            tab,
                            trans('output.tab.notepad'),
                        )
                    self.window.ui.tabs['output'].setTabIcon(
                        tab,
                        QIcon(":/icons/paste.svg"),
                    )

        for idx in items:
            title = items[idx].title
            if items[idx].initialized and title is not None and len(title) > 0:
                self.update_name(
                    idx,
                    items[idx].title,
                    False,
                )

    def get_notepad_name(self, idx: int):
        """
        Get notepad name

        :param idx: notepad idx
        :return: notepad name
        """
        num = self.get_num_notepads()
        if num > 1:
            title = trans('text.context_menu.copy_to.notepad') + ' ' + str(idx)
        else:
            title = trans('text.context_menu.copy_to.notepad')
        item = self.window.core.notepad.get_by_id(idx)
        if item is None:
            return None
        if item.initialized and item.title is not None and len(item.title) > 0:
            title = item.title
        return title

    def rename(self, idx: int):
        """
        Rename tab

        :param idx: notepad index (real, not tab idx)
        """
        # get attachment object by ID
        item = self.window.core.notepad.get_by_id(idx)
        if item is None:
            return

        # set dialog and show
        self.window.ui.dialog['rename'].id = 'notepad'
        self.window.ui.dialog['rename'].input.setText(item.title)
        self.window.ui.dialog['rename'].current = idx
        self.window.ui.dialog['rename'].show()
        self.update()

    def update_name(self, idx: int, name: str, close: bool = True):
        """
        Update notepad title

        :param idx: notepad idx
        :param name: notepad name
        :param close: close dialog
        """
        num = self.get_num_notepads()
        item = self.window.core.notepad.get_by_id(idx)
        if item is None:
            item = NotepadItem()
            item.idx = idx
            self.window.core.notepad.items[idx] = item

        tab_idx = idx + (self.start_tab_idx - 1)  # calculate tab idx
        if name is None or len(name) == 0:
            # set default name
            if num > 1:
                self.window.ui.tabs['output'].setTabText(
                    tab_idx,
                    trans('output.tab.notepad') + " " + str(idx),
                )
            else:
                self.window.ui.tabs['output'].setTabText(
                    tab_idx,
                    trans('output.tab.notepad'),
                )
            item.title = ""
            item.initialized = False
        else:
            # set custom name
            self.window.ui.tabs['output'].setTabText(
                tab_idx,
                name,
            )
            item.title = name
            item.initialized = True
        self.window.core.notepad.update(item)
        if close:
            self.window.ui.dialog['rename'].close()

    def save(self, idx: int):
        """
        Save notepad contents

        :param idx: notepad idx
        """
        item = self.window.core.notepad.get_by_id(idx)
        if item is None:
            item = NotepadItem()
            item.idx = idx
            self.window.core.notepad.items[idx] = item

        if idx in self.window.ui.notepad:
            prev_content = item.content
            item.content = self.window.ui.notepad[idx].toPlainText()
            if prev_content != item.content:  # update only if content changed
                self.window.core.notepad.update(item)
            self.update()

    def save_all(self):
        """Save all notepads contents"""
        items = self.window.core.notepad.get_all()
        num_notepads = self.get_num_notepads()
        if num_notepads > 0:
            for idx in range(1, num_notepads + 1):
                if idx in self.window.ui.notepad:
                    prev_content = str(items[idx].content)
                    items[idx].content = self.window.ui.notepad[idx].toPlainText()
                    # update only if content changed
                    if prev_content != items[idx].content:
                        self.window.core.notepad.update(items[idx])
            self.update()

    def setup(self):
        """Setup all notepads"""
        self.setup_tabs()
        self.load()

    def append_text(self, text: str, idx: int):
        """
        Append text to notepad

        :param text: text to append
        :param idx: notepad idx
        """
        if idx not in self.window.ui.notepad:
            return
        dt = ""  # TODO: add to config append date/time
        # dt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ":\n--------------------------\n"
        prev_text = self.window.ui.notepad[idx].toPlainText()
        if prev_text.strip() != "":
            prev_text += "\n"
        new_text = prev_text + dt + text.strip()
        self.window.ui.notepad[idx].setText(new_text)
        self.save(idx)

        # move cursor to end
        cursor = self.window.ui.notepad[idx].textarea.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.window.ui.notepad[idx].textarea.setTextCursor(cursor)

    def get_num_notepads(self) -> int:
        """
        Get number of notepads

        :return: number of notepads
        """
        return int(self.window.core.config.get('notepad.num') or self.default_num_notepads)

    def get_current_active(self) -> int:
        """
        Get current notepad index

        :return: current notepad index
        """
        return self.window.ui.tabs['output'].currentIndex() - (self.start_tab_idx - 1)

    def is_active(self) -> bool:
        """
        Check if notepad tab is active

        :return: True if notepad tab is active
        """
        return self.window.ui.tabs['output'].currentIndex() >= self.start_tab_idx

    def rename_upd(self, idx: int, name: str):
        """
        Rename notepad tab

        :param idx: notepad idx
        :param name: new notepad name
        """
        item = self.window.core.notepad.get_by_id(idx)
        if item is None:
            item = NotepadItem()
            item.idx = idx
            self.window.core.notepad.items[idx] = item
        item.title = name
        self.window.core.notepad.update(item)
        self.update()

    def open(self):
        """Open notepad"""
        # if notepad disabled, do nothing
        if self.get_num_notepads() == 0:
            return
        # switch to first notepad tab if current tab is not notepad
        if self.window.controller.ui.current_tab < self.start_tab_idx:
            self.window.ui.tabs['output'].setCurrentIndex(self.start_tab_idx)
        self.window.activateWindow()  # focus

    def update(self):
        """Update notepads UI"""
        pass

    def reload(self):
        """Reload notepads"""
        self.window.core.notepad.locked = True
        self.window.core.notepad.reset()
        self.update_tabs()
        self.window.core.notepad.locked = False

    def switch_to_tab(self, idx: int = None):
        """
        Switch to notepad tab

        :param idx: notepad idx
        """
        if idx is None:
            idx = 1  # get first notepad idx
        tab = idx + (self.start_tab_idx - 1)
        if tab < self.window.ui.tabs['output'].count():
            self.window.ui.tabs['output'].setCurrentIndex(tab)
        else:
            self.window.ui.tabs['output'].setCurrentIndex(self.window.ui.tabs['output'].count() - 1)

    def get_first_notepad_tab_idx(self) -> int:
        """
        Get first notepad tab index

        :return: first notepad tab index
        """
        return self.start_tab_idx

    def get_current_notepad_text(self) -> str:
        """
        Get current notepad text

        :return: current notepad text
        """
        idx = self.get_current_active()
        if idx in self.window.ui.notepad:
            return self.window.ui.notepad[idx].toPlainText()
        return ""

    def get_notepad_text(self, idx: int) -> str:
        """
        Get notepad text

        :param idx: notepad index
        :return: notepad text
        """
        if idx in self.window.ui.notepad:
            return self.window.ui.notepad[idx].toPlainText()
        return ""

    def clear(self, idx: int) -> bool:
        """
        Clear notepad contents

        :param idx: notepad idx
        """
        if idx in self.window.ui.notepad:
            self.window.ui.notepad[idx].textarea.clear()
            self.save(idx)
            return True
        return False
