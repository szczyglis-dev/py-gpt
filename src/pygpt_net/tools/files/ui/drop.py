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

from PySide6.QtCore import Qt, QModelIndex, QObject, QEvent, QPoint, QTimer, QRect
from PySide6.QtWidgets import QFrame


class ExplorerDropHandler(QObject):
    """
    Drag & drop handler for FileExplorer (uploads and internal moves).
    - Accepts local file and directory URLs.
    - Target directory rules based on mouse position:
      * hovering directory (not in left gutter) -> into that directory
      * hovering a row in its left gutter       -> into parent directory (one level up)
      * between two rows                        -> into their common parent (or explorer root if top-level)
      * empty area                              -> explorer root
    - Internal drags result in move; external drags result in copy/upload.
    - Provides manual auto-scroll during drag.
    - Visuals:
      * highlight rectangle when targeting a directory row
      * horizontal indicator line snapped between rows for "between" drops
    """
    def __init__(self, explorer):
        super().__init__(explorer)
        self.explorer = explorer
        self.view = explorer.treeView

        try:
            self.view.setAcceptDrops(True)
        except Exception:
            pass
        vp = self.view.viewport()
        if vp is not None:
            try:
                vp.setAcceptDrops(True)
            except Exception:
                pass
            vp.installEventFilter(self)
        self.view.installEventFilter(self)

        self._indicator = QFrame(self.view.viewport())
        self._indicator.setObjectName("drop-indicator-line")
        self._indicator.setFrameShape(QFrame.NoFrame)
        self._indicator.setStyleSheet("#drop-indicator-line { background-color: rgba(40,120,255,0.95); }")
        self._indicator.hide()
        self._indicator_height = 2

        self._dir_highlight = QFrame(self.view.viewport())
        self._dir_highlight.setObjectName("drop-dir-highlight")
        self._dir_highlight.setFrameShape(QFrame.NoFrame)
        self._dir_highlight.setStyleSheet(
            "#drop-dir-highlight { border: 2px solid rgba(40,120,255,0.95); border-radius: 3px; "
            "background-color: rgba(40,120,255,0.10); }"
        )
        self._dir_highlight.hide()

        self._scroll_margin = 28
        self._scroll_speed_max = 12
        self._last_pos = None
        self._auto_timer = QTimer(self)
        self._auto_timer.setInterval(20)
        self._auto_timer.timeout.connect(self._on_auto_scroll)

        self._left_gutter_extra = 28

    def _mime_has_local_urls(self, md) -> bool:
        try:
            if md and md.hasUrls():
                for url in md.urls():
                    if url.isLocalFile():
                        return True
        except Exception:
            pass
        return False

    def _local_paths_from_mime(self, md) -> list:
        out = []
        try:
            if not (md and md.hasUrls()):
                return out
            for url in md.urls():
                try:
                    if url.isLocalFile():
                        p = url.toLocalFile()
                        if p:
                            out.append(p)
                except Exception:
                    continue
        except Exception:
            pass
        return out

    def _nearest_row_index(self, pos: QPoint):
        idx = self.view.indexAt(pos)
        if idx.isValid():
            return idx

        vp = self.view.viewport()
        h = vp.height()
        for d in range(1, 65):
            y_up = pos.y() - d
            if y_up >= 0:
                idx_up = self.view.indexAt(QPoint(pos.x(), y_up))
                if idx_up.isValid():
                    return idx_up
            y_dn = pos.y() + d
            if y_dn < h:
                idx_dn = self.view.indexAt(QPoint(pos.x(), y_dn))
                if idx_dn.isValid():
                    return idx_dn
        return QModelIndex()

    def _indices_above_below(self, pos: QPoint):
        vp = self.view.viewport()
        h = vp.height()
        above = QModelIndex()
        below = QModelIndex()

        for d in range(0, 80):
            y_up = pos.y() - d
            if y_up < 0:
                break
            idx_up = self.view.indexAt(QPoint(max(0, pos.x()), y_up))
            if idx_up.isValid():
                above = idx_up
                break

        for d in range(0, 80):
            y_dn = pos.y() + d
            if y_dn >= h:
                break
            idx_dn = self.view.indexAt(QPoint(max(0, pos.x()), y_dn))
            if idx_dn.isValid():
                below = idx_dn
                break

        return above, below

    def _gap_parent_index(self, pos: QPoint) -> QModelIndex:
        above, below = self._indices_above_below(pos)
        if above.isValid() and below.isValid():
            pa = above.parent()
            pb = below.parent()
            if pa == pb:
                return pa
            if pa.isValid():
                return pa
            if pb.isValid():
                return pb
        elif above.isValid():
            return above.parent()
        elif below.isValid():
            return below.parent()
        return QModelIndex()

    def _is_left_gutter(self, pos: QPoint, idx: QModelIndex) -> bool:
        if not idx.isValid():
            return False
        rect = self.view.visualRect(idx)
        return pos.x() < rect.left() + self._left_gutter_extra

    def _snap_line_y(self, pos: QPoint) -> int:
        vp = self.view.viewport()
        y = max(0, min(pos.y(), vp.height() - 1))
        idx = self._nearest_row_index(pos)
        if idx.isValid():
            rect = self.view.visualRect(idx)
            if y < rect.center().y():
                return rect.top()
            return rect.bottom()
        return y

    def _calc_context(self, pos: QPoint):
        vp = self.view.viewport()
        if vp is None:
            return {'type': 'empty'}

        idx = self.view.indexAt(pos)
        if idx.isValid():
            if self._is_left_gutter(pos, idx):
                rect = self.view.visualRect(idx)
                line_y = rect.top() if pos.y() < rect.center().y() else rect.bottom()
                return {'type': 'into_parent', 'idx': idx, 'parent_idx': idx.parent(), 'line_y': line_y}

            path = self.explorer.model.filePath(idx)
            if os.path.isdir(path):
                return {'type': 'into_dir', 'idx': idx}
            rect = self.view.visualRect(idx)
            line_y = rect.top() if pos.y() < rect.center().y() else rect.bottom()
            return {'type': 'into_parent', 'idx': idx, 'parent_idx': idx.parent(), 'line_y': line_y}

        parent_idx = self._gap_parent_index(pos)
        return {'type': 'gap_between', 'parent_idx': parent_idx, 'line_y': self._snap_line_y(pos)}

    def _update_visuals(self, ctx):
        self._indicator.hide()
        self._dir_highlight.hide()

        if not isinstance(ctx, dict):
            return

        if ctx.get('type') == 'into_dir' and ctx.get('idx', QModelIndex()).isValid():
            rect = self.view.visualRect(ctx['idx'])
            self._dir_highlight.setGeometry(QRect(0, rect.top(), self.view.viewport().width(), rect.height()))
            self._dir_highlight.show()
            return

        if ctx.get('type') in ('gap_between', 'into_parent'):
            y = ctx.get('line_y', None)
            if y is None:
                return
            self._indicator.setGeometry(QRect(0, y, self.view.viewport().width(), self._indicator_height))
            self._indicator.show()
            return

    def _on_auto_scroll(self):
        if self._last_pos is None:
            return
        vp = self.view.viewport()
        y = self._last_pos.y()
        h = vp.height()
        vbar = self.view.verticalScrollBar()
        delta = 0

        if y < self._scroll_margin:
            strength = max(0.0, (self._scroll_margin - y) / self._scroll_margin)
            delta = -max(1, int(strength * self._scroll_speed_max))
        elif y > h - self._scroll_margin:
            strength = max(0.0, (y - (h - self._scroll_margin)) / self._scroll_margin)
            delta = max(1, int(strength * self._scroll_speed_max))

        if delta != 0 and vbar is not None:
            vbar.setValue(vbar.value() + delta)

    def _target_dir_from_context(self, ctx) -> str:
        t = ctx.get('type')
        if t == 'into_dir':
            idx = ctx.get('idx', QModelIndex())
            if idx.isValid():
                path = self.explorer.model.filePath(idx)
                if os.path.isdir(path):
                    return path
        elif t in ('gap_between', 'into_parent'):
            parent_idx = ctx.get('parent_idx', QModelIndex())
            if parent_idx.isValid():
                return self.explorer.model.filePath(parent_idx)
            return self.explorer.directory
        return self.explorer.directory

    def _is_internal_drag(self, event) -> bool:
        try:
            src = event.source()
            return src is not None and (src is self.view or src is self.view.viewport())
        except Exception:
            return False

    def eventFilter(self, obj, event):
        et = event.type()

        if et == QEvent.DragEnter:
            md = getattr(event, 'mimeData', lambda: None)()
            if self._mime_has_local_urls(md):
                try:
                    if self._is_internal_drag(event):
                        event.setDropAction(Qt.MoveAction)
                    else:
                        event.setDropAction(Qt.CopyAction)
                    event.acceptProposedAction()
                except Exception:
                    event.accept()
                try:
                    self._last_pos = event.position().toPoint()
                except Exception:
                    try:
                        self._last_pos = event.pos()
                    except Exception:
                        self._last_pos = None
                self._auto_timer.start()

                pos = self._last_pos or QPoint(0, 0)
                ctx = self._calc_context(pos)
                self._update_visuals(ctx)
                return True
            return False

        if et == QEvent.DragMove:
            md = getattr(event, 'mimeData', lambda: None)()
            if self._mime_has_local_urls(md):
                try:
                    if self._is_internal_drag(event):
                        event.setDropAction(Qt.MoveAction)
                    else:
                        event.setDropAction(Qt.CopyAction)
                    event.acceptProposedAction()
                except Exception:
                    event.accept()

                try:
                    self._last_pos = event.position().toPoint()
                except Exception:
                    try:
                        self._last_pos = event.pos()
                    except Exception:
                        self._last_pos = None

                pos = self._last_pos or QPoint(0, 0)
                ctx = self._calc_context(pos)
                self._update_visuals(ctx)
                return True
            return False

        if et in (QEvent.DragLeave, QEvent.Leave):
            self._auto_timer.stop()
            self._indicator.hide()
            self._dir_highlight.hide()
            self._last_pos = None
            return False

        if et == QEvent.Drop:
            self._auto_timer.stop()
            self._indicator.hide()
            self._dir_highlight.hide()

            md = getattr(event, 'mimeData', lambda: None)()
            if not self._mime_has_local_urls(md):
                return False

            try:
                pos = event.position().toPoint()
            except Exception:
                pos = event.pos() if hasattr(event, "pos") else QPoint()

            ctx = self._calc_context(pos)
            target_dir = self._target_dir_from_context(ctx)

            paths = self._local_paths_from_mime(md)
            is_internal = self._is_internal_drag(event)

            dest_paths = []
            try:
                if is_internal:
                    dest_paths = self.explorer.clipboard.move_paths(paths, target_dir)
                else:
                    try:
                        self.explorer.tool.transfers.import_paths(paths, target_dir)
                        dest_paths = [os.path.join(target_dir, os.path.basename(p.rstrip(os.sep))) for p in paths]
                    except Exception:
                        dest_paths = self.explorer.clipboard.copy_paths(paths, target_dir)
                if os.path.isdir(target_dir):
                    self.explorer.expand_directory(target_dir, center=False)
                if dest_paths:
                    self.explorer.reveal(dest_paths, select_first=True)
            except Exception as e:
                try:
                    self.explorer.window.core.debug.log(e)
                except Exception:
                    pass

            try:
                event.setDropAction(Qt.MoveAction if is_internal else Qt.CopyAction)
                event.acceptProposedAction()
            except Exception:
                event.accept()
            return True

        return False

