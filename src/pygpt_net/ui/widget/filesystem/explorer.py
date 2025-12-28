#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.12.27 17:00:00                  #
# ================================================== #

import datetime
import os
import shutil
import struct
import sys
from typing import Union

from PySide6.QtCore import Qt, QModelIndex, QDir, QObject, QEvent, QUrl, QPoint, QMimeData, QTimer, QRect, QItemSelectionModel
from PySide6.QtGui import QAction, QIcon, QCursor, QResizeEvent, QGuiApplication, QKeySequence, QShortcut, QClipboard, QDrag
from PySide6.QtWidgets import QTreeView, QMenu, QWidget, QVBoxLayout, QFileSystemModel, QLabel, QHBoxLayout, \
    QPushButton, QSizePolicy, QAbstractItemView, QFrame

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.ui.widget.element.button import ContextMenuButton
from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.utils import trans


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
                else:
                    self.setCurrentIndex(QModelIndex())

                event.accept()
                self._md_pressed = False
                return
        self._md_pressed = False
        super().mouseReleaseEvent(event)


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
                    dest_paths = self.explorer._move_paths(paths, target_dir)
                else:
                    try:
                        self.explorer.window.controller.files.upload_paths(paths, target_dir)
                        dest_paths = [os.path.join(target_dir, os.path.basename(p.rstrip(os.sep))) for p in paths]
                    except Exception:
                        dest_paths = self.explorer._copy_paths(paths, target_dir)
                if os.path.isdir(target_dir):
                    self.explorer._expand_dir(target_dir, center=False)
                if dest_paths:
                    self.explorer._reveal_paths(dest_paths, select_first=True)
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


class FileExplorer(QWidget):
    def __init__(self, window, directory, index_data):
        """
        File explorer widget

        :param window: Window instance
        :param directory: directory to explore
        :param index_data: index data
        """
        super().__init__()

        self.window = window
        self.owner = None
        self.index_data = index_data
        self.directory = directory
        self.model = IndexedFileSystemModel(self.window, self.index_data)
        self.model.setRootPath(self.directory)
        self.model.setFilter(self.model.filter() | QDir.Hidden)
        self.treeView = MultiDragTreeView()
        self.treeView.setModel(self.model)
        self.treeView.setRootIndex(self.model.index(self.directory))
        self.treeView.setUniformRowHeights(True)
        self.setProperty('class', 'file-explorer')

        # Multi-selection support via Ctrl/Shift and row-based selection
        try:
            self.treeView.setSelectionMode(QAbstractItemView.ExtendedSelection)
            self.treeView.setSelectionBehavior(QAbstractItemView.SelectRows)
        except Exception:
            pass

        header = QHBoxLayout()

        self.btn_open = QPushButton(trans('action.open'))
        self.btn_open.setMaximumHeight(40)
        self.btn_open.clicked.connect(
                lambda: self.action_open(self.directory)
        )
        self.btn_open.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        self.btn_upload = QPushButton(trans('files.local.upload'))
        self.btn_upload.setMaximumHeight(40)
        self.btn_upload.clicked.connect(self.window.controller.files.upload_local)
        self.btn_upload.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        self.btn_idx = ContextMenuButton(trans('idx.btn.index_all'), self)
        self.btn_idx.action = self.idx_context_menu
        self.btn_idx.setMaximumHeight(40)
        self.btn_idx.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        self.btn_clear = ContextMenuButton(trans('idx.btn.clear'), self)
        self.btn_clear.action = self.clear_context_menu
        self.btn_clear.setMaximumHeight(40)
        self.btn_clear.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        self.btn_tool = QPushButton(QIcon(":/icons/db.svg"), "")
        self.btn_tool.setMaximumHeight(40)
        self.btn_tool.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.btn_tool.clicked.connect(
            lambda: self.window.tools.get("indexer").toggle()
        )

        self.path_label = QLabel(self.directory)
        self.path_label.setMaximumHeight(40)
        self.path_label.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)

        header.addWidget(self.btn_open)
        header.addWidget(self.btn_upload)
        header.addStretch()
        header.addWidget(self.path_label)
        header.addStretch()

        header.addWidget(self.btn_tool)
        header.addWidget(self.btn_idx)
        header.addWidget(self.btn_clear)
        self.layout = QVBoxLayout()

        self.window.ui.nodes['tip.output.tab.files'] = HelpLabel(trans('tip.output.tab.files'), self.window)

        self.layout.addWidget(self.treeView)
        self.layout.addWidget(self.window.ui.nodes['tip.output.tab.files'])
        self.layout.addLayout(header)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        self.treeView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.treeView.customContextMenuRequested.connect(self.openContextMenu)
        self.treeView.setColumnWidth(0, int(self.width() / 2))

        self.header = self.treeView.header()
        self.header.setStretchLastSection(True)
        self.header.setContentsMargins(0, 0, 0, 0)

        # Persisted column widths across model refreshes/layout changes
        self._saved_column_widths = {}
        self._is_restoring_columns = False

        # Re-apply widths when user resizes columns or model refreshes
        try:
            self.header.sectionResized.connect(self._on_header_section_resized)
            self.model.modelAboutToBeReset.connect(self._on_model_about_to_reset)
            self.model.modelReset.connect(self._on_model_reset)
            self.model.layoutAboutToBeChanged.connect(self._on_layout_about_to_change)
            self.model.layoutChanged.connect(self._on_layout_changed)
            self.model.directoryLoaded.connect(self._on_model_directory_loaded)
        except Exception:
            pass

        self.column_proportion = 0.3
        self.adjustColumnWidths()  # initial layout

        self.header.setStyleSheet("""
           QHeaderView::section {
               text-align: center;
               vertical-align: middle;
           }
       """)
        self.tab = None
        self.installEventFilter(self)
        try:
            self.treeView.viewport().installEventFilter(self)
        except Exception:
            pass

        self._icons = {
            'open': QIcon(":/icons/view.svg"),
            'open_dir': QIcon(":/icons/folder_filled.svg"),
            'download': QIcon(":/icons/download.svg"),
            'rename': QIcon(":/icons/edit.svg"),
            'duplicate': QIcon(":/icons/stack.svg"),
            'touch': QIcon(":/icons/add.svg"),
            'mkdir': QIcon(":/icons/add_folder.svg"),
            'refresh': QIcon(":/icons/reload.svg"),
            'upload': QIcon(":/icons/upload.svg"),
            'delete': QIcon(":/icons/delete.svg"),
            'attachment': QIcon(":/icons/attachment.svg"),
            'copy': QIcon(":/icons/copy.svg"),
            'cut': QIcon(":/icons/cut.svg"),
            'paste': QIcon(":/icons/paste.svg"),
            'read': QIcon(":/icons/view.svg"),
            'db': QIcon(":/icons/db.svg"),
            'pack': QIcon(":/icons/upload.svg"),
            'unpack': QIcon(":/icons/download.svg"),
        }

        try:
            self.treeView.setDragEnabled(True)
            self.treeView.setAcceptDrops(True)
            self.treeView.setDropIndicatorShown(False)
            self.treeView.setDragDropMode(QAbstractItemView.DragDrop)
            self.treeView.setDefaultDropAction(Qt.MoveAction)
            self.treeView.setAutoScroll(False)
        except Exception:
            pass

        self._cb_paths = []
        self._cb_mode = None

        try:
            sc_copy = QShortcut(QKeySequence.Copy, self.treeView, context=Qt.WidgetWithChildrenShortcut)
            sc_copy.activated.connect(self.action_copy_selection)
            sc_cut = QShortcut(QKeySequence.Cut, self.treeView, context=Qt.WidgetWithChildrenShortcut)
            sc_cut.activated.connect(self.action_cut_selection)
            sc_paste = QShortcut(QKeySequence.Paste, self.treeView, context=Qt.WidgetWithChildrenShortcut)
            sc_paste.activated.connect(self.action_paste_into_current)
        except Exception:
            pass

        self._dnd_handler = ExplorerDropHandler(self)

    def _on_header_section_resized(self, logical_index: int, old: int, new: int):
        """Track user-driven column width changes."""
        if self._is_restoring_columns:
            return
        try:
            self._saved_column_widths[logical_index] = int(new)
        except Exception:
            pass

    def _on_model_about_to_reset(self):
        """Save current widths before model reset."""
        self._save_current_column_widths()

    def _on_model_reset(self):
        """Restore widths right after model reset."""
        self._schedule_restore_columns()

    def _on_layout_about_to_change(self):
        """Save widths before layout changes."""
        self._save_current_column_widths()

    def _on_layout_changed(self):
        """Restore widths after layout changes."""
        self._schedule_restore_columns()

    def _on_model_directory_loaded(self, path: str):
        """Ensure widths are re-applied when a directory finishes loading."""
        self._schedule_restore_columns()

    def _save_current_column_widths(self):
        """Persist current column widths."""
        try:
            count = self.model.columnCount()
            for i in range(count):
                w = self.treeView.columnWidth(i)
                if w > 0:
                    self._saved_column_widths[i] = int(w)
        except Exception:
            pass

    def _restore_columns_now(self):
        """Best-effort restoration of column widths with proportional fallback."""
        try:
            self._is_restoring_columns = True
            col_count = self.model.columnCount()
            self.adjustColumnWidths()  # apply proportional baseline
            if self._saved_column_widths:
                for i, w in list(self._saved_column_widths.items()):
                    if 0 <= i < col_count and w > 0:
                        try:
                            self.treeView.setColumnWidth(i, int(w))
                        except Exception:
                            pass
            try:
                self.header.setStretchLastSection(True)
            except Exception:
                pass
        finally:
            self._is_restoring_columns = False

    def _schedule_restore_columns(self, delay_ms: int = 0):
        """Defer restoration to allow view/header to settle after reset."""
        QTimer.singleShot(max(0, delay_ms), self._restore_columns_now)

    def eventFilter(self, source, event):
        """
        Focus event filter

        :param source: source
        :param event: event
        """
        if event.type() == event.Type.FocusIn:
            if self.tab is not None:
                col_idx = self.tab.column_idx
                self.window.controller.ui.tabs.on_column_focus(col_idx)
        return super().eventFilter(source, event)

    def set_tab(self, tab: Tab):
        """
        Set tab

        :param tab: Tab
        """
        self.tab = tab

    def setOwner(self, owner: Tab):
        """
        Set tab parent (owner)

        :param owner: parent tab instance
        """
        self.owner = owner

    def getOwner(self) -> Tab:
        """
        Get tab parent (owner)

        :return: parent tab instance
        """
        return self.owner

    def update_view(self):
        """Update explorer view keeping column widths intact."""
        self._save_current_column_widths()
        self.model.beginResetModel()
        self.model.setRootPath(self.directory)
        self.model.endResetModel()
        self.treeView.setRootIndex(self.model.index(self.directory))
        self._schedule_restore_columns()

    def idx_context_menu(self, parent, pos):
        """
        Index all btn context menu

        :param parent: parent widget
        :param pos: mouse  position
        """
        menu = QMenu(self)
        idx_list = self.window.core.config.get('llama.idx.list')
        if len(idx_list) > 0:
            for idx in idx_list:
                id = idx['id']
                name = f"{idx['name']} ({idx['id']})"
                action = menu.addAction(f"IDX: {name}")
                action.triggered.connect(
                    lambda checked=False,
                           id=id: self.window.controller.idx.indexer.index_all_files(id)
                )
        menu.exec(parent.mapToGlobal(pos))

    def clear_context_menu(self, parent, pos):
        """
        Clear btn context menu

        :param parent: parent widget
        :param pos: mouse position
        """
        menu = QMenu(self)
        idx_list = self.window.core.config.get('llama.idx.list')
        if len(idx_list) > 0:
            for idx in idx_list:
                id = idx['id']
                name = f"{idx['name']} ({idx['id']})"
                action = menu.addAction(f"IDX: {name}")
                action.triggered.connect(
                    lambda checked=False,
                           id=id: self.window.controller.idx.indexer.clear(id)
                )
        menu.exec(parent.mapToGlobal(pos))

    def adjustColumnWidths(self):
        """Adjust column widths and persist them."""
        total_width = self.treeView.width()
        col_count = self.model.columnCount()
        first_column_width = int(total_width * self.column_proportion)
        self.treeView.setColumnWidth(0, first_column_width)
        if col_count > 1:
            remaining = max(total_width - first_column_width, 0)
            per_col = remaining // (col_count - 1) if col_count > 1 else 0
            for column in range(1, col_count):
                self.treeView.setColumnWidth(column, per_col)
        self._save_current_column_widths()

    def resizeEvent(self, event: QResizeEvent):
        """
        Resize event

        :param event: Event object
        """
        super().resizeEvent(event)
        if event.oldSize().width() != event.size().width():
            self.adjustColumnWidths()

    def openContextMenu(self, position):
        """
        Open context menu

        :param position: mouse position
        """
        paths = self._selected_paths()
        if paths:
            first_path = paths[0]
            multiple = len(paths) > 1
            target_multi = paths if multiple else first_path
            actions = {}
            preview_actions = []
            use_actions = []

            can_preview = False
            try:
                can_preview = self.window.core.filesystem.actions.has_preview(target_multi)
            except Exception:
                try:
                    can_preview = self.window.core.filesystem.actions.has_preview(first_path)
                except Exception:
                    can_preview = False

            if can_preview:
                try:
                    preview_actions = self.window.core.filesystem.actions.get_preview(self, target_multi)
                except Exception:
                    try:
                        preview_actions = self.window.core.filesystem.actions.get_preview(self, first_path)
                    except Exception:
                        preview_actions = []

            parent = self._parent_for_selection(paths)

            actions['open'] = QAction(self._icons['open'], trans('action.open'), self)
            actions['open'].triggered.connect(lambda: self.action_open(target_multi))

            actions['open_dir'] = QAction(self._icons['open_dir'], trans('action.open_dir'), self)
            actions['open_dir'].triggered.connect(lambda: self.action_open_dir(target_multi))

            actions['download'] = QAction(self._icons['download'], trans('action.download'), self)
            actions['download'].triggered.connect(lambda: self.window.controller.files.download_local(target_multi))

            actions['rename'] = QAction(self._icons['rename'], trans('action.rename'), self)
            actions['rename'].triggered.connect(lambda: self.action_rename(target_multi))

            actions['duplicate'] = QAction(self._icons['duplicate'], trans('action.duplicate'), self)
            actions['duplicate'].triggered.connect(lambda: self.window.controller.files.duplicate_local(target_multi, ""))

            actions['touch'] = QAction(self._icons['touch'], trans('action.touch'), self)
            actions['touch'].triggered.connect(lambda: self.window.controller.files.touch_file(parent))

            actions['mkdir'] = QAction(self._icons['mkdir'], trans('action.mkdir'), self)
            actions['mkdir'].triggered.connect(lambda: self.action_make_dir(parent))

            actions['refresh'] = QAction(self._icons['refresh'], trans('action.refresh'), self)
            actions['refresh'].triggered.connect(lambda: self.window.controller.files.update_explorer())

            actions['upload'] = QAction(self._icons['upload'], trans('action.upload'), self)
            actions['upload'].triggered.connect(lambda: self.window.controller.files.upload_local(parent))

            actions['delete'] = QAction(self._icons['delete'], trans('action.delete'), self)
            actions['delete'].triggered.connect(lambda: self.action_delete(target_multi))

            actions['copy'] = QAction(self._icons['copy'], trans('action.copy'), self)
            actions['copy'].triggered.connect(self.action_copy_selection)
            actions['cut'] = QAction(self._icons['cut'], trans('action.cut'), self)
            actions['cut'].triggered.connect(self.action_cut_selection)
            actions['paste'] = QAction(self._icons['paste'], trans('action.paste'), self)
            actions['paste'].triggered.connect(lambda: self.action_paste_into(parent))
            actions['paste'].setEnabled(self._can_paste())

            # Pack / Unpack availability
            try:
                can_unpack_all = all(
                    os.path.isfile(p) and self.window.core.filesystem.packer.can_unpack(p)
                    for p in paths
                )
            except Exception:
                can_unpack_all = False

            # Build menu
            menu = QMenu(self)
            if preview_actions:
                for action in preview_actions:
                    menu.addAction(action)
            menu.addAction(actions['open'])
            menu.addAction(actions['open_dir'])

            use_menu = QMenu(trans('action.use'), self)

            files_only = all(os.path.isfile(p) for p in paths)
            if files_only:
                actions['use_attachment'] = QAction(self._icons['attachment'], trans('action.use.attachment'), self)
                actions['use_attachment'].triggered.connect(
                    lambda: self.window.controller.files.use_attachment(target_multi)
                )
                use_menu.addAction(actions['use_attachment'])

            if self.window.core.filesystem.actions.has_use(first_path):
                use_actions = self.window.core.filesystem.actions.get_use(self, first_path)

            if use_actions:
                for action in use_actions:
                    use_menu.addAction(action)

            actions['use_copy_work_path'] = QAction(self._icons['copy'], trans('action.use.copy_work_path'), self)
            actions['use_copy_work_path'].triggered.connect(
                lambda: self.window.controller.files.copy_work_path(target_multi)
            )

            actions['use_copy_sys_path'] = QAction(self._icons['copy'], trans('action.use.copy_sys_path'), self)
            actions['use_copy_sys_path'].triggered.connect(
                lambda: self.window.controller.files.copy_sys_path(target_multi)
            )

            actions['use_read_cmd'] = QAction(self._icons['read'], trans('action.use.read_cmd'), self)
            actions['use_read_cmd'].triggered.connect(
                lambda: self.window.controller.files.make_read_cmd(target_multi)
            )

            use_menu.addAction(actions['use_copy_work_path'])
            use_menu.addAction(actions['use_copy_sys_path'])
            use_menu.addAction(actions['use_read_cmd'])
            menu.addMenu(use_menu)

            allowed_any = any(self.window.core.idx.indexing.is_allowed(p) for p in paths)
            if allowed_any:
                idx_menu = QMenu(trans('action.idx'), self)
                idx_list = self.window.core.config.get('llama.idx.list')
                if len(idx_list) > 0:
                    for idx in idx_list:
                        id = idx['id']
                        name = f"{idx['name']} ({idx['id']})"
                        action = QAction(self._icons['db'], f"IDX: {name}", self)
                        action.triggered.connect(lambda checked=False, id=id, target=target_multi: self.action_idx(target, id))
                        idx_menu.addAction(action)

                remove_idx_set = set()
                for p in paths:
                    status = self.model.get_index_status(p)
                    if status.get('indexed'):
                        for ix in status.get('indexed_in', []):
                            remove_idx_set.add(ix)

                if len(remove_idx_set) > 0:
                    idx_menu.addSeparator()
                    for ix in sorted(remove_idx_set):
                        action = QAction(self._icons['delete'], trans("action.idx.remove") + ": " + ix, self)
                        action.triggered.connect(
                            lambda checked=False, ix=ix, target=target_multi: self.action_idx_remove(target, ix)
                        )
                        idx_menu.addAction(action)

                menu.addMenu(idx_menu)

            menu.addSeparator()
            menu.addAction(actions['copy'])
            menu.addAction(actions['cut'])
            menu.addAction(actions['paste'])
            menu.addSeparator()

            # Pack submenu (available for any selection)
            pack_menu = QMenu(trans("action.pack"), self)
            a_zip = QAction(self._icons['pack'], "ZIP (.zip)", self)
            a_zip.triggered.connect(lambda: self.action_pack(target_multi, 'zip'))
            a_tgz = QAction(self._icons['pack'], "Tar GZip (.tar.gz)", self)
            a_tgz.triggered.connect(lambda: self.action_pack(target_multi, 'tar.gz'))
            pack_menu.addAction(a_zip)
            pack_menu.addAction(a_tgz)
            menu.addMenu(pack_menu)

            # Unpack (only when all selected are supported archives)
            if can_unpack_all:
                a_unpack = QAction(self._icons['unpack'], trans("action.unpack"), self)
                a_unpack.triggered.connect(lambda: self.action_unpack(target_multi))
                menu.addAction(a_unpack)

            menu.addSeparator()
            menu.addAction(actions['download'])
            menu.addAction(actions['touch'])
            menu.addAction(actions['mkdir'])
            menu.addAction(actions['upload'])
            menu.addAction(actions['refresh'])

            menu.addAction(actions['rename'])
            menu.addAction(actions['duplicate'])
            menu.addAction(actions['delete'])

            menu.exec(QCursor.pos())
        else:
            actions = {}

            actions['touch'] = QAction(self._icons['touch'], trans('action.touch'), self)
            actions['touch'].triggered.connect(
                lambda: self.window.controller.files.touch_file(self.directory),
            )

            actions['open_dir'] = QAction(self._icons['open_dir'], trans('action.open_dir'), self)
            actions['open_dir'].triggered.connect(
                lambda: self.action_open_dir(self.directory),
            )

            actions['mkdir'] = QAction(self._icons['mkdir'], trans('action.mkdir'), self)
            actions['mkdir'].triggered.connect(
                lambda: self.action_make_dir(self.directory),
            )

            actions['upload'] = QAction(self._icons['upload'], trans('action.upload'), self)
            actions['upload'].triggered.connect(
                lambda: self.window.controller.files.upload_local(),
            )

            actions['paste'] = QAction(self._icons['paste'], trans('action.paste'), self)
            actions['paste'].triggered.connect(lambda: self.action_paste_into(self.directory))
            actions['paste'].setEnabled(self._can_paste())

            menu = QMenu(self)
            menu.addAction(actions['touch'])
            menu.addAction(actions['open_dir'])
            menu.addAction(actions['mkdir'])
            menu.addAction(actions['upload'])
            menu.addAction(actions['paste'])
            menu.exec(QCursor.pos())

    def action_open(self, path: Union[str, list]):
        """
        Open action handler

        :param path: path to open (str or list of str)
        """
        self.window.controller.files.open(path)

    def action_idx(self, path: Union[str, list], idx: str):
        """
        Index file or dir handler

        :param path: path to open (str or list of str)
        :param idx: index ID to use (name)
        """
        self.window.controller.idx.indexer.index_file(path, idx)

    def action_idx_remove(self, path: Union[str, list], idx: str):
        """
        Remove file or dir from index handler

        :param path: path to open (str or list of str)
        :param idx: index ID to use (name)
        """
        self.window.controller.idx.indexer.index_file_remove(path, idx)

    def action_open_dir(self, path: Union[str, list]):
        """
        Open in directory action handler

        :param path: path to open (str or list of str)
        """
        self.window.controller.files.open_dir(path, True)

    def action_make_dir(self, path: str = None):
        """
        Make directory action handler

        :param path: parent path
        """
        self.window.controller.files.make_dir_dialog(path)

    def action_rename(self, path: Union[str, list]):
        """
        Rename action handler

        :param path: path to rename (str or list of str)
        """
        self.window.controller.files.rename(path)

    def action_delete(self, path: Union[str, list]):
        """
        Delete action handler

        :param path: path to delete (str or list of str)
        """
        self.window.controller.files.delete(path)

    def action_pack(self, path: Union[str, list], fmt: str):
        """
        Pack selected items into an archive.

        :param path: path or list of paths to include
        :param fmt: 'zip' or 'tar.gz'
        """
        paths = path if isinstance(path, list) else [path]
        try:
            dst = self.window.core.filesystem.packer.pack_paths(paths, fmt)
        except Exception as e:
            try:
                self.window.core.debug.log(e)
            except Exception:
                pass
            dst = None

        try:
            self.window.controller.files.update_explorer()
        except Exception:
            self.update_view()

        if dst and os.path.exists(dst):
            self._reveal_paths([dst], select_first=True)

    def action_unpack(self, path: Union[str, list]):
        """
        Unpack selected archives to sibling directories named after archives.

        :param path: path or list of paths to archives
        """
        paths = path if isinstance(path, list) else [path]
        created = []
        for p in paths:
            try:
                if self.window.core.filesystem.packer.can_unpack(p):
                    out_dir = self.window.core.filesystem.packer.unpack_to_sibling_dir(p)
                    if out_dir:
                        created.append(out_dir)
            except Exception as e:
                try:
                    self.window.core.debug.log(e)
                except Exception:
                    pass

        try:
            self.window.controller.files.update_explorer()
        except Exception:
            self.update_view()

        if created:
            self._reveal_paths(created, select_first=True)

    # ===== Copy / Cut / Paste API =====

    def _selected_paths(self) -> list:
        """Return unique selected file system paths from first column."""
        paths = []
        try:
            indexes = self.treeView.selectionModel().selectedRows(0)
        except Exception:
            indexes = []
        for idx in indexes:
            try:
                p = self.model.filePath(idx)
                if p and p not in paths:
                    paths.append(p)
            except Exception:
                continue
        return paths

    def _parent_for_selection(self, paths: list) -> str:
        """
        Determine a sensible parent directory for operations like paste/touch/mkdir when selection may contain many items.
        - For single selection: item if it is a directory; otherwise its parent directory.
        - For multi selection: common parent directory of all selected items; falls back to explorer root if not determinable.
        """
        if not paths:
            return self.directory
        if len(paths) == 1:
            p = paths[0]
            return p if os.path.isdir(p) else os.path.dirname(p)
        try:
            parents = [p if os.path.isdir(p) else os.path.dirname(p) for p in paths]
            cp = os.path.commonpath([os.path.abspath(x) for x in parents])
            return cp if os.path.isdir(cp) else os.path.dirname(cp)
        except Exception:
            return self.directory

    def action_copy_selection(self):
        """Copy currently selected files/dirs to system clipboard and internal buffer."""
        paths = self._selected_paths()
        if not paths:
            return
        self._set_clipboard_files(paths, mode='copy')

    def action_cut_selection(self):
        """Cut currently selected files/dirs to system clipboard and internal buffer (virtual until paste)."""
        paths = self._selected_paths()
        if not paths:
            return
        self._set_clipboard_files(paths, mode='cut')

    def action_paste_into(self, target_dir: str):
        """Paste clipboard files into given directory and expand/scroll to them."""
        if not target_dir:
            target_dir = self.directory
        paths, mode = self._get_clipboard_files_and_mode()
        if not paths:
            return

        dest_paths = []
        try:
            if mode == 'cut':
                dest_paths = self._move_paths(paths, target_dir)
            else:
                dest_paths = self._copy_paths(paths, target_dir)
        finally:
            self._cb_paths = []
            self._cb_mode = None

        if os.path.isdir(target_dir):
            self._expand_dir(target_dir, center=False)

        try:
            self.window.controller.files.update_explorer()
        except Exception:
            self.update_view()

        if dest_paths:
            self._reveal_paths(dest_paths, select_first=True)

    def action_paste_into_current(self):
        """Paste into directory derived from current selection or root when none."""
        try:
            sel = self.treeView.selectionModel()
            indexes = sel.selectedRows(0) if sel is not None else []
        except Exception:
            indexes = []
        if indexes:
            path = self.model.filePath(indexes[0])
            target = path if os.path.isdir(path) else os.path.dirname(path)
        else:
            target = self.directory
        self.action_paste_into(target)

    def _can_paste(self) -> bool:
        """Check if there are files to paste either from system clipboard or internal."""
        try:
            md = QGuiApplication.clipboard().mimeData()
            if md and md.hasUrls():
                for url in md.urls():
                    if url.isLocalFile():
                        return True
        except Exception:
            pass
        return bool(self._cb_paths)

    # ===== Filesystem helpers =====

    def _copy_paths(self, paths: list, target_dir: str):
        """Copy each path into target_dir, directories are copied recursively. Returns list of new destinations."""
        dests = []
        if not os.path.isdir(target_dir):
            os.makedirs(target_dir, exist_ok=True)
        for src in paths:
            try:
                if not os.path.exists(src):
                    continue
                base_name = os.path.basename(src.rstrip(os.sep))
                dst = self._unique_dest(target_dir, base_name)
                if os.path.isdir(src):
                    shutil.copytree(src, dst, copy_function=shutil.copy2)
                else:
                    shutil.copy2(src, dst)
                dests.append(dst)
            except Exception as e:
                try:
                    self.window.core.debug.log(e)
                except Exception:
                    pass
        return dests

    def _move_paths(self, paths: list, target_dir: str):
        """Move each path into target_dir. Skips invalid moves (into itself). Returns list of new destinations."""
        dests = []
        if not os.path.isdir(target_dir):
            os.makedirs(target_dir, exist_ok=True)
        for src in paths:
            try:
                if not os.path.exists(src):
                    continue
                if os.path.isdir(src):
                    try:
                        sp = os.path.abspath(src)
                        tp = os.path.abspath(target_dir)
                        if os.path.commonpath([sp]) == os.path.commonpath([sp, tp]):
                            continue
                    except Exception:
                        pass
                base_name = os.path.basename(src.rstrip(os.sep))
                dst = os.path.join(target_dir, base_name)
                if os.path.abspath(dst) == os.path.abspath(src):
                    continue
                if os.path.exists(dst):
                    dst = self._unique_dest(target_dir, base_name)
                shutil.move(src, dst)
                dests.append(dst)
            except Exception as e:
                try:
                    self.window.core.debug.log(e)
                except Exception:
                    pass
        return dests

    def _unique_dest(self, target_dir: str, name: str) -> str:
        """Return a unique destination path in target_dir based on name."""
        root, ext = os.path.splitext(name)
        candidate = os.path.join(target_dir, name)
        if not os.path.exists(candidate):
            return candidate
        i = 1
        while True:
            suffix = " - Copy" if i == 1 else f" - Copy ({i})"
            cand = os.path.join(target_dir, f"{root}{suffix}{ext}")
            if not os.path.exists(cand):
                return cand
            i += 1

    def _expand_dir(self, path: str, center: bool = False):
        """Expand and optionally center on a directory index."""
        try:
            idx = self.model.index(path)
            if idx.isValid():
                if not self.treeView.isExpanded(idx):
                    self.treeView.expand(idx)
                if center:
                    self.treeView.scrollTo(idx, QTreeView.PositionAtCenter)
                else:
                    self.treeView.scrollTo(idx, QTreeView.EnsureVisible)
        except Exception:
            pass

    def _reveal_paths(self, paths: list, select_first: bool = True):
        """
        Reveal and optionally select the given paths in the view.
        Tries a few times with small delays to wait for model refresh.
        """
        def do_reveal(attempts_left=6):
            try:
                sm = self.treeView.selectionModel()
            except Exception:
                sm = None
            first_index = None
            for p in paths:
                dir_path = p if os.path.isdir(p) else os.path.dirname(p)
                self._expand_dir(dir_path, center=False)
                idx = self.model.index(p)
                if idx.isValid():
                    if first_index is None:
                        first_index = idx
                    self.treeView.scrollTo(idx, QTreeView.PositionAtCenter)
            if first_index is not None and sm is not None and select_first:
                try:
                    sm.clearSelection()
                    self.treeView.setCurrentIndex(first_index)
                    self.treeView.scrollTo(first_index, QTreeView.PositionAtCenter)
                except Exception:
                    pass
            elif attempts_left > 0:
                QTimer.singleShot(150, lambda: do_reveal(attempts_left - 1))

        QTimer.singleShot(100, do_reveal)

    # ===== Clipboard integration (OS + internal) =====

    def _urls_to_text_uri_list(self, urls):
        """
        Build RFC compliant text/uri-list payload (CRLF separated).
        """
        parts = []
        for u in urls:
            try:
                parts.append(u.toString(QUrl.FullyEncoded))
            except Exception:
                parts.append(u.toString())
        data = ("\r\n".join(parts) + "\r\n").encode("utf-8")
        return data

    def _build_gnome_payload(self, urls, verb: str):
        """
        Build x-special/gnome-copied-files payload:
        copy|cut + newline + list of file:// URLs + trailing newline.
        """
        lines = [verb]
        for u in urls:
            try:
                lines.append(u.toString(QUrl.FullyEncoded))
            except Exception:
                lines.append(u.toString())
        return ("\n".join(lines) + "\n").encode("utf-8")

    def _set_clipboard_files(self, paths: list, mode: str = 'copy'):
        """
        Set system clipboard with file urls and cut/copy semantics; keep internal buffer.
        Designed to work across Linux (GNOME/KDE), Windows, and macOS as far as OS allows.
        """
        self._cb_paths = [os.path.abspath(p) for p in paths if p]
        self._cb_mode = 'cut' if mode == 'cut' else 'copy'

        try:
            urls = [QUrl.fromLocalFile(p) for p in self._cb_paths]
            md = QMimeData()

            md.setData("text/uri-list", self._urls_to_text_uri_list(urls))
            md.setUrls(urls)

            try:
                md.setData("application/x-kde-cutselection", b"1" if self._cb_mode == 'cut' else b"0")
            except Exception:
                pass

            try:
                verb = "cut" if self._cb_mode == 'cut' else "copy"
                payload = self._build_gnome_payload(urls, verb)
                md.setData("x-special/gnome-copied-files", payload)
                md.setData("x-special/nautilus-clipboard", payload)
            except Exception:
                pass

            try:
                effect = 2 if self._cb_mode == 'cut' else 1
                data = struct.pack("<I", effect)
                md.setData('application/x-qt-windows-mime;value="Preferred DropEffect"', data)
                md.setData("application/x-qt-windows-mime;value=Preferred DropEffect", data)
                md.setData("Preferred DropEffect", data)
            except Exception:
                pass

            cb = QGuiApplication.clipboard()
            cb.setMimeData(md, QClipboard.Clipboard)
            try:
                cb.setMimeData(md, QClipboard.Selection)
            except Exception:
                pass
        except Exception as e:
            try:
                self.window.core.debug.log(e)
            except Exception:
                pass

    def _get_clipboard_files_and_mode(self):
        """
        Read file urls and cut/copy mode from system clipboard.
        Returns tuple (paths, mode) where mode in {'copy','cut'}.
        Falls back to internal buffer if system clipboard does not provide file urls.
        """
        paths = []
        mode = 'copy'
        try:
            md = QGuiApplication.clipboard().mimeData()
        except Exception:
            md = None

        try:
            if md:
                urls = []
                if md.hasUrls():
                    urls = md.urls()
                elif md.hasFormat("text/uri-list"):
                    try:
                        raw = bytes(md.data("text/uri-list")).decode("utf-8", "ignore")
                        for line in raw.splitlines():
                            line = line.strip()
                            if line and not line.startswith("#"):
                                u = QUrl(line)
                                if u.isLocalFile():
                                    urls.append(u)
                    except Exception:
                        pass

                for u in urls:
                    try:
                        if u.isLocalFile():
                            lf = u.toLocalFile()
                            if lf:
                                paths.append(lf)
                    except Exception:
                        continue

                try:
                    if md.hasFormat("application/x-kde-cutselection"):
                        data = bytes(md.data("application/x-kde-cutselection"))
                        if data and (data.startswith(b'1') or data == b"\x01"):
                            mode = 'cut'
                except Exception:
                    pass
                try:
                    if md.hasFormat("x-special/gnome-copied-files"):
                        data = bytes(md.data("x-special/gnome-copied-files")).decode("utf-8", "ignore")
                        if data.splitlines()[0].strip().lower().startswith("cut"):
                            mode = 'cut'
                    elif md.hasFormat("x-special/nautilus-clipboard"):
                        data = bytes(md.data("x-special/nautilus-clipboard")).decode("utf-8", "ignore")
                        if data.splitlines()[0].strip().lower().startswith("cut"):
                            mode = 'cut'
                except Exception:
                    pass
                try:
                    for key in ('application/x-qt-windows-mime;value="Preferred DropEffect"',
                                "application/x-qt-windows-mime;value=Preferred DropEffect",
                                "Preferred DropEffect"):
                        if md.hasFormat(key):
                            data = bytes(md.data(key))
                            if data and len(data) >= 4:
                                value = struct.unpack("<I", data[:4])[0]
                                if value & 2:
                                    mode = 'cut'
                                    break
                except Exception:
                    pass
        except Exception:
            paths = []

        if not paths and self._cb_paths:
            paths = list(self._cb_paths)
            mode = self._cb_mode or 'copy'

        return paths, mode


class IndexedFileSystemModel(QFileSystemModel):
    def __init__(self, window, index_dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.window = window
        self.index_dict = index_dict
        self._status_cache = {}
        self.directoryLoaded.connect(self.refresh_path)
        try:
            self.setReadOnly(False)
        except Exception:
            pass

    def refresh_path(self, path):
        index = self.index(path)
        if index.isValid():
            self._status_cache.clear()
            self.dataChanged.emit(index, index)

    def columnCount(self, parent=QModelIndex()) -> int:
        """
        Return column count

        :param parent: parent
        :return: column count
        """
        return super().columnCount(parent) + 1

    def data(self, index, role=Qt.DisplayRole) -> any:
        """
        Data handler

        :param index: row index
        :param role: role
        :return: data
        """
        last_col = self.columnCount() - 1
        if index.column() == last_col:
            if role == Qt.DisplayRole:
                file_path = self.filePath(index.siblingAtColumn(0))
                status = self.get_index_status(file_path)
                if status['indexed']:
                    ts = status['last_index_at']
                    dt = datetime.datetime.fromtimestamp(ts)
                    if dt.date() == datetime.date.today():
                        ds = dt.strftime("%H:%M")
                    else:
                        ds = dt.strftime("%Y-%m-%d %H:%M")
                    content = f"{ds} ({','.join(status['indexed_in'])})"
                else:
                    content = '-'
                return content
        elif index.column() == last_col - 1:
            if role == Qt.DisplayRole:
                dt_qt = self.lastModified(index)
                ts = dt_qt.toSecsSinceEpoch()
                dt_py = datetime.datetime.fromtimestamp(ts)
                if dt_py.date() == datetime.date.today():
                    data = dt_py.strftime("%H:%M")
                else:
                    data = dt_py.strftime("%Y-%m-%d %H:%M")
                file_path = self.filePath(index.siblingAtColumn(0))
                status = self.get_index_status(file_path)
                if status['indexed']:
                    if 'last_index_at' in status and status['last_index_at'] < ts:
                        data += '*'
                return data

        return super().data(index, role)

    def get_index_status(self, file_path) -> dict:
        """
        Get index status

        :param file_path: file path
        :return: file index status
        """
        file_id = self.window.core.idx.files.get_id(file_path)
        cached = self._status_cache.get(file_id)
        if cached is not None:
            return cached
        indexed_in = []
        indexed_timestamps = {}
        last_index_at = 0
        for idx in self.index_dict:
            items = self.index_dict[idx]
            if file_id in items:
                indexed_in.append(idx)
                ts = items[file_id]['indexed_ts']
                indexed_timestamps[idx] = ts
                if ts > last_index_at:
                    last_index_at = ts
        if indexed_in:
            indexed_in.sort(key=lambda x: indexed_timestamps[x], reverse=True)
            result = {
                'indexed': True,
                'indexed_in': indexed_in,
                'last_index_at': last_index_at,
            }
        else:
            result = {'indexed': False}
        self._status_cache[file_id] = result
        return result

    def headerData(self, section, orientation, role=Qt.DisplayRole) -> str:
        """
        Prepare Header data (append Indexed column)

        :param section: Section
        :param orientation: Orientation
        :param role: Role
        :return: Header data
        """
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section == 0:  # name
                return trans('files.explorer.header.name')
            elif section == 1:  # size
                return trans('files.explorer.header.size')
            elif section == 2:  # type
                return trans('files.explorer.header.type')
            elif section == 3:  # modified
                return trans('files.explorer.header.modified')
            elif section == 4:  # indexed
                return trans('files.explorer.header.indexed')
        return super().headerData(section, orientation, role)

    def update_idx_status(self, idx_data):
        """
        Update index data status

        :param idx_data: new index data dict
        """
        self.index_dict = idx_data
        self._status_cache.clear()
        row_count = self.rowCount()
        if row_count > 0:
            top_left_index = self.index(0, 0)
            bottom_right_index = self.index(row_count - 1, self.columnCount() - 1)
            self.dataChanged.emit(top_left_index, bottom_right_index, [Qt.DisplayRole])
        path = self.rootPath()
        self.setRootPath("")
        self.setRootPath(path)
        self.layoutChanged.emit()