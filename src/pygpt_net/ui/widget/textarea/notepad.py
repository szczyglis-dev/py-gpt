#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.02.05 02:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt, QEvent, QTimer
from PySide6.QtGui import (
    QAction,
    QIcon,
    QKeySequence,
    QTextCursor,
    QFontMetrics,
    QColor,
)
from PySide6.QtWidgets import QTextEdit, QWidget, QVBoxLayout

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.core.text.finder import Finder
from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.utils import trans
from .highlight import MarkerHighlighter


class NotepadWidget(QWidget):
    def __init__(self, window=None):
        """
        Notepad

        :param window: main window
        """
        super(NotepadWidget, self).__init__(window)
        self.window = window
        self.id = 1  # assigned in setup
        self.textarea = NotepadOutput(self.window)
        self.window.ui.nodes['tip.output.tab.notepad'] = HelpLabel(trans('tip.output.tab.notepad'), self.window)
        self.opened = False
        self.tab = None

        layout = QVBoxLayout()
        layout.addWidget(self.textarea)
        layout.addWidget(self.window.ui.nodes['tip.output.tab.notepad'])
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self.setProperty('class', 'layout-notepad')

    def set_tab(self, tab: Tab):
        """
        Set tab

        :param tab: Tab
        """
        self.tab = tab
        self.textarea.set_tab(tab)

    def scroll_to_bottom(self):
        """Scroll down"""
        self.textarea.scroll_to_bottom()

    def setText(self, text: str):
        """
        Set text

        :param text: Text
        """
        self.textarea.setText(text)
        self.textarea.on_update()

    def toPlainText(self) -> str:
        """
        Get plain text

        :return: Plain text
        """
        return self.textarea.toPlainText()

    def on_destroy(self):
        """On destroy"""
        # unregister finder from memory
        self.window.controller.finder.unset(self.textarea.finder)

    def on_delete(self):
        """On delete"""
        self.tab = None  # clear tab reference
        self.textarea.on_delete()  # delete textarea
        self.deleteLater()

class NotepadOutput(QTextEdit):
    ICON_VOLUME = QIcon(":/icons/volume.svg")
    ICON_SAVE = QIcon(":/icons/save.svg")
    ICON_SEARCH = QIcon(":/icons/search.svg")
    ICON_MARK = QIcon(":/icons/edit.svg")
    ICON_UNMARK = QIcon(":/icons/close.svg")

    def __init__(self, window=None):
        """
        Notepad output textarea

        :param window: main window
        """
        super(NotepadOutput, self).__init__(window)
        self.window = window
        self.finder = Finder(window, self)
        self.setAcceptRichText(False)
        self.setStyleSheet(self.window.controller.theme.style('font.chat.output'))

        # Ensure the editor always accepts keyboard focus on single click
        self.setFocusPolicy(Qt.StrongFocus)

        self.value = self.window.core.config.data['font_size']
        self.max_font_size = 42
        self.min_font_size = 8
        self.id = 1  # assigned in setup
        self.textChanged.connect(self.text_changed)
        self.tab = None
        self.last_scroll_pos = None
        self.installEventFilter(self)
        self.setProperty('class', 'layout-notepad')
        self.initialized = False

        metrics = QFontMetrics(self.font())
        space_width = metrics.horizontalAdvance(" ")
        self.setTabStopDistance(4 * space_width)

        self._vscroll = self.verticalScrollBar()
        self._vscroll.valueChanged.connect(self._on_scrollbar_value_changed)
        self._restore_attempts = 0
        self._pending_scroll_pos = None

        # highlight state (using QSyntaxHighlighter for rendering)
        self._highlights = []  # list of (start, length)

        # timers/slots must be available even if later connections fail
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(400)
        self._save_timer.timeout.connect(self._persist)

        # highlighter
        self._highlighter = MarkerHighlighter(self.document(), self.get_highlights, self.get_highlight_color)

        # schedule guard for column-focus sync
        self._column_focus_sync_scheduled = False

    def on_delete(self):
        """On delete"""
        if self.finder:
            self.finder.disconnect()  # disconnect finder
            self.finder = None  # delete finder
        if self._save_timer.isActive():
            self._save_timer.stop()
        self.deleteLater()

    def showEvent(self, event):
        """On show event"""
        super().showEvent(event)
        self._restore_attempts = 0
        QTimer.singleShot(0, self.restore_scroll_pos)
        self.initialized = True

    def changeEvent(self, event):
        """React to theme/palette changes"""
        if event.type() in (QEvent.PaletteChange, QEvent.ApplicationPaletteChange, QEvent.StyleChange):
            try:
                self._highlighter.rehighlight()
            except Exception:
                pass
        super().changeEvent(event)

    def scroll_to_bottom(self):
        """Scroll to bottom"""
        self.moveCursor(QTextCursor.End)
        self.ensureCursorVisible()
        scroll_bar = self._vscroll
        scroll_bar.setValue(scroll_bar.maximum())

    def eventFilter(self, source, event):
        """
        Focus event filter

        :param source: source
        :param event: event
        """
        if source is self and event.type() == QEvent.FocusIn:
            self._post_column_focus_sync()
        return super().eventFilter(source, event)

    def _post_column_focus_sync(self):
        """
        Post column-focus sync so it runs after the editor actually gained focus,
        preventing any intermediate handlers from consuming the first keystroke.
        """
        if self.tab is None:
            return
        if self._column_focus_sync_scheduled:
            return
        self._column_focus_sync_scheduled = True
        QTimer.singleShot(0, self._do_column_focus_sync)

    def _do_column_focus_sync(self):
        """Perform column-focus sync and keep editor focus if something tries to steal it."""
        self._column_focus_sync_scheduled = False
        if self.tab is None:
            return
        idx = getattr(self.tab, 'column_idx', None)
        if idx is None:
            return
        had_focus = self.hasFocus()
        try:
            self.window.controller.ui.tabs.on_column_focus(idx)
        except Exception:
            # Keep the UI resilient even if external handler fails
            pass
        # If external code changed focus, restore it to keep typing seamless
        if had_focus and not self.hasFocus() and self.isVisible():
            self.setFocus(Qt.OtherFocusReason)

    def set_tab(self, tab: Tab):
        """
        Set tab

        :param tab: Tab
        """
        self.tab = tab

    def setText(self, text: str):
        """
        Set text

        :param text: Text
        """
        if self.toPlainText() == text:
            return
        self.setPlainText(text)
        self._highlighter.rehighlight()  # refresh highlighting on new content

    def text_changed(self):
        """On text changed"""
        if not self.window.core.notepad.locked:
            if self.finder is not None:
                self.finder.text_changed()
            self.last_scroll_pos = self._vscroll.value()
            if self.initialized and not self.toPlainText():
                QTimer.singleShot(0, lambda: self.clear_highlights(persist=False))  # if empty, reset highlights
            self.schedule_save()

    def _on_scrollbar_value_changed(self, value: int):
        """
        On scrollbar value changed

        :param value: New value
        """
        if not self.window.core.notepad.locked:
            self.last_scroll_pos = value
            self.schedule_save()

    def is_initialized(self) -> bool:
        """
        Check if initialized

        :return: True if initialized
        """
        return self.initialized

    def restore_scroll_pos(self):
        """Restore last scroll position"""
        if self.window.core.notepad.locked:
            QTimer.singleShot(25, self.restore_scroll_pos)
            return
        if not self.initialized:
            return
        if self._pending_scroll_pos is not None:
            self.last_scroll_pos = self._pending_scroll_pos
        if self.last_scroll_pos is None:
            return
        scroll_bar = self._vscroll
        current_max = scroll_bar.maximum()
        if current_max == 0:
            return  # nothing to scroll
        if self.last_scroll_pos > current_max:
            if self._restore_attempts < 30:
                self._restore_attempts += 1
                QTimer.singleShot(16, self.restore_scroll_pos)
            else:
                scroll_bar.setValue(current_max)
        else:
            self.window.core.notepad.locked = True
            scroll_bar.setValue(self.last_scroll_pos)
            if self._pending_scroll_pos is not None:
                self._pending_scroll_pos = None
            self.window.core.notepad.locked = False

    def set_scroll_pos(self, pos: int):
        """
        Set scroll position

        :param pos: Scroll position
        """
        self._pending_scroll_pos = pos
        self.last_scroll_pos = pos

    def get_scroll_pos(self) -> int:
        """
        Get scroll position

        :return: Scroll position
        """
        return self._vscroll.value()

    def schedule_save(self):
        """Schedule save of notepad content"""
        try:
            self._save_timer.start()
        except Exception:
            pass

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: Event
        """
        menu = self.createStandardContextMenu()
        cursor = self.textCursor()
        selected_text = cursor.selectedText()
        has_selection = bool(selected_text)

        # Mark / Unmark actions for selection
        if has_selection:
            start = min(cursor.selectionStart(), cursor.selectionEnd())
            end = max(cursor.selectionStart(), cursor.selectionEnd())
            overlap = self._selection_overlaps_any_highlight(start, end)

            action_mark = QAction(self.ICON_MARK, trans("action.mark"), self)
            action_mark.triggered.connect(self.mark_selection)
            menu.addAction(action_mark)

            action_unmark = QAction(self.ICON_UNMARK, trans("action.unmark"), self)
            action_unmark.setEnabled(overlap)
            action_unmark.triggered.connect(self.unmark_selection)
            menu.addAction(action_unmark)

        if selected_text:
            plain_text = cursor.selection().toPlainText()

            action = QAction(self.ICON_VOLUME, trans('text.context_menu.audio.read'), self)
            action.triggered.connect(self.audio_read_selection)
            menu.addAction(action)

            excluded_id = f"notepad_id_{self.id}"
            copy_to_menu = self.window.ui.context_menu.get_copy_to_menu(menu, selected_text, excluded=[excluded_id])
            menu.addMenu(copy_to_menu)

            action = QAction(self.ICON_SAVE, trans('action.save_selection_as'), self)
            action.triggered.connect(
                lambda: self.window.controller.chat.common.save_text(plain_text))
            menu.addAction(action)
        else:
            action = QAction(self.ICON_SAVE, trans('action.save_as'), self)
            action.triggered.connect(
                lambda: self.window.controller.chat.common.save_text(self.toPlainText()))
            menu.addAction(action)

        # Add zoom submenu
        zoom_menu = self.window.ui.context_menu.get_zoom_menu(self, "font_size", self.value, self.on_zoom_changed)
        menu.addMenu(zoom_menu)

        action = QAction(self.ICON_SEARCH, trans('text.context_menu.find'), self)
        action.triggered.connect(self.find_open)
        action.setShortcut(QKeySequence("Ctrl+F"))
        menu.addAction(action)

        menu.exec_(event.globalPos())

    def audio_read_selection(self):
        """
        Read selected text (audio)
        """
        self.window.controller.audio.read_text(self.textCursor().selectedText())

    def find_open(self):
        """Open find dialog"""
        self.window.controller.finder.open(self.finder)

    def on_update(self):
        """On content update"""
        self.finder.clear()  # clear finder

    def on_zoom_changed(self, value: int):
        """
        On font size changed

        :param value: New font size
        """
        self.value = value
        self.window.core.config.data['font_size'] = value
        self.window.core.config.save()
        option = self.window.controller.settings.editor.get_option('font_size')
        option['value'] = self.value
        self.window.controller.config.apply(
                parent_id='config',
                key='font_size',
                option=option,
        )
        self.window.controller.ui.update_font_size()
        self.last_scroll_pos = self._vscroll.value()

    def keyPressEvent(self, e):
        """
        Key press event

        :param e: Event
        """
        if e.key() == Qt.Key_F and e.modifiers() & Qt.ControlModifier:
            self.find_open()
        else:
            self.finder.clear(restore=True, to_end=False)
            super(NotepadOutput, self).keyPressEvent(e)

    def wheelEvent(self, event):
        """
        Wheel event: set font size

        :param event: Event
        """
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                if self.value < self.max_font_size:
                    self.value += 1
                else:
                    return
            else:
                if self.value > self.min_font_size:
                    self.value -= 1
                else:
                    return

            self.window.core.config.data['font_size'] = self.value
            self.window.core.config.save()
            option = self.window.controller.settings.editor.get_option('font_size')
            option['value'] = self.value
            self.window.controller.config.apply(
                parent_id='config',
                key='font_size',
                option=option,
            )
            self.window.controller.ui.update_font_size()
            event.accept()
            self.last_scroll_pos = self._vscroll.value()
        else:
            super(NotepadOutput, self).wheelEvent(event)
            self.last_scroll_pos = self._vscroll.value()

    def mousePressEvent(self, e):
        """
        Ensure the editor grabs focus on first click and keep column state in sync.
        """
        if not self.hasFocus():
            # Force focus so the first keystroke is delivered to the editor
            self.setFocus(Qt.MouseFocusReason)
        super(NotepadOutput, self).mousePressEvent(e)
        self._post_column_focus_sync()

    def focusInEvent(self, e):
        """
        Focus in event

        :param e: focus event
        """
        self.window.controller.finder.focus_in(self.finder)
        super(NotepadOutput, self).focusInEvent(e)
        self._post_column_focus_sync()

    def focusOutEvent(self, e):
        """
        Focus out event

        :param e: focus event
        """
        super(NotepadOutput, self).focusOutEvent(e)
        self.window.controller.finder.focus_out(self.finder)

    # ==== Marking / Highlights API ====

    def mark_selection(self):
        """Apply highlight to current selection"""
        cursor = self.textCursor()
        if not cursor.hasSelection():
            return
        start = min(cursor.selectionStart(), cursor.selectionEnd())
        end = max(cursor.selectionStart(), cursor.selectionEnd())
        self._add_highlight((start, end - start))
        self._highlighter.rehighlight()
        self._persist()

    def unmark_selection(self):
        """Remove highlight from current selection"""
        cursor = self.textCursor()
        if not cursor.hasSelection():
            return
        start = min(cursor.selectionStart(), cursor.selectionEnd())
        end = max(cursor.selectionStart(), cursor.selectionEnd())
        self._remove_range_from_highlights(start, end - start)
        self._highlighter.rehighlight()
        self._persist()

    def get_highlights(self):
        """Return current highlights as list of (start, length)"""
        return list(self._highlights)

    def set_highlights(self, highlights):
        """Set highlights and repaint"""
        self._highlights = self._merge_ranges(self._sanitize_ranges(highlights))
        self._highlighter.rehighlight()

    def clear_highlights(self, persist: bool = True):
        """Clear all highlights"""
        self._highlights = []
        self._highlighter.rehighlight()
        if persist:
            self._persist()

    # ==== Highlight colors / theme ====

    def get_highlight_color(self):
        """
        Return (text_color, background_color) for highlights based on current theme.
        """
        is_dark = self._is_dark_theme()
        if is_dark:
            text_color = QColor(0, 0, 0)
            bg_color = QColor(255, 255, 0)  # yellow
        else:
            text_color = QColor(0, 0, 0)
            bg_color = QColor(255, 255, 0)  # yellow
        return text_color, bg_color

    def apply_highlight_theme(self):
        """
        Public method to refresh highlight colors. Can be called by theme controller
        after theme switch.
        """
        try:
            self._highlighter.rehighlight()
        except Exception:
            pass

    def _is_dark_theme(self) -> bool:
        """
        Get whether current theme is dark
        """
        return self.window.controller.theme.is_dark_theme()

    # ==== Internal highlight helpers ====

    def _persist(self):
        """Persist notepad state"""
        if self._save_timer.isActive():
            self._save_timer.stop()
        try:
            self.window.controller.notepad.save(self.id)  # save content + marking
        except Exception as e:
            print(e)

    def _sanitize_ranges(self, ranges):
        """Sanitize ranges to (start>=0, length>0) integers"""
        out = []
        for r in ranges or []:
            try:
                s = int(r[0])
                l = int(r[1])
            except Exception:
                continue
            if s < 0 or l <= 0:
                continue
            out.append((s, l))
        out.sort(key=lambda x: x[0])
        return out

    def _merge_ranges(self, ranges):
        """Merge overlapping/adjacent ranges"""
        if not ranges:
            return []
        merged = []
        for s, l in ranges:
            if not merged:
                merged.append([s, s + l])
                continue
            ps, pe = merged[-1]
            se = s + l
            if s <= pe:
                merged[-1][1] = max(pe, se)
            else:
                merged.append([s, se])
        return [(s, e - s) for s, e in merged]

    def _add_highlight(self, rng):
        """Add a highlight range and merge"""
        s, l = int(rng[0]), int(rng[1])
        if l <= 0:
            return
        self._highlights.append((s, l))
        self._highlights = self._merge_ranges(self._sanitize_ranges(self._highlights))
        self.schedule_save()

    def _remove_range_from_highlights(self, s, l):
        """Subtract a range from all highlights"""
        if l <= 0:
            return
        start = s
        end = s + l
        result = []
        for hs, hl in self._highlights:
            he = hs + hl
            if he <= start or hs >= end:
                result.append((hs, hl))
                continue
            if hs < start:
                result.append((hs, start - hs))
            if he > end:
                result.append((end, he - end))
        self._highlights = self._merge_ranges(self._sanitize_ranges(result))
        self.schedule_save()

    def _selection_overlaps_any_highlight(self, s, e):
        """Check if selection overlaps any highlight"""
        for hs, hl in self._highlights:
            he = hs + hl
            if not (he <= s or hs >= e):
                return True
        return False