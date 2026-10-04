#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.01 22:20:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QPlainTextEdit, QVBoxLayout

from pygpt_net.utils import trans


def _column_value(item, column: int) -> str:
    """Return the visible value for a list column, including checkbox state."""
    value = str(item.text(column) or "")
    if value:
        return value
    if column == 0 and item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
        return "✓" if item.checkState(column) == Qt.CheckState.Checked else "—"
    return ""


def set_item_tooltips(tree, item, extra: dict[int, str] | None = None):
    """Expose every full cell value as a tooltip without losing extra diagnostics."""
    extra = extra or {}
    header = tree.headerItem()
    for column in range(tree.columnCount()):
        value = _column_value(item, column)
        addition = str(extra.get(column) or "").strip()
        parts = []
        if value:
            parts.append(value)
        if addition and addition not in parts:
            parts.append(addition)
        tooltip = "\n\n".join(parts)
        if not tooltip:
            label = str(header.text(column) or "").strip() if header is not None else ""
            if label and column == 0 and item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                tooltip = f"{label}: {_column_value(item, column)}"
        item.setToolTip(column, tooltip)
        widget = tree.itemWidget(item, column)
        if widget is not None:
            widget.setToolTip(tooltip)


def show_item_details(parent, tree, item):
    """Show all visible row fields in a compact, copyable details dialog."""
    if tree is None or item is None:
        return
    header = tree.headerItem()
    lines = []
    for column in range(tree.columnCount()):
        label = str(header.text(column) or "").strip() if header is not None else ""
        if not label:
            continue
        lines.append(f"{label}: {_column_value(item, column)}")

    dialog = QDialog(parent)
    dialog.setWindowTitle(trans("action.show_details"))
    dialog.setWindowIcon(QIcon(":/icons/info.svg"))
    dialog.setMinimumSize(520, 300)
    dialog.resize(640, 380)

    text = QPlainTextEdit(dialog)
    text.setReadOnly(True)
    text.setPlainText("\n\n".join(lines))
    text.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)

    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, parent=dialog)
    buttons.rejected.connect(dialog.reject)

    layout = QVBoxLayout(dialog)
    layout.addWidget(text, 1)
    layout.addWidget(buttons)
    dialog.exec()
