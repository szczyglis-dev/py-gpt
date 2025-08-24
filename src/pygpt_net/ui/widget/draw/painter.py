#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.24 23:00:00                  #
# ================================================== #

import datetime
from collections import deque

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QImage, QPainter, QPen, QAction, QIcon
from PySide6.QtWidgets import QMenu, QWidget, QFileDialog, QMessageBox, QApplication

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.utils import trans


class PainterWidget(QWidget):
    def __init__(self, window=None):
        super().__init__(window)
        self.window = window
        self.image = QImage(self.size(), QImage.Format_RGB32)
        self.image.fill(Qt.white)
        self.drawing = False
        self.brushSize = 3
        self.brushColor = Qt.black
        self.lastPoint = QPoint()
        self.originalImage = None
        self.undoLimit = 10
        self.undoStack = deque(maxlen=self.undoLimit)
        self.redoStack = deque()
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()
        self.installEventFilter(self)
        self.tab = None
        self._pen = QPen(self.brushColor, self.brushSize, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setAttribute(Qt.WA_StaticContents, True)

        self._act_undo = QAction(QIcon(":/icons/undo.svg"), trans('action.undo'), self)
        self._act_undo.triggered.connect(self.undo)

        self._act_redo = QAction(QIcon(":/icons/redo.svg"), trans('action.redo'), self)
        self._act_redo.triggered.connect(self.redo)

        self._act_copy = QAction(QIcon(":/icons/copy.svg"), trans('action.copy'), self)
        self._act_copy.triggered.connect(self.handle_copy)

        self._act_paste = QAction(QIcon(":/icons/paste.svg"), trans('action.paste'), self)
        self._act_paste.triggered.connect(self.handle_paste)

        self._act_open = QAction(QIcon(":/icons/folder_filled.svg"), trans('action.open'), self)
        self._act_open.triggered.connect(self.action_open)

        self._act_capture = QAction(QIcon(":/icons/fullscreen.svg"), trans('painter.btn.capture'), self)
        self._act_capture.triggered.connect(self.action_capture)

        self._act_save = QAction(QIcon(":/icons/save.svg"), trans('img.action.save'), self)
        self._act_save.triggered.connect(self.action_save)

        self._act_clear = QAction(QIcon(":/icons/close.svg"), trans('painter.btn.clear'), self)
        self._act_clear.triggered.connect(self.action_clear)

        self._ctx_menu = QMenu(self)
        self._ctx_menu.addAction(self._act_undo)
        self._ctx_menu.addAction(self._act_redo)
        self._ctx_menu.addAction(self._act_open)
        self._ctx_menu.addAction(self._act_capture)
        self._ctx_menu.addAction(self._act_copy)
        self._ctx_menu.addAction(self._act_paste)
        self._ctx_menu.addAction(self._act_save)
        self._ctx_menu.addAction(self._act_clear)

    def set_tab(self, tab: Tab):
        """
        Set tab

        :param tab: Tab
        """
        self.tab = tab

    def handle_paste(self):
        """Handle clipboard paste"""
        clipboard = QApplication.clipboard()
        source = clipboard.mimeData()
        if source.hasImage():
            image = clipboard.image()
            if isinstance(image, QImage):
                self.window.ui.painter.set_image(image)

    def handle_copy(self):
        """Handle clipboard copy"""
        clipboard = QApplication.clipboard()
        clipboard.setImage(self.image)

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: Event
        """
        self._act_undo.setEnabled(self.has_undo())
        self._act_redo.setEnabled(self.has_redo())

        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()
        self._act_paste.setEnabled(bool(mime_data.hasImage()))

        self._ctx_menu.exec(event.globalPos())

    def action_open(self):
        """Open the image"""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Image",
            "",
            "Images (*.png *.jpg *.jpeg)",
        )
        if path:
            self.open_image(path)

    def action_capture(self):
        """Capture the image"""
        self.saveForUndo()
        self.window.controller.painter.capture.use()

    def action_save(self):
        """Save image to file"""
        name = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".png"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Image",
            name,
            "PNG(*.png);;JPEG(*.jpg *.jpeg);;All Files(*.*) ",
        )
        if path:
            self.image.save(path)

    def action_clear(self):
        """Clear the image"""
        self.saveForUndo()
        self.clear_image()
        self.originalImage = self.image

    def open_image(self, path):
        """
        Open the image

        :param path: Path to image
        """
        self.saveForUndo()
        img = QImage(path)
        if img.isNull():
            QMessageBox.information(self, "Image Loader", "Cannot load file.")
            return
        self.scale_to_fit(img)

    def set_image(self, image):
        """
        Set image

        :param image: Image
        """
        self.saveForUndo()
        self.scale_to_fit(image)
        self.originalImage = self.image
        self.update()

    def scale_to_fit(self, image):
        """
        Scale image to fit the widget

        :param image: Image
        """
        if image.width() == self.width():
            new = image
        else:
            if image.width() > image.height():
                width = self.width()
                height = (image.height() * self.width()) / image.width()
                new = image.scaled(
                    width,
                    int(height),
                    Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation,
                )
            else:
                height = self.height()
                width = (image.width() * self.height()) / image.height()
                new = image.scaled(
                    int(width),
                    height,
                    Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation,
                )

        if self.image.size() != self.size():
            self.image = QImage(self.size(), QImage.Format_RGB32)
        self.image.fill(Qt.white)
        painter = QPainter(self.image)
        painter.drawImage(0, 0, new)
        painter.end()
        self.update()
        self.originalImage = self.image

    def saveForUndo(self):
        """Save current state for undo"""
        self.undoStack.append(QImage(self.image))
        self.redoStack.clear()

    def undo(self):
        """Undo the last action"""
        if self.undoStack:
            self.redoStack.append(QImage(self.image))
            self.image = self.undoStack.pop()
            self.update()

    def redo(self):
        """Redo the last undo action"""
        if self.redoStack:
            self.undoStack.append(QImage(self.image))
            self.image = self.redoStack.pop()
            self.update()

    def has_undo(self) -> bool:
        """Check if undo is available"""
        return bool(self.undoStack)

    def has_redo(self) -> bool:
        """Check if redo is available"""
        return bool(self.redoStack)

    def set_brush_color(self, color):
        """
        Set the brush color

        :param color: Color
        """
        self.brushColor = color
        self._pen.setColor(color)

    def set_brush_size(self, size):
        """
        Set the brush size

        :param size: Brush size
        """
        self.brushSize = size
        self._pen.setWidth(size)

    def clear_image(self):
        """Clear the image"""
        self.saveForUndo()
        self.image.fill(Qt.white)
        self.update()

    def mousePressEvent(self, event):
        """
        Mouse press event

        :param event: Event
        """
        if event.button() == Qt.LeftButton:
            self.drawing = True
            self.lastPoint = event.pos()
            self.saveForUndo()
            painter = QPainter(self.image)
            painter.setPen(self._pen)
            painter.drawPoint(self.lastPoint)
            painter.end()
            self.update()

    def mouseMoveEvent(self, event):
        """
        Mouse move event

        :param event: Event
        """
        if (event.buttons() & Qt.LeftButton) and self.drawing:
            painter = QPainter(self.image)
            painter.setPen(self._pen)
            painter.drawLine(self.lastPoint, event.pos())
            painter.end()
            self.lastPoint = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        """
        Mouse release event

        :param event: Event
        """
        if event.button() == Qt.LeftButton or event.button() == Qt.RightButton:
            self.drawing = False

    def keyPressEvent(self, event):
        """
        Key press event to handle undo action

        :param event: Event
        """
        if event.key() == Qt.Key_Z and QApplication.keyboardModifiers() == Qt.ControlModifier:
            self.undo()
        elif event.key() == Qt.Key_V and QApplication.keyboardModifiers() == Qt.ControlModifier:
            self.handle_paste()

    def paintEvent(self, event):
        """
        Paint event (draw)

        :param event: Event
        """
        painter = QPainter(self)
        painter.drawImage(self.rect(), self.image, self.image.rect())
        painter.end()
        self.originalImage = self.image

    def resizeEvent(self, event):
        """
        Update coords on resize

        :param event: Event
        """
        if self.image.size() != self.size():
            new = QImage(self.size(), QImage.Format_RGB32)
            new.fill(Qt.white)
            painter = QPainter(new)
            painter.drawImage(QPoint(0, 0), self.image)
            painter.end()
            self.image = new

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