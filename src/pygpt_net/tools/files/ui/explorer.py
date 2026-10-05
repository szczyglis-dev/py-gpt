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

from PySide6.QtCore import Qt, QDir, QEvent, QTimer
from PySide6.QtGui import QGuiApplication, QIcon, QResizeEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import QTreeView, QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QSizePolicy, QAbstractItemView, QSplitter, QLineEdit, QHeaderView, QStackedWidget


from pygpt_net.core.tabs.tab import Tab
from pygpt_net.utils import trans


from .preview import PreviewPanel
from .search import TreeSearch
from .tree import MultiDragTreeView
from .drop import ExplorerDropHandler
from .empty import EmptyFilesState, EmptyFilesDropPanel
from .model import IndexedFileSystemModel
from .menus import Menus
from ..core.clipboard import Clipboard
from ..core.archives import Archives

class FileExplorer(QWidget):
    def __init__(self, tool, directory, index_data):
        """
        File explorer widget

        :param tool: Files tool owning this frontend
        :param directory: directory to explore
        :param index_data: index data
        """
        super().__init__()

        self.tool = tool
        self.window = tool.window
        self.clipboard = Clipboard(self)
        self.archives = Archives(self)
        self.menus = Menus(self)
        self.owner = None
        self._closed = False
        self.index_data = index_data
        self.directory = directory
        self.model = IndexedFileSystemModel(self.window, self.index_data)
        self.model.setRootPath(self.directory)
        self.model.setFilter(self.model.filter() | QDir.Hidden)
        self.treeView = MultiDragTreeView()
        self.treeView.setModel(self.model)
        self.treeView.setRootIndex(self.model.index(self.directory))
        self.treeView.setUniformRowHeights(True)
        self.treeView.setIndentation(16)
        self.setProperty('class', 'file-explorer')

        # Multi-selection support via Ctrl/Shift and row-based selection
        try:
            self.treeView.setSelectionMode(QAbstractItemView.ExtendedSelection)
            self.treeView.setSelectionBehavior(QAbstractItemView.SelectRows)
        except Exception:
            pass

        self.header_buttons = []
        for name, icon, tooltip, callback in (
            ('filesOpenButton', 'folder_open', 'action.open',
             lambda checked=False: self.tool.paths.open(self.directory)),
            ('filesUploadButton', 'upload', 'files.local.upload.tooltip',
             lambda checked=False: self.tool.transfers.upload()),
            ('filesSwapColumnsButton', 'sync', 'files.columns.swap',
             lambda checked=False: self.toggle_columns()),
        ):
            button = QPushButton(QIcon(f':/icons/{icon}.svg'), '', self)
            button.setObjectName(name)
            button.setFixedSize(32, 32)
            button.setStyleSheet(f'QPushButton#{name} {{ padding: 4px; }}')
            button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            button.setCursor(Qt.PointingHandCursor)
            button.setFocusPolicy(Qt.NoFocus)
            button.setToolTip(trans(tooltip))
            button.clicked.connect(callback)
            self.header_buttons.append((button, tooltip))

        self.layout = QVBoxLayout()

        self.preview = PreviewPanel(self.window, self.directory, self)
        self.preview.directoryRequested.connect(self.navigate_directory)

        self.search = QLineEdit()
        self.search.setPlaceholderText(trans('files.search.placeholder'))
        self.search.setClearButtonEnabled(True)
        self.search.setAcceptDrops(False)
        self.search.addAction(QIcon(':/icons/search.svg'), QLineEdit.LeadingPosition)
        self.search_status = QLabel()
        self.searching_text = trans('files.search.searching')
        self.search_header = QWidget(self)
        search_bar = QHBoxLayout(self.search_header)
        search_bar.setContentsMargins(24, 0, 0, 0)
        search_bar.addWidget(self.search, 1)

        self.empty_files = EmptyFilesState(self.tool, self.directory, self)
        self.empty_files_wrapper = QWidget(self)
        empty_files_layout = QVBoxLayout(self.empty_files_wrapper)
        empty_files_layout.setContentsMargins(0, 0, 0, 0)
        empty_files_layout.addWidget(self.empty_files, 0, Qt.AlignCenter)

        self.files_stack = QStackedWidget(self)
        self.files_stack.addWidget(self.treeView)
        self.files_stack.addWidget(self.empty_files_wrapper)

        self.files_panel = EmptyFilesDropPanel(self, self)
        self.files_panel.setMinimumWidth(220)
        files_layout = QVBoxLayout(self.files_panel)
        files_layout.setContentsMargins(0, 0, 10, 0)
        files_layout.setSpacing(0)
        files_layout.addWidget(self.search_header)
        files_layout.addWidget(self.files_stack)
        self.footer_layout = QHBoxLayout()
        self.footer_layout.setContentsMargins(0, 4, 0, 12)
        self.footer_layout.addStretch(1)
        for button, _ in self.header_buttons:
            self.footer_layout.addWidget(button)
        files_layout.addLayout(self.footer_layout)
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self._columns_resize_timer = QTimer(self)
        self._columns_resize_timer.setSingleShot(True)
        self._columns_resize_timer.timeout.connect(self._resize_columns)
        self.splitter.installEventFilter(self)
        self.splitter.addWidget(self.files_panel)
        self.splitter.addWidget(self.preview)
        self.columns_swapped = self._load_columns_swap()
        self._files_ratio = self._load_columns_ratio()
        self.splitter.splitterMoved.connect(self._remember_columns_ratio)
        self._apply_columns_layout(self.columns_swapped)
        self.preview.layout.removeWidget(self.preview.breadcrumbs_widget)
        self.header_layout = QHBoxLayout()
        self.header_layout.setContentsMargins(0, 0, 10, 0)
        self.header_layout.setSpacing(self.splitter.handleWidth())
        self.header_layout.addWidget(self.preview.breadcrumbs_widget, 1)
        self.header_layout.addWidget(self.search_status)
        self.layout.addLayout(self.header_layout)
        self.layout.addWidget(self.splitter, 1)
        self.treeView.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.treeView.clicked.connect(self.on_tree_clicked)
        self.treeView.activated.connect(self.preview_index)
        self.tree_search = TreeSearch(self)

        # Toggle the file-list column between the tree and the centered upload
        # state whenever the root directory becomes empty/non-empty.
        self.model.rowsInserted.connect(self.refresh_empty_state)
        self.model.rowsRemoved.connect(self.refresh_empty_state)
        self.model.modelReset.connect(self.refresh_empty_state)
        self.model.directoryLoaded.connect(self.refresh_empty_state)
        self.refresh_empty_state()

        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.setLayout(self.layout)

        self.treeView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.treeView.customContextMenuRequested.connect(self.menus.context)
        self.treeView.setColumnWidth(0, int(self.width() / 2))

        self.treeView.setHeaderHidden(True)
        self.header = self.treeView.header()
        self.header.setContextMenuPolicy(Qt.CustomContextMenu)
        self.header.customContextMenuRequested.connect(self.menus.header)
        self.header.setStretchLastSection(False)
        self.header.setContentsMargins(0, 0, 0, 0)
        self.header.setSectionsClickable(True)
        self.header.setSortIndicatorShown(True)
        self.header.setSortIndicator(0, Qt.AscendingOrder)
        self.treeView.setSortingEnabled(True)
        self.model.sort(0, Qt.AscendingOrder)

        self.model.modelReset.connect(self._schedule_restore_columns)
        self.model.layoutChanged.connect(lambda *_: self._schedule_restore_columns())
        self.model.directoryLoaded.connect(lambda *_: self._schedule_restore_columns())
        self.adjustColumnWidths()

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


        try:
            sc_copy = QShortcut(QKeySequence.Copy, self.treeView, context=Qt.WidgetWithChildrenShortcut)
            sc_copy.activated.connect(self.clipboard.copy)
            sc_cut = QShortcut(QKeySequence.Cut, self.treeView, context=Qt.WidgetWithChildrenShortcut)
            sc_cut.activated.connect(self.clipboard.cut)
            sc_paste = QShortcut(QKeySequence.Paste, self.treeView, context=Qt.WidgetWithChildrenShortcut)
            sc_paste.activated.connect(self.clipboard.paste_current)
        except Exception:
            pass

        self._dnd_handler = ExplorerDropHandler(self)

    def _load_columns_swap(self) -> bool:
        """Return persisted Files column order; missing/invalid values mean default order."""
        try:
            value = self.window.core.config.get('files.columns.swap', False)
            return value is True
        except Exception:
            return False

    def _load_columns_ratio(self) -> float:
        """Load the file-list share independently of column order."""
        try:
            value = float(self.window.core.config.get('files.columns.ratio', 0.45))
            if 0 < value < 1:
                return value
        except (TypeError, ValueError, OverflowError):
            pass
        return 0.45

    def _remember_columns_ratio(self, *_):
        """Only manual separator moves replace the preferred proportion."""
        sizes = self.splitter.sizes()
        total = sum(sizes)
        if len(sizes) != 2 or total <= 0 or not all(sizes):
            return
        self._files_ratio = sizes[1 if self.columns_swapped else 0] / total
        config = self.window.core.config
        config.set('files.columns.ratio', self._files_ratio)
        config.save()

    def _resize_columns(self):
        """Follow the last user proportion without recording minimum-size clamps."""
        if self._closed or not self.splitter.isVisible():
            return
        available = max(0, self.splitter.width() - self.splitter.handleWidth())
        files_size = round(available * self._files_ratio)
        preview_size = max(0, available - files_size)
        sizes = [preview_size, files_size] if self.columns_swapped else [files_size, preview_size]
        self.splitter.setSizes(sizes)

    def _apply_columns_layout(self, swapped: bool):
        """Apply column order while keeping each panel's preferred share."""
        if swapped:
            self.splitter.insertWidget(0, self.preview)
            self.splitter.insertWidget(1, self.files_panel)
        else:
            self.splitter.insertWidget(0, self.files_panel)
            self.splitter.insertWidget(1, self.preview)
        # Equal stretch factors let Qt resize both panels proportionally.
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)
        self.columns_swapped = swapped
        files_size = round(1000 * self._files_ratio)
        sizes = [1000 - files_size, files_size] if swapped else [files_size, 1000 - files_size]
        self.splitter.setSizes(sizes)
        self._columns_resize_timer.start(0)

    def toggle_columns(self):
        """Swap Files columns in runtime and persist the selected order."""
        swapped = not self.columns_swapped
        self._apply_columns_layout(swapped)
        try:
            config = self.window.core.config
            config.set('files.columns.swap', swapped)
            config.save()
        except Exception as e:
            try:
                self.window.core.debug.log(e)
            except Exception:
                pass

    def _root_is_empty(self) -> bool:
        try:
            with os.scandir(self.directory) as entries:
                return next(entries, None) is None
        except (FileNotFoundError, NotADirectoryError):
            return True
        except OSError:
            return False

    def refresh_empty_state(self, *args):
        """Show upload affordance instead of the tree when the workdir is empty."""
        if self._root_is_empty():
            self.files_stack.setCurrentWidget(self.empty_files_wrapper)
        else:
            self.files_stack.setCurrentWidget(self.treeView)

    def retranslate(self):
        """Refresh Files labels/tooltips after a runtime language change."""
        for button, tooltip in self.header_buttons:
            button.setToolTip(trans(tooltip))
        self.search.setPlaceholderText(trans('files.search.placeholder'))
        self.searching_text = trans('files.search.searching')
        self.empty_files.retranslate()
        if self.preview.path is None:
            self.preview.show_empty()


    def on_tree_clicked(self, index):
        """Handle a single left-click in the file tree.

        Files are previewed as before. Directories toggle their expanded state,
        so navigating the tree does not depend on the branch indicator.
        """
        path = self.model.filePath(index)
        if os.path.isdir(path):
            if QGuiApplication.keyboardModifiers() & (Qt.ControlModifier | Qt.ShiftModifier):
                return
            if self.treeView.isExpanded(index):
                self.treeView.collapse(index)
            else:
                self.treeView.expand(index)
            return
        self.preview_index(index)

    def preview_index(self, index):
        path = self.model.filePath(index)
        if os.path.isfile(path):
            if not self.preview.open_file(path) and self.preview.path:
                self.treeView.setCurrentIndex(self.model.index(self.preview.path))

    def navigate_directory(self, path):
        self.search.clear()
        self.tree_search.start()
        index = self.model.index(path)
        ancestor = index
        while ancestor.isValid() and ancestor != self.treeView.rootIndex():
            self.treeView.expand(ancestor)
            ancestor = ancestor.parent()
        if index.isValid():
            self.treeView.setCurrentIndex(index)
            self.treeView.scrollTo(index)

    def _schedule_restore_columns(self):
        """Keep the single name column after filesystem model refreshes."""
        if not self._closed:
            QTimer.singleShot(0, self.adjustColumnWidths)

    def eventFilter(self, source, event):
        """
        Focus event filter

        :param source: source
        :param event: event
        """
        if source is getattr(self, 'splitter', None) and event.type() in (QEvent.Resize, QEvent.Show):
            self._columns_resize_timer.start(0)
        if event.type() in (QEvent.FocusIn, QEvent.MouseButtonPress):
            if getattr(self, 'tab', None) is not None:
                col_idx = self.tab.column_idx
                self.window.controller.tabs.on_column_focus(col_idx)
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
        """Refresh the root and restart the current recursive search."""
        if not self.preview.set_root(self.directory):
            self.directory = self.preview.root
            return
        self.empty_files.set_target_dir(self.directory)
        self.model.beginResetModel()
        self.model.setRootPath(self.directory)
        self.model.endResetModel()
        self.treeView.setRootIndex(self.model.index(self.directory))
        self.tree_search.start()
        self.refresh_empty_state()
        self._schedule_restore_columns()


    def adjustColumnWidths(self):
        """Show only the filename, filling the tree panel."""
        if self._closed:
            return
        for column in range(1, self.model.columnCount()):
            self.treeView.setColumnHidden(column, True)
        self.header.setSectionResizeMode(0, QHeaderView.Stretch)

    def resizeEvent(self, event: QResizeEvent):
        """
        Resize event

        :param event: Event object
        """
        super().resizeEvent(event)
        if event.oldSize().width() != event.size().width():
            self.adjustColumnWidths()


    # ===== Copy / Cut / Paste API =====

    def selected_paths(self) -> list:
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

    def parent_for_selection(self, paths: list) -> str:
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


    # ===== Filesystem helpers =====


    def expand_directory(self, path: str, center: bool = False):
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

    def reveal(self, paths: list, select_first: bool = True):
        """
        Reveal and optionally select the given paths in the view.
        Tries a few times with small delays to wait for model refresh.
        """
        def do_reveal(attempts_left=6):
            if getattr(self, '_closed', False):
                return
            try:
                sm = self.treeView.selectionModel()
            except Exception:
                sm = None
            first_index = None
            for p in paths:
                dir_path = p if os.path.isdir(p) else os.path.dirname(p)
                self.expand_directory(dir_path, center=False)
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


    def stop(self):
        """Cancel asynchronous work before the frontend leaves the registry."""
        self._closed = True
        self.tree_search.cancelled.set()
        self.tree_search.generation += 1
        self.tree_search.timer.stop()
        self.tree_search.apply_timer.stop()
        self.tree_search.stop_applying()
        self._columns_resize_timer.stop()
        self._dnd_handler._auto_timer.stop()

    def on_delete(self):
        self.stop()
        if self.tool.explorer is self:
            self.tool.unregister_surface(self.tool)
            self.tool.explorer = None
