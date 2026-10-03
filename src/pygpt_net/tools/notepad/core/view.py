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
"""Scroll restoration and deferred column focus for one editor."""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QTextCursor

class ViewState:
    def __init__(self, editor):
        self.editor = editor
        self.scrollbar = editor.verticalScrollBar()
        self.last_scroll_pos = None
        self.pending_scroll = None
        self.restore_attempts = 0
        self.focus_scheduled = False
        self.restore_timer = QTimer(editor)
        self.restore_timer.setSingleShot(True)
        self.restore_timer.timeout.connect(self.restore_scroll)
        self.focus_timer = QTimer(editor)
        self.focus_timer.setSingleShot(True)
        self.focus_timer.timeout.connect(self.sync_focus)

    def stop(self):
        self.restore_timer.stop()
        self.focus_timer.stop()

    def schedule_focus(self):
        """
        Post column-focus sync so it runs after the editor actually gained focus,
        preventing any intermediate handlers from consuming the first keystroke.
        """
        if self.editor.tab is None:
            return
        if self.focus_scheduled:
            return
        self.focus_scheduled = True
        self.focus_timer.start(0)

    def sync_focus(self):
        """Perform column-focus sync and keep editor focus if something tries to steal it."""
        self.focus_scheduled = False
        if self.editor.tab is None:
            return
        idx = getattr(self.editor.tab, 'column_idx', None)
        if idx is None:
            return
        had_focus = self.editor.hasFocus()
        try:
            self.editor.window.controller.tabs.on_column_focus(idx)
        except Exception:
            # Keep the UI resilient even if external handler fails
            pass
        # If external code changed focus, restore it to keep typing seamless
        if had_focus and not self.editor.hasFocus() and self.editor.isVisible():
            self.editor.setFocus(Qt.OtherFocusReason)

    def restore_scroll(self):
        """Restore last scroll position"""
        if self.editor.session.loading:
            self.restore_timer.start(25)
            return
        if not self.editor.initialized:
            return
        if self.pending_scroll is not None:
            self.last_scroll_pos = self.pending_scroll
        if self.last_scroll_pos is None:
            return
        scroll_bar = self.scrollbar
        current_max = scroll_bar.maximum()
        if current_max == 0:
            return  # nothing to scroll
        if self.last_scroll_pos > current_max:
            if self.restore_attempts < 30:
                self.restore_attempts += 1
                self.restore_timer.start(16)
            else:
                scroll_bar.setValue(current_max)
        else:
            self.editor.session.loading = True
            scroll_bar.setValue(self.last_scroll_pos)
            if self.pending_scroll is not None:
                self.pending_scroll = None
            self.editor.session.loading = False

    def set_scroll(self, pos: int):
        """
        Set scroll position

        :param pos: Scroll position
        """
        self.pending_scroll = pos
        self.last_scroll_pos = pos

    def scroll(self) -> int:
        """
        Get scroll position

        :return: Scroll position
        """
        return self.scrollbar.value()

    def bottom(self):
        """Scroll to bottom"""
        self.editor.moveCursor(QTextCursor.End)
        self.editor.ensureCursorVisible()
        scroll_bar = self.scrollbar
        scroll_bar.setValue(scroll_bar.maximum())

