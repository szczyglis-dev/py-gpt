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


from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy


from pygpt_net.utils import trans


class EmptyFilesState(QWidget):
    """Compact clickable upload target shown when the Files list is empty."""

    def __init__(self, tool, target_dir, parent=None):
        super().__init__(parent)
        self.tool = tool
        self.window = tool.window
        self.target_dir = target_dir
        # Mouse hover/click belongs only to this compact affordance. Drag & drop
        # is handled by the whole file-list column (EmptyFilesDropPanel).
        self.setAcceptDrops(False)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.setMinimumWidth(220)
        self.setMaximumWidth(460)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        self.icon_label = QLabel(self)
        self.icon_label.setPixmap(QIcon(":/icons/upload.svg").pixmap(QSize(64, 64)))
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.icon_label)

        self.text_label = QLabel(trans("files.empty.upload_or_drop"), self)
        self.text_label.setWordWrap(True)
        self.text_label.setAlignment(Qt.AlignCenter)
        self.text_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.text_label)

    def set_target_dir(self, path: str):
        self.target_dir = path

    def retranslate(self):
        self.text_label.setText(trans("files.empty.upload_or_drop"))

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.tool.transfers.upload(self.target_dir)
            event.accept()
            return
        super().mouseReleaseEvent(event)


class EmptyFilesDropPanel(QWidget):
    """Right Files column drop target used while the workdir is empty."""

    def __init__(self, explorer, parent=None):
        super().__init__(parent)
        self.explorer = explorer
        self.setAcceptDrops(True)

    @staticmethod
    def _local_paths(event):
        paths = []
        try:
            mime = event.mimeData()
            if not mime or not mime.hasUrls():
                return paths
            for url in mime.urls():
                if url.isLocalFile():
                    path = url.toLocalFile()
                    if path:
                        paths.append(path)
        except Exception:
            pass
        return paths

    def _accept_external_files(self, event) -> bool:
        # This parent is the fallback drop target for the whole right column.
        # When files exist, the tree view keeps its normal drop/move handling.
        if not self.explorer._root_is_empty():
            return False
        if not self._local_paths(event):
            return False
        event.setDropAction(Qt.CopyAction)
        event.acceptProposedAction()
        return True

    def dragEnterEvent(self, event):
        if not self._accept_external_files(event):
            event.ignore()

    def dragMoveEvent(self, event):
        if not self._accept_external_files(event):
            event.ignore()

    def dropEvent(self, event):
        if not self.explorer._root_is_empty():
            event.ignore()
            return
        paths = self._local_paths(event)
        if not paths:
            event.ignore()
            return
        self.explorer.tool.transfers.import_paths(paths, self.explorer.directory)
        event.setDropAction(Qt.CopyAction)
        event.acceptProposedAction()

