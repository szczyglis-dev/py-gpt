#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.25 20:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QIcon, QImage
from PySide6.QtWidgets import QTextEdit, QApplication, QPushButton

from pygpt_net.utils import trans

class ChatInput(QTextEdit):

    ICON_PASTE = QIcon(":/icons/paste.svg")
    ICON_VOLUME = QIcon(":/icons/volume.svg")
    ICON_SAVE = QIcon(":/icons/save.svg")
    ICON_ATTACHMENT = QIcon(":/icons/add.svg")

    def __init__(self, window=None):
        """
        Chat input

        :param window: main window
        """
        super().__init__(window)
        self.window = window
        self.setAcceptRichText(False)
        self.setFocus()
        self.value = self.window.core.config.data['font_size.input']
        self.max_font_size = 42
        self.min_font_size = 8
        self._text_top_padding = 10
        self.textChanged.connect(self.window.controller.ui.update_tokens)
        self.setProperty('class', 'layout-input')

        # Add a "+" button in the top-left corner to add attachments
        self._init_attachment_button()
        self._apply_text_top_padding()

    def _apply_text_top_padding(self):
        """Apply extra top padding inside the text area by using viewport margins."""
        m = self.viewportMargins()
        self.setViewportMargins(m.left(), self._text_top_padding, m.right(), m.bottom())

    def set_text_top_padding(self, px: int):
        """Public helper to adjust top padding at runtime."""
        self._text_top_padding = max(0, int(px))
        self._apply_text_top_padding()

    def insertFromMimeData(self, source):
        """
        Insert from mime data

        :param source: source
        """
        self.handle_clipboard(source)
        if not source.hasImage():
            super().insertFromMimeData(source)

    def handle_clipboard(self, source):
        """
        Handle clipboard

        :param source: source
        """
        if source.hasImage():
            image = source.imageData()
            if isinstance(image, QImage):
                self.window.controller.attachment.from_clipboard_image(image)
        elif source.hasUrls():
            urls = source.urls()
            for url in urls:
                if url.isLocalFile():
                    local_path = url.toLocalFile()
                    self.window.controller.attachment.from_clipboard_url(local_path)
        elif source.hasText():
            text = source.text()
            if text:
                self.window.controller.attachment.from_clipboard_text(text)

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: event
        """
        menu = self.createStandardContextMenu()
        try:
            if self.window.controller.attachment.clipboard_has_attachment():
                action = QAction(self.ICON_PASTE, trans("action.use.attachment"), menu)
                action.triggered.connect(self.action_from_clipboard)
                menu.addAction(action)

            cursor = self.textCursor()
            selected_text = cursor.selectedText()
            if selected_text:
                plain_text = cursor.selection().toPlainText()

                action = QAction(self.ICON_VOLUME, trans('text.context_menu.audio.read'), menu)
                action.triggered.connect(self.audio_read_selection)
                menu.addAction(action)

                copy_to_menu = self.window.ui.context_menu.get_copy_to_menu(menu, selected_text, excluded=["input"])
                menu.addMenu(copy_to_menu)

                action = QAction(self.ICON_SAVE, trans('action.save_selection_as'), menu)
                action.triggered.connect(lambda: self.window.controller.chat.common.save_text(plain_text))
                menu.addAction(action)
            else:
                action = QAction(self.ICON_SAVE, trans('action.save_as'), menu)
                action.triggered.connect(lambda: self.window.controller.chat.common.save_text(self.toPlainText()))
                menu.addAction(action)

            try:
                self.window.core.prompt.template.to_menu_options(menu, "input")
                self.window.core.prompt.custom.to_menu_options(menu, "input")
            except Exception as e:
                self.window.core.debug.log(e)

            action = QAction(self.ICON_SAVE, trans('preset.prompt.save_custom'), menu)
            action.triggered.connect(self.window.controller.presets.save_prompt)
            menu.addAction(action)

            menu.exec(event.globalPos())
        finally:
            menu.deleteLater()

    def action_from_clipboard(self):
        """
        Get from clipboard
        """
        clipboard = QApplication.clipboard()
        source = clipboard.mimeData()
        self.handle_clipboard(source)

    def audio_read_selection(self):
        """Read selected text (audio)"""
        self.window.controller.audio.read_text(self.textCursor().selectedText())

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key event
        """
        handled = False
        key = event.key()
        if key in (Qt.Key_Return, Qt.Key_Enter):
            mode = self.window.core.config.get('send_mode')
            if mode > 0:
                modifiers = event.modifiers()
                if mode == 2:
                    if modifiers == Qt.ShiftModifier or modifiers == Qt.ControlModifier:
                        self.window.controller.chat.input.send_input()
                        handled = True
                else:
                    if modifiers != Qt.ShiftModifier and modifiers != Qt.ControlModifier:
                        self.window.controller.chat.input.send_input()
                        handled = True
                self.setFocus()
        elif key == Qt.Key_Escape and self.window.controller.ctx.extra.is_editing():
            self.window.controller.ctx.extra.edit_cancel()
            handled = True

        if not handled:
            super().keyPressEvent(event)

    def wheelEvent(self, event):
        """
        Wheel event: set font size

        :param event: Event
        """
        if event.modifiers() & Qt.ControlModifier:
            prev = self.value
            dy = event.angleDelta().y()
            if dy > 0:
                if self.value < self.max_font_size:
                    self.value += 1
            else:
                if self.value > self.min_font_size:
                    self.value -= 1

            if self.value != prev:
                self.window.core.config.data['font_size.input'] = self.value
                self.window.core.config.save()
                self.window.controller.ui.update_font_size()
            event.accept()
            return
        super().wheelEvent(event)

    # --- Added: attachment button (top-left) ---------------------------------

    def _init_attachment_button(self):
        """Create and place the '+' attachment button pinned in the top-left corner."""
        self._attach_margin = 6  # inner padding around the button
        self._attach_offset_y = -6  # shift the button 2px up

        self._attach_btn = QPushButton(self)
        self._attach_btn.setObjectName("chatInputAttachBtn")
        self._attach_btn.setIconSize(QSize(18, 18)) # icon size (slightly larger for visibility)
        self._attach_btn.setFixedSize(24, 24) # full button size
        self._attach_btn.setCursor(Qt.PointingHandCursor)
        self._attach_btn.setToolTip(trans("attachments.btn.input.add"))
        self._attach_btn.setFocusPolicy(Qt.NoFocus)
        self._attach_btn.setFlat(True) # flat button style

        self._attach_btn.setIcon(self.ICON_ATTACHMENT)
        self._attach_btn.clicked.connect(self.action_add_attachment)
        self._update_viewport_margins_for_attachment()
        self._reposition_attachment_button()

    def _update_viewport_margins_for_attachment(self):
        """Reserve space for the attachment button on the left and apply top text padding."""
        top = self._text_top_padding
        left = self._attach_btn.width() + self._attach_margin * 2 if hasattr(self, "_attach_btn") else self.viewportMargins().left()
        self.setViewportMargins(left, top, 0, 0)

    def _reposition_attachment_button(self):
        """Keep the attachment button pinned to the top-left corner."""
        if hasattr(self, "_attach_btn"):
            fw = self.frameWidth()
            x = fw + self._attach_margin
            y = fw + self._attach_margin + self._attach_offset_y  # shift up by ~2px
            if y < 0:
                y = 0
            self._attach_btn.move(x, y)
            self._attach_btn.raise_()

    def resizeEvent(self, event):
        """Resize event keeps the attachment button in place."""
        super().resizeEvent(event)
        # Keep the attachment button pinned when resizing
        try:
            self._reposition_attachment_button()
        except Exception:
            pass

    def action_add_attachment(self):
        """Add attachment (button click)."""
        self.window.controller.attachment.open_add()