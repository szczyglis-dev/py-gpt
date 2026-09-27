"""Breadcrumb file tree in a native popup, dismissed by outside clicks."""
import os

from PySide6.QtCore import Qt, QDir, QModelIndex
from PySide6.QtWidgets import QFrame, QVBoxLayout, QTreeView, QFileSystemModel, QAbstractItemView


class DirectoryFileSystemModel(QFileSystemModel):
    """Filesystem model that does not advertise expandability for empty folders."""

    def hasChildren(self, parent=QModelIndex()) -> bool:
        if parent.isValid():
            try:
                index = parent.siblingAtColumn(0)
                path = self.filePath(index)
                if path and self.isDir(index):
                    with os.scandir(path) as entries:
                        return next(entries, None) is not None
            except OSError:
                # Preserve QFileSystemModel's lazy/default behavior when the
                # directory cannot be inspected (permissions, transient mount, etc.).
                pass
            except Exception:
                pass
        return super().hasChildren(parent)


class DirectoryPopup(QFrame):
    def __init__(self, path, open_file, parent=None):
        super().__init__(parent, Qt.Popup)
        self.open_file = open_file
        self.setFrameShape(QFrame.StyledPanel)
        self.resize(420, 350)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        self.tree = QTreeView(self)
        self.model = DirectoryFileSystemModel(self)
        self.model.setFilter(QDir.AllEntries | QDir.NoDotAndDotDot | QDir.Hidden)
        self.model.setRootPath(path)
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(path))
        self.tree.setHeaderHidden(True)
        for column in range(1, self.model.columnCount()):
            self.tree.hideColumn(column)
        self.tree.setUniformRowHeights(True)
        self.tree.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tree.setExpandsOnDoubleClick(False)
        self.tree.setSortingEnabled(True)
        self.tree.sortByColumn(0, Qt.AscendingOrder)
        self.tree.clicked.connect(self.activate)
        self.tree.activated.connect(self.open_selected_file)
        layout.addWidget(self.tree)

    def activate(self, index):
        if self.model.isDir(index):
            # Qt handles clicks on the disclosure arrow; this handles the row.
            self.tree.setExpanded(index, not self.tree.isExpanded(index))
        else:
            self.open_selected_file(index)

    def open_selected_file(self, index):
        if index.isValid() and not self.model.isDir(index):
            path = self.model.filePath(index)
            self.close()
            self.open_file(path)

    def showEvent(self, event):
        super().showEvent(event)
        self.tree.setFocus(Qt.PopupFocusReason)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        super().closeEvent(event)
        self.deleteLater()
