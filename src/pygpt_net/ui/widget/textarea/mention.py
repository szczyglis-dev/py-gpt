#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.18 10:55:00                  #
# ================================================== #

import os
from dataclasses import dataclass
from typing import Iterable, Optional

from PySide6.QtCore import Qt, Signal, QPoint, QSize, QFile
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QVBoxLayout,
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
)

from pygpt_net.core.text.mentions import KIND_ATTACHMENT, KIND_FILE_CONTEXT, KIND_CONVERSATION
from pygpt_net.utils import trans


# False disables icons only for workdir file rows.
WORKDIR_MENTIONS_SHOW_FILETYPE_ICONS = True

# Maximum Library rows in the [+] picker (newest uploads first).
ATTACHMENT_BUTTON_LIBRARY_LIMIT = 5


@dataclass(frozen=True, slots=True)
class MentionEntry:
    kind: str
    label: str
    value: str
    is_dir: bool = False
    icon: str = ""


class MentionPopup(QFrame):
    """Small non-activating picker shown above an active ``@`` trigger."""

    selected = Signal(object)

    ROLE_ENTRY = Qt.UserRole + 41
    ROLE_HEADER = Qt.UserRole + 42
    MAX_VISIBLE_ROWS = 9
    MAX_RESULTS = 250
    WIDTH = 430

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Tool | Qt.FramelessWindowHint)
        self.setProperty("class", "mention-popup")
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFocusPolicy(Qt.NoFocus)

        self.list = QListWidget(self)
        self.list.setProperty("class", "mention-popup-list")
        self.list.setFocusPolicy(Qt.NoFocus)
        self.list.setIconSize(QSize(16, 16))
        self.list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.setTextElideMode(Qt.ElideMiddle)
        self.list.itemClicked.connect(self._activate_item)
        self.list.itemActivated.connect(self._activate_item)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)
        layout.addWidget(self.list)

        self._entries: list[MentionEntry] = []
        self._query = ""
        self._from_attachment_button = False
        self.hide()

    def set_entries(self, entries: Iterable[MentionEntry], *, from_attachment_button: bool = False):
        self._from_attachment_button = from_attachment_button
        self._entries = list(entries or [])
        self._query = ""
        self.apply_filter("")

    def apply_filter(self, query: str) -> bool:
        raw_query = str(query or "").strip().replace("\\", "/")
        self._query = raw_query.casefold()
        matches = []

        # Workdir rows are files only. Keep their relative directory paths
        # visible and searchable, including descendants of a typed directory.
        for entry in self._entries:
            if entry.kind == KIND_FILE_CONTEXT and entry.is_dir:
                continue
            label = str(entry.label or "").replace("\\", "/")
            value = str(entry.value or "").replace("\\", "/")
            haystack = f"{label}\n{value}".casefold()
            if not self._query or self._query in haystack:
                matches.append(entry)

        self.list.clear()
        self._add_header(trans('input.mentions.add_new'))
        self._add_entry(MentionEntry('upload', trans('input.mentions.upload_files'), ''))
        self._add_entry(MentionEntry('sketch', trans('input.mentions.sketch'), ''))
        conversations = [e for e in matches if e.kind == KIND_CONVERSATION]
        attachments = [e for e in matches if e.kind == KIND_ATTACHMENT]
        files = [e for e in matches if e.kind == KIND_FILE_CONTEXT]

        conversations.sort(key=lambda e: e.label.casefold())
        if self._from_attachment_button:
            # The source supplies newest-first order for the button picker.
            attachments = attachments[:max(0, ATTACHMENT_BUTTON_LIBRARY_LIMIT)]
        else:
            attachments.sort(key=lambda e: e.label.casefold())
        files.sort(key=lambda e: e.label.casefold())

        # Keep the widget light even for very large project data trees. Filtering
        # still runs against the full entry set, so typing narrows into items
        # that were not present in the initial visible slice.
        visible = []
        visible.extend(conversations)
        visible.extend(attachments)
        visible.extend(files)
        visible = visible[:self.MAX_RESULTS]
        conversations = [e for e in visible if e.kind == KIND_CONVERSATION]
        attachments = [e for e in visible if e.kind == KIND_ATTACHMENT]
        files = [e for e in visible if e.kind == KIND_FILE_CONTEXT]

        if conversations:
            self._add_header(trans("input.mentions.chat_history"))
            for entry in conversations:
                self._add_entry(entry)
        if attachments:
            self._add_header(trans("input.mentions.library"))
            for entry in attachments:
                self._add_entry(entry)
        if files:
            self._add_header(trans("input.mentions.workdir"))
            for entry in files:
                self._add_entry(entry)

        readers = [entry for entry in matches if entry.kind == 'web_loader']
        if readers:
            self._add_header(trans('input.mentions.connect'))
            for entry in sorted(readers, key=lambda entry: entry.label.casefold()):
                self._add_entry(entry)

        self._select_first()
        self._resize_for_items()
        if self.list.count() == 0:
            self.hide()
            return False
        return True

    def _add_header(self, text: str):
        item = QListWidgetItem(text)
        item.setData(self.ROLE_HEADER, True)
        item.setFlags(Qt.NoItemFlags)
        font = QFont(item.font())
        font.setBold(True)
        item.setFont(font)
        self.list.addItem(item)

    def _add_entry(self, entry: MentionEntry):
        label = entry.label
        if entry.kind == KIND_FILE_CONTEXT and entry.is_dir and not label.endswith("/"):
            label += "/"
        item = QListWidgetItem(label)
        icon_name = {
            'upload': 'attachment',
            'sketch': 'brush',
            KIND_CONVERSATION: 'chat1',
            KIND_ATTACHMENT: 'upload',
        }.get(entry.kind)
        if entry.kind == 'web_loader':
            item.setIcon(QIcon(entry.icon or ':/icons/language.svg'))
        elif icon_name:
            item.setIcon(QIcon(f':/icons/{icon_name}.svg'))
        elif entry.kind == KIND_FILE_CONTEXT and WORKDIR_MENTIONS_SHOW_FILETYPE_ICONS:
            extension = os.path.splitext(entry.value or entry.label)[1].lower().lstrip('.')
            icon = extension if extension and QFile.exists(f':/filetypes/{extension}.svg') else 'default'
            item.setIcon(QIcon(f':/filetypes/{icon}.svg'))
        item.setData(self.ROLE_ENTRY, entry)
        item.setToolTip(entry.value)
        self.list.addItem(item)

    def _select_first(self):
        for row in range(self.list.count()):
            item = self.list.item(row)
            if item is not None and item.data(self.ROLE_ENTRY) is not None:
                self.list.setCurrentRow(row)
                return

    def _resize_for_items(self):
        rows = min(max(self.list.count(), 1), self.MAX_VISIBLE_ROWS)
        row_h = self.list.sizeHintForRow(0)
        if row_h <= 0:
            row_h = 28
        height = min(280, max(54, rows * row_h + 4))
        self.resize(self.WIDTH, height)

    def _activate_item(self, item: Optional[QListWidgetItem]):
        if item is None:
            return
        entry = item.data(self.ROLE_ENTRY)
        if entry is None:
            return
        self.hide()
        self.selected.emit(entry)

    def current_entry(self) -> Optional[MentionEntry]:
        item = self.list.currentItem()
        if item is None:
            return None
        return item.data(self.ROLE_ENTRY)

    def choose_current(self) -> bool:
        entry = self.current_entry()
        if entry is None:
            return False
        self.hide()
        self.selected.emit(entry)
        return True

    def move_selection(self, delta: int):
        count = self.list.count()
        if count <= 0:
            return
        row = self.list.currentRow()
        if row < 0:
            row = 0 if delta >= 0 else count - 1
        for _ in range(count):
            row = (row + delta) % count
            item = self.list.item(row)
            if item is not None and item.data(self.ROLE_ENTRY) is not None:
                self.list.setCurrentRow(row)
                self.list.scrollToItem(item, QAbstractItemView.EnsureVisible)
                return

    def show_above(self, anchor_global: QPoint, gap: int = 6):
        if self.list.count() <= 0:
            self.hide()
            return

        self.ensurePolished()
        self.layout().activate()
        self._resize_for_items()
        screen = QApplication.screenAt(anchor_global)
        geometry = screen.availableGeometry() if screen is not None else QApplication.primaryScreen().availableGeometry()

        x = anchor_global.x()
        y = anchor_global.y() - self.height() - gap
        x = max(geometry.left() + 4, min(x, geometry.right() - self.width() - 4))
        if y < geometry.top() + 4:
            y = anchor_global.y() + 22
        y = max(geometry.top() + 4, min(y, geometry.bottom() - self.height() - 4))

        self.move(x, y)
        self.show()
        self.raise_()
