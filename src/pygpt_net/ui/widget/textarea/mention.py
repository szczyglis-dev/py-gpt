#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.05 16:00:00                  #
# ================================================== #

import os
from dataclasses import dataclass
from typing import Iterable, Optional

from PySide6.QtCore import Qt, Signal, QPoint, QSize, QFile, QRect, QEvent
from PySide6.QtGui import QFont, QIcon, QColor
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QVBoxLayout,
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
    QStyledItemDelegate, QStyleOptionViewItem, QStyle,
)

from pygpt_net.core.text.mentions import KIND_ATTACHMENT, KIND_FILE_CONTEXT, KIND_CONVERSATION
from pygpt_net.utils import trans


# False disables icons only for workdir file rows.
WORKDIR_MENTIONS_SHOW_FILETYPE_ICONS = True

# Maximum Library rows in the [+] picker (newest uploads first).
ATTACHMENT_BUTTON_LIBRARY_LIMIT = 5

MENTION_HEADER_COLOR = QColor("#808080")


@dataclass(frozen=True, slots=True)
class MentionEntry:
    kind: str
    label: str
    value: str
    is_dir: bool = False
    icon: str = ""
    shared: bool = False
    active: bool = True
    attachment_id: str = ""


class SharingDelegate(QStyledItemDelegate):
    """Paint controls inside the themed item, without embedded header widgets."""

    def paint(self, painter, option, index):
        action = index.data(MentionPopup.ROLE_TOGGLE)
        label_only = bool(index.data(MentionPopup.ROLE_SHARING_LABEL))
        if not action and not label_only:
            return super().paint(painter, option, index)
        item_option = QStyleOptionViewItem(option)
        self.initStyleOption(item_option, index)
        label_width = option.fontMetrics.horizontalAdvance(trans("input.mentions.sharing")) + 12
        room = option.rect.width() - (label_width + 20 if label_only else 64)
        item_option.text = option.fontMetrics.elidedText(item_option.text, Qt.ElideMiddle, max(0, room))
        style = option.widget.style() if option.widget else QApplication.style()
        style.drawControl(QStyle.CE_ItemViewItem, item_option, painter, option.widget)
        rect = self.toggle_rect(option.rect)
        if label_only:
            painter.save()
            painter.setPen(MENTION_HEADER_COLOR)
            painter.drawText(QRect(option.rect.right() - 8 - label_width, option.rect.top(), label_width, option.rect.height()),
                             Qt.AlignRight | Qt.AlignVCenter, trans("input.mentions.sharing"))
            painter.restore()
            return
        state = bool(index.data(MentionPopup.ROLE_CHECKED))
        QIcon(f":/icons/toggle_{'on' if state else 'off'}.svg").paint(painter, rect)

    @staticmethod
    def toggle_rect(rect):
        return QRect(rect.right() - 37, rect.center().y() - 12, 32, 24)


class MentionPopup(QFrame):
    """Small non-activating picker shown above an active ``@`` trigger."""

    selected = Signal(object)
    attachment_share_changed = Signal(str, bool)
    library_share_changed = Signal(bool)

    ROLE_ENTRY = Qt.UserRole + 41
    ROLE_HEADER = Qt.UserRole + 42
    ROLE_TOGGLE = Qt.UserRole + 43
    ROLE_CHECKED = Qt.UserRole + 44
    ROLE_SHARING_LABEL = Qt.UserRole + 45
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
        self.list.setItemDelegate(SharingDelegate(self.list))
        self.list.viewport().installEventFilter(self)
        self.list.itemClicked.connect(self._activate_item)
        self.list.itemActivated.connect(self._activate_item)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)
        layout.addWidget(self.list)

        self._project_available = False
        self._project_shared = False
        self._library_shared = False
        self._library_limit = ATTACHMENT_BUTTON_LIBRARY_LIMIT
        self._entries: list[MentionEntry] = []
        self._search_entries = []
        self._library_entries = []
        self._query = ""
        self._from_attachment_button = False
        self.hide()

    def set_entries(self, entries: Iterable[MentionEntry], *, from_attachment_button: bool = False, query: str = ''):
        entries = list(entries or [])
        if entries != self._entries or from_attachment_button != self._from_attachment_button:
            self._entries = entries
            ordered = entries if from_attachment_button else sorted(entries, key=lambda e: e.label.casefold())
            self._search_entries = [
                (entry, (str(entry.label or '') + '\n' + str(entry.value or '')).replace('\\', '/').casefold())
                for entry in ordered if entry.kind != KIND_FILE_CONTEXT or not entry.is_dir
            ]
            self._library_entries = [entry for entry in entries if entry.kind == KIND_ATTACHMENT]
        self._from_attachment_button = from_attachment_button
        self._library_limit = ATTACHMENT_BUTTON_LIBRARY_LIMIT
        if not any(entry.kind == KIND_ATTACHMENT for entry in self._entries):
            self._library_shared = False
        return self.apply_filter(query)

    def apply_filter(self, query: str) -> bool:
        raw_query = str(query or "").strip().replace("\\", "/")
        self._query = raw_query.casefold()
        matches = []

        # Normalize and sort once per source snapshot, not for every keystroke.
        for entry, haystack in self._search_entries:
            if not self._query or self._query in haystack:
                matches.append(entry)

        library_entries = self._library_entries
        self.list.clear()
        self._add_header(trans('input.mentions.add_new'))
        if self._project_available:
            self.list.item(0).setData(self.ROLE_SHARING_LABEL, True)
        self._add_entry(MentionEntry('upload', trans('input.mentions.upload_files'), ''))
        self._add_entry(MentionEntry('sketch', trans('input.mentions.sketch'), ''))
        conversations = [e for e in matches if e.kind == KIND_CONVERSATION]
        attachments = [e for e in matches if e.kind == KIND_ATTACHMENT]
        files = [e for e in matches if e.kind == KIND_FILE_CONTEXT]

        if self._query.isdigit():
            conversations.sort(key=lambda e: (e.value != self._query, e.label.casefold()))
        if self._from_attachment_button:
            conversations.sort(key=lambda e: e.label.casefold())
            files.sort(key=lambda e: e.label.casefold())
            # The source supplies newest-first order for the button picker.
            more_library = len(attachments) > self._library_limit
            attachments = attachments[:self._library_limit]

        # Filtering runs against complete source sets before applying display limits.
        visible = conversations[:self.MAX_RESULTS] + attachments + files[:self.MAX_RESULTS]
        conversations = [e for e in visible if e.kind == KIND_CONVERSATION]
        attachments = [e for e in visible if e.kind == KIND_ATTACHMENT]
        files = [e for e in visible if e.kind == KIND_FILE_CONTEXT]

        if files:
            self._add_header(trans("input.mentions.workdir"))
            for entry in files:
                self._add_entry(entry)
        if conversations:
            self._add_header(trans("input.mentions.chat_history"))
            for entry in conversations:
                self._add_entry(entry)
        if attachments or (self._project_available and library_entries):
            self._add_library_header(library_entries)
            for entry in attachments:
                self._add_entry(entry)
            if self._from_attachment_button and attachments and more_library:
                self._add_entry(MentionEntry("load_more", trans("input.mentions.load_more"), ""))
            elif self._from_attachment_button and attachments and self._library_limit > ATTACHMENT_BUTTON_LIBRARY_LIMIT:
                self._add_entry(MentionEntry("show_less", trans("input.mentions.show_less"), ""))

        readers = [entry for entry in matches if entry.kind == 'web_loader']
        if readers:
            self._add_header(trans('input.mentions.connect'))
            for entry in sorted(readers, key=lambda entry: entry.label.casefold()):
                self._add_entry(entry)

        if self._from_attachment_button:
            self.list.setCurrentRow(-1)
            self.list.clearSelection()
        else:
            self._select_first()
        self._resize_for_items()
        if self.list.count() == 0:
            self.hide()
            return False
        return True

    def set_project_state(self, available, enabled, library_enabled=False):
        self._project_available = bool(available)
        self._project_shared = bool(enabled)
        self._library_shared = bool(library_enabled)

    def _set_toggle(self, item, action, enabled):
        item.setData(self.ROLE_TOGGLE, action)
        item.setData(self.ROLE_CHECKED, bool(enabled))
        item.setToolTip(trans("input.mentions.sharing.all.tooltip" if action == "library"
                              else "input.mentions.sharing.tooltip"))

    def _add_library_header(self, entries):
        label = trans("input.mentions.library")
        shared_count = sum(bool(entry.attachment_id) and entry.active for entry in entries) if self._project_available else 0
        if shared_count:
            label += " (" + trans("input.mentions.shared_count").format(count=shared_count) + ")"
        self._add_header(label)
        if self._project_available and entries:
            # Include filtered rows and rows beyond the visible limit.
            if all(entry.active for entry in entries):
                self._library_shared = True
            elif not any(entry.active for entry in entries):
                self._library_shared = False
            self._set_toggle(self.list.item(self.list.count() - 1), "library",
                             self._library_shared)

    def eventFilter(self, watched, event):
        if watched is self.list.viewport() and event.type() in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease):
            if event.button() == Qt.LeftButton:
                item = self.list.itemAt(event.position().toPoint())
                if item is not None and item.data(self.ROLE_TOGGLE):
                    rect = SharingDelegate.toggle_rect(self.list.visualItemRect(item))
                    if rect.contains(event.position().toPoint()):
                        if event.type() == QEvent.MouseButtonRelease:
                            enabled = not bool(item.data(self.ROLE_CHECKED))
                            action = item.data(self.ROLE_TOGGLE)
                            if action == "library":
                                self._library_shared = enabled
                                item.setData(self.ROLE_CHECKED, enabled)
                                self.library_share_changed.emit(enabled)
                            else:
                                self.attachment_share_changed.emit(action, enabled)
                        return True
        return super().eventFilter(watched, event)

    def _load_more(self):
        row = self.list.currentRow()
        scroll = self.list.verticalScrollBar().value()
        self._library_limit += ATTACHMENT_BUTTON_LIBRARY_LIMIT
        self.apply_filter(self._query)
        self.list.setCurrentRow(min(row, self.list.count() - 1))
        self.list.verticalScrollBar().setValue(scroll)

    def _show_less(self):
        self._library_limit = ATTACHMENT_BUTTON_LIBRARY_LIMIT
        self.apply_filter(self._query)
        self.list.verticalScrollBar().setValue(0)

    def _add_header(self, text: str):
        item = QListWidgetItem(text)
        item.setForeground(MENTION_HEADER_COLOR)
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
        if entry.kind in ("load_more", "show_less"):
            item.setTextAlignment(Qt.AlignCenter)
        icon_name = {
            'upload': 'attachment',
            'sketch': 'brush',
            KIND_CONVERSATION: 'chat1',
        }.get(entry.kind)
        if entry.kind == 'web_loader':
            item.setIcon(QIcon(entry.icon or ':/icons/language.svg'))
        elif entry.kind == KIND_ATTACHMENT and entry.icon:
            item.setIcon(QIcon(entry.icon))
        elif icon_name:
            item.setIcon(QIcon(f':/icons/{icon_name}.svg'))
        elif entry.kind == KIND_ATTACHMENT or (entry.kind == KIND_FILE_CONTEXT and WORKDIR_MENTIONS_SHOW_FILETYPE_ICONS):
            filename = entry.label if entry.kind == KIND_ATTACHMENT else (entry.value or entry.label)
            extension = os.path.splitext(filename)[1].lower().lstrip('.')
            icon = extension if extension and QFile.exists(f':/filetypes/{extension}.svg') else 'default'
            item.setIcon(QIcon(f':/filetypes/{icon}.svg'))
        item.setData(self.ROLE_ENTRY, entry)
        item.setToolTip(entry.label if entry.shared else entry.value)
        self.list.addItem(item)
        if entry.kind == KIND_ATTACHMENT and self._project_available and entry.attachment_id:
            self._set_toggle(item, entry.attachment_id, entry.active)

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
        if entry.kind == "load_more":
            self._load_more()
            return
        if entry.kind == "show_less":
            self._show_less()
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
        if entry.kind == "load_more":
            self._load_more()
            return True
        if entry.kind == "show_less":
            self._show_less()
            return True
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
