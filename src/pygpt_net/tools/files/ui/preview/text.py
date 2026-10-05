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

import os

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QIcon, QTextCursor
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QPlainTextEdit, QPlainTextDocumentLayout, QVBoxLayout, QFrame

from pygpt_net.core.text.editor import TextEditor
from pygpt_net.utils import trans


class PreviewDocumentLayout(QPlainTextDocumentLayout):
    """A little extra breathing room between source lines."""

    def blockBoundingRect(self, block):
        rect = super().blockBoundingRect(block)
        if block.isVisible():
            rect.setHeight(rect.height() + 2)
        return rect


class TextPreview(TextEditor):
    zoom_key = "filesystem.preview.text.font_size"
    def __init__(self, panel, path, text):
        self.panel = panel
        self.annotation_ranges = ()
        self._baseline_content = str(text)
        super().__init__(
            window=panel.window,
            parent=panel,
            path=os.path.abspath(path),
            line_numbers=True,
            syntax_highlighting=True,
            tabs=True,
        )
        self.setObjectName('filesPreviewText')
        self.line_numbers.setProperty('transparent_background', True)
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet(self.styleSheet() +
                          '\nQPlainTextEdit { border: none; font-family: "Monaspace Neon"; font-weight: normal; letter-spacing: 0px; }')
        self.document().setDocumentLayout(PreviewDocumentLayout(self.document()))
        self.annotation_timer = QTimer(self)
        self.annotation_timer.setInterval(150)
        self.annotation_timer.timeout.connect(self.refresh_annotations)
        self.setPlainText(self._baseline_content)
        # QTextDocument normalizes line endings and paragraph separators while
        # loading. Compare edits against that representation, not raw file bytes.
        self._baseline_content = self.toPlainText()
        self.ensurePolished()
        self.document().setModified(False)
        self.textChanged.connect(self._sync_modified_state)
        self.update_gutter()
        self.highlight_line()


    def set_baseline_content(self, text=None):
        """Set the current text as the clean baseline used for dirty-state checks."""
        self._baseline_content = self.toPlainText() if text is None else str(text)
        self._sync_modified_state()

    def is_content_modified(self):
        """Return True only when current contents differ from the clean baseline."""
        return self.toPlainText() != self._baseline_content

    def _sync_modified_state(self):
        """Keep Qt's modified flag aligned with the actual content comparison."""
        changed = self.is_content_modified()
        document = self.document()
        if document.isModified() != changed:
            document.setModified(changed)

    def is_line_marked(self, line_number):
        return any(start <= line_number <= end for start, end in self.annotation_ranges)

    def annotation_session(self):
        window = self.panel.window
        return window.controller.chat.text.get_annotations(window.core.ctx.get_current_meta())

    def refresh_annotations(self):
        """Follow the active conversation, including removals after model delivery."""
        session = self.annotation_session()
        items = session.annotations if session is not None else []
        ranges = ()
        if items:
            path = os.path.relpath(self.path, self.panel.window.core.filesystem.get_data_dir()).replace(os.sep, '/')
            ranges = tuple(
                (item['start_line'], item['end_line'])
                for item in items
                if item.get('source') == 'files' and item.get('path') == path
            )
        if ranges != self.annotation_ranges:
            self.annotation_ranges = ranges
            self.highlight_line()

    def annotate(self, cursor):
        session = self.annotation_session()
        if session is None:
            return
        cursor = QTextCursor(cursor)
        if not cursor.hasSelection():
            cursor.select(QTextCursor.LineUnderCursor)
        start = self.document().findBlock(cursor.selectionStart()).blockNumber() + 1
        end = self.document().findBlock(max(cursor.selectionStart(), cursor.selectionEnd() - 1)).blockNumber() + 1
        selected = cursor.selection().toPlainText()
        workdir = self.panel.window.core.filesystem.get_data_dir()
        path = os.path.relpath(self.path, workdir).replace(os.sep, '/')
        dialog = QDialog(self)
        dialog.setWindowTitle(trans('ui.annotation_title', domain='plugin.canvas_web'))
        layout = QVBoxLayout(dialog)
        label = QLabel(f'{path}:{start}–{end}')
        label.setTextFormat(Qt.PlainText)
        label.setWordWrap(True)
        layout.addWidget(label)
        note = QPlainTextEdit(dialog)
        note.setPlaceholderText(trans('ui.annotation_selection_prompt', domain='plugin.canvas_web'))
        layout.addWidget(note)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setEnabled(False)
        note.textChanged.connect(
            lambda: buttons.button(QDialogButtonBox.Save).setEnabled(bool(note.toPlainText().strip()))
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.resize(420, 220)
        if dialog.exec() == QDialog.Accepted:
            session.add_file_annotation(path, start, end, selected, note.toPlainText())
            self.refresh_annotations()
        dialog.deleteLater()

    def on_destroy(self):
        self.annotation_timer.stop()
        super().on_destroy()

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_annotations()
        self.annotation_timer.start()

    def hideEvent(self, event):
        self.annotation_timer.stop()
        super().hideEvent(event)

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        menu.addSeparator()
        cursor = self.textCursor() if self.textCursor().hasSelection() else self.cursorForPosition(event.pos())
        action = menu.addAction(
            QIcon(":/icons/chat3.svg"),
            trans('ui.annotate_selection', domain='plugin.canvas_web'),
            lambda: self.annotate(cursor),
        )
        session = self.annotation_session()
        action.setEnabled(session is not None)
        if session is not None:
            path = os.path.relpath(self.path, self.panel.window.core.filesystem.get_data_dir()).replace(os.sep, '/')
            items = [
                item for item in session.annotations
                if item.get('source') == 'files' and item.get('path') == path
            ]
            if items:
                annotations = menu.addMenu(trans('ui.annotation_title', domain='plugin.canvas_web'))
                for item in items:
                    entry = annotations.addMenu(f"{item['start_line']}–{item['end_line']}: {item['note'][:60]}")
                    entry.setToolTip(item['note'])
                    entry.addAction(
                        trans('ui.remove_annotation', domain='plugin.canvas_web'),
                        lambda checked=False, aid=item['id']: session._remove_annotation(aid),
                    )

        self.panel.add_file_actions(menu)
        self.add_find_action(menu)
        self.get_tabs_menu(menu)
        menu.addMenu(self.panel.window.ui.context_menu.get_copy_to_menu(
            menu,
            selected_text_provider=lambda: self.textCursor().selection().toPlainText()
            if self.textCursor().hasSelection() else self.toPlainText(),
        ))
        self.add_zoom_menu(menu)
        menu.addSeparator()
        self.add_word_wrap_action(menu)
        menu.exec(event.globalPos())
        menu.deleteLater()
