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


from PySide6.QtCore import Qt, QModelIndex, QUrl, QPoint, QPointF, QMimeData, QItemSelectionModel
from PySide6.QtGui import QGuiApplication, QDrag, QPainter, QPen, QPalette
from PySide6.QtWidgets import QTreeView


class MultiDragTreeView(QTreeView):
    """
    QTreeView with improved multi-selection UX:
    - When multiple rows are already selected and user presses left mouse (no modifiers),
      a short press-release clears selection (global single-click to deselect),
      but moving the mouse beyond the drag threshold starts a drag containing the whole selection
      instead of altering selection.
    - This avoids accidental selection changes when the intent was to drag many items.
    - Shift-range selection anchor is kept stable to avoid selecting the entire directory accidentally.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._md_pressed = False
        self._md_drag_started = False
        self._md_maybe_clear = False
        self._md_press_pos = QPoint()
        self._md_press_index = QModelIndex()
        self._sel_anchor_index = QModelIndex()

    def drawBranches(self, painter, rect, index):
        """Compact chevrons use the current theme's text color."""
        if not self.model().hasChildren(index):
            return
        center = QPointF(rect.right() - self.indentation() / 2 + 1, rect.center().y())
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(self.palette().color(QPalette.Text), 1))
        if self.isExpanded(index):
            points = [QPointF(-4, -2), QPointF(0, 2), QPointF(4, -2)]
        else:
            points = [QPointF(-2, -4), QPointF(2, 0), QPointF(-2, 4)]
        painter.drawPolyline([center + point for point in points])
        painter.restore()

    def _selected_count(self) -> int:
        try:
            return len(self.selectionModel().selectedRows(0))
        except Exception:
            return 0

    def _make_urls_from_selection(self):
        urls = []
        try:
            model = self.model()
            rows = self.selectionModel().selectedRows(0)
            seen = set()
            for idx in rows:
                p = model.filePath(idx)
                if p and p not in seen:
                    seen.add(p)
                    urls.append(QUrl.fromLocalFile(p))
        except Exception:
            pass
        return urls

    def _start_multi_drag(self):
        urls = self._make_urls_from_selection()
        if not urls:
            return
        md = QMimeData()
        try:
            parts = []
            for u in urls:
                try:
                    parts.append(u.toString(QUrl.FullyEncoded))
                except Exception:
                    parts.append(u.toString())
            md.setData("text/uri-list", ("\r\n".join(parts) + "\r\n").encode("utf-8"))
        except Exception:
            pass
        md.setUrls(urls)

        drag = QDrag(self)
        drag.setMimeData(md)
        drag.exec(Qt.MoveAction | Qt.CopyAction, Qt.MoveAction)

    def _drag_threshold(self) -> int:
        """
        Return platform drag threshold using style hints when available.
        Compatible with Qt 6 where static startDragDistance() is not exposed on QGuiApplication.
        """
        try:
            hints = QGuiApplication.styleHints()
            if hints is not None:
                getter = getattr(hints, "startDragDistance", None)
                if callable(getter):
                    return int(getter())
                val = getattr(hints, "startDragDistance", 0)
                if isinstance(val, int) and val > 0:
                    return val
        except Exception:
            pass
        try:
            from PySide6.QtWidgets import QApplication
            return int(QApplication.startDragDistance())
        except Exception:
            pass
        return 10

    def _event_point(self, event) -> QPoint:
        """Return mouse point for Qt versions exposing either .position() or .pos()."""
        try:
            return event.position().toPoint()
        except Exception:
            try:
                return event.pos()
            except Exception:
                return QPoint()

    def _row_index_at(self, pos: QPoint) -> QModelIndex:
        """
        Return a model index for the row under 'pos' forced to column 0,
        so row-based selection is consistent no matter which column is clicked.
        """
        try:
            idx = self.indexAt(pos)
            if idx.isValid():
                try:
                    return idx.siblingAtColumn(0)
                except Exception:
                    return self.model().index(idx.row(), 0, idx.parent())
        except Exception:
            pass
        return QModelIndex()

    def mousePressEvent(self, event):
        pos = self._event_point(event)
        if event.button() == Qt.LeftButton:
            ctrl = bool(event.modifiers() & Qt.ControlModifier)
            shift = bool(event.modifiers() & Qt.ShiftModifier)

            pressed_idx = self._row_index_at(pos)
            self._md_press_index = pressed_idx

            if shift:
                try:
                    sm = self.selectionModel()
                except Exception:
                    sm = None
                if sm is not None:
                    anchor = self._sel_anchor_index if self._sel_anchor_index.isValid() else sm.currentIndex()
                    if not (anchor and anchor.isValid()):
                        anchor = pressed_idx
                        self._sel_anchor_index = pressed_idx
                    try:
                        sm.setCurrentIndex(anchor, QItemSelectionModel.NoUpdate)
                    except Exception:
                        pass
                super().mousePressEvent(event)
                return

            if not ctrl and not shift:
                if pressed_idx.isValid():
                    self._sel_anchor_index = pressed_idx
                    try:
                        sm = self.selectionModel()
                        if sm is not None:
                            sm.setCurrentIndex(pressed_idx, QItemSelectionModel.NoUpdate)
                    except Exception:
                        pass

                if self._selected_count() > 1:
                    self._md_pressed = True
                    self._md_drag_started = False
                    self._md_maybe_clear = True
                    self._md_press_pos = pos
                    self.setFocus(Qt.MouseFocusReason)
                    event.accept()
                    return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._md_pressed and (event.buttons() & Qt.LeftButton):
            pos = self._event_point(event)
            if (pos - self._md_press_pos).manhattanLength() >= self._drag_threshold():
                self._md_maybe_clear = False
                self._md_drag_started = True
                self._md_pressed = False
                self._start_multi_drag()
                event.accept()
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._md_pressed and event.button() == Qt.LeftButton:
            if self._md_maybe_clear and not self._md_drag_started:
                try:
                    sm = self.selectionModel()
                except Exception:
                    sm = None
                if sm is not None:
                    sm.clearSelection()
                if self._md_press_index.isValid():
                    try:
                        self.setCurrentIndex(self._md_press_index)
                    except Exception:
                        pass
                    self._sel_anchor_index = self._md_press_index
                    self.clicked.emit(self._md_press_index)
                else:
                    self.setCurrentIndex(QModelIndex())

                event.accept()
                self._md_pressed = False
                return
        self._md_pressed = False
        super().mouseReleaseEvent(event)

