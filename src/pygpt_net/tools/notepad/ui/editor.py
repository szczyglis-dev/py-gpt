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
"""Plain text editor integrating markers, menus, finder and viewport."""
from PySide6.QtCore import Qt, QEvent, QTimer
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QTextEdit, QSizePolicy
from pygpt_net.core.tabs.tab import Tab
from pygpt_net.core.text.finder import Finder
from pygpt_net.ui.widget.textarea.zoom import zoom_text
from ..core.markers import Markers
from ..core.view import ViewState
from .menus import EditorMenus
from .highlight import MARKER_PROPERTY

class NotepadOutput(QTextEdit):

    def __init__(self, session, window=None):
        """
        Notepad output textarea

        :param window: main window
        """
        super(NotepadOutput, self).__init__(window)
        self.window = window
        self.session = session
        self.finder = Finder(window, self)
        self.setAcceptRichText(False)
        self.apply_theme_style()

        # Ensure the editor always accepts keyboard focus on single click
        self.setFocusPolicy(Qt.StrongFocus)

        self.value = self.window.core.config.data['font_size']
        self.max_font_size = 42
        self.min_font_size = 8
        self.id = 1  # assigned in setup
        self.textChanged.connect(self.text_changed)
        self.tab = None
        self.installEventFilter(self)
        self.setProperty('class', 'layout-notepad-output')
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.initialized = False
        self._closed = False
        metrics = QFontMetrics(self.font())
        self.setTabStopDistance(4 * metrics.horizontalAdvance(" "))
        self.view = ViewState(self)
        self.markers = Markers(self)
        self.menus = EditorMenus(self)
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(400)
        self.save_timer.timeout.connect(self.persist)
        self.view.scrollbar.valueChanged.connect(self._on_scrollbar_value_changed)

    def minimumSizeHint(self):
        """Never let the notepad enforce a minimum width on an output column."""
        size = super().minimumSizeHint()
        size.setWidth(0)
        return size

    def apply_theme_style(self):
        """Apply chat-output typography and the plain-chat surface to the editor."""
        size = self.window.core.config.get('font_size')
        theme = self.window.controller.theme.common.normalize_theme(
            self.window.core.config.get('theme')
        )
        # Match the preset-list surface in each built-in color theme.
        backgrounds = {
            'light': '#efefef',
            'mint': '#e8f4ee',
            'gray': '#2b2d34',
            'gray_dark': '#222527',
            'dark': '#202020',
            'matrix': '#0d1710',
            'flare': '#170d0d',
            'retro': '#1c1233',
            'ocean': '#0d1a24',
            'sun': '#1b1206',
        }
        background = backgrounds.get(theme)
        if background is None:
            background = '#efefef' if self.window.controller.theme.common.is_light_theme_id(theme) else '#202020'
        self.setStyleSheet(
            'QTextEdit {'
            f'font-size: {size}px;'
            f'background-color: {background};'
            'border: none;'
            'border-radius: 10px;'
            'padding: 13px 10px 10px 10px;'
            '}'
        )

    def on_delete(self):
        if self._closed:
            return
        self._closed = True
        self.save_timer.stop()
        self.view.stop()
        self.finder.timer.stop()
        self.window.controller.finder.unset(self.finder)
        self.finder.disconnect()
        self.tab = None

    def contextMenuEvent(self, event):
        self.menus.context(event)

    def showEvent(self, event):
        """On show event"""
        super().showEvent(event)
        self.view.restore_attempts = 0
        self.view.restore_timer.start(0)
        self.initialized = True

    def changeEvent(self, event):
        """React to theme/palette changes"""
        if event.type() in (QEvent.PaletteChange, QEvent.ApplicationPaletteChange, QEvent.StyleChange):
            try:
                self.markers.highlighter.rehighlight()
            except Exception:
                pass
        super().changeEvent(event)

    def eventFilter(self, source, event):
        """
        Focus event filter

        :param source: source
        :param event: event
        """
        if source is self and event.type() == QEvent.FocusIn:
            self.view.schedule_focus()
        return super().eventFilter(source, event)

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
        self.markers.highlighter.rehighlight()  # refresh highlighting on new content

    def text_changed(self):
        """On text changed"""
        if not self.session.loading:
            if self.finder is not None:
                self.finder.text_changed()
            self.view.last_scroll_pos = self.view.scrollbar.value()
            if self.document().isEmpty():
                # Reset insertion style, not saved formatting: undo must still
                # restore the removed text together with its markers.
                fmt = self.currentCharFormat()
                fmt.setProperty(MARKER_PROPERTY, False)
                self.setCurrentCharFormat(fmt)
            self.schedule_save()

    def _on_scrollbar_value_changed(self, value: int):
        """
        On scrollbar value changed

        :param value: New value
        """
        if not self.session.loading:
            self.view.last_scroll_pos = value
            self.schedule_save()

    def schedule_save(self):
        """Schedule save of notepad content"""
        try:
            if not self._closed and not self.session.loading:
                self.save_timer.start()
        except Exception:
            pass

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
        zoom_text(self, self.window, value, 'font_size')

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
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta:
                value = max(self.min_font_size, min(self.max_font_size, self.value + (1 if delta > 0 else -1)))
                if value != self.value:
                    zoom_text(self, self.window, value, 'font_size')
            event.accept()
        else:
            super().wheelEvent(event)
        self.view.last_scroll_pos = self.view.scrollbar.value()

    def mousePressEvent(self, e):
        """
        Ensure the editor grabs focus on first click and keep column state in sync.
        """
        if not self.hasFocus():
            # Force focus so the first keystroke is delivered to the editor
            self.setFocus(Qt.MouseFocusReason)
        super(NotepadOutput, self).mousePressEvent(e)
        self.view.schedule_focus()

    def focusInEvent(self, e):
        """
        Focus in event

        :param e: focus event
        """
        self.window.controller.finder.focus_in(self.finder)
        super(NotepadOutput, self).focusInEvent(e)
        self.view.schedule_focus()

    def focusOutEvent(self, e):
        """
        Focus out event

        :param e: focus event
        """
        super(NotepadOutput, self).focusOutEvent(e)
        self.window.controller.finder.focus_out(self.finder)

    def persist(self):
        """Persist notepad state"""
        if self.save_timer.isActive():
            self.save_timer.stop()
        try:
            self.session.save()  # save content + marking
        except Exception as e:
            print(e)

