#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.12 08:00:00                  #
# ================================================== #

import datetime

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QImage, QPainter, QPen, QAction, QIcon, QKeySequence
from PySide6.QtWidgets import QMenu, QWidget, QFileDialog, QMessageBox, QApplication

from pygpt_net.utils import trans
import pygpt_net.icons_rc


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
        self.undoStack = []
        self.redoStack = []
        self.undoLimit = 10
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()

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
        actions = {}
        actions['undo'] = QAction(QIcon(":/icons/undo.svg"), trans('action.undo'), self)
        actions['undo'].triggered.connect(
            lambda: self.undo())
        if self.has_undo():
            actions['undo'].setEnabled(True)
        else:
            actions['undo'].setEnabled(False)

        actions['redo'] = QAction(QIcon(":/icons/redo.svg"), trans('action.redo'), self)
        actions['redo'].triggered.connect(
            lambda: self.redo())
        if self.has_redo():
            actions['redo'].setEnabled(True)
        else:
            actions['redo'].setEnabled(False)

        actions['copy'] = QAction(QIcon(":/icons/copy.svg"),  trans('action.copy'), self)
        actions['copy'].triggered.connect(
            lambda: self.handle_copy()
        )

        is_paste = False
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()
        if mime_data.hasImage():
            is_paste = True

        actions['paste'] = QAction(QIcon(":/icons/paste.svg"), trans('action.paste'), self)
        actions['paste'].triggered.connect(
            lambda: self.handle_paste()
        )
        if is_paste:
            actions['paste'].setEnabled(True)
        else:
            actions['paste'].setEnabled(False)

        actions['open'] = QAction(QIcon(":/icons/folder_filled.svg"), trans('action.open'), self)
        actions['open'].triggered.connect(
            lambda: self.action_open())
        actions['capture'] = QAction(QIcon(":/icons/fullscreen.svg"), trans('painter.btn.capture'), self)
        actions['capture'].triggered.connect(
            lambda: self.action_capture())
        actions['save'] = QAction(QIcon(":/icons/save.svg"), trans('img.action.save'), self)
        actions['save'].triggered.connect(
            lambda: self.action_save())
        actions['clear'] = QAction(QIcon(":/icons/close.svg"), trans('painter.btn.clear'), self)
        actions['clear'].triggered.connect(
            lambda: self.action_clear())

        menu = QMenu(self)
        menu.addAction(actions['undo'])
        menu.addAction(actions['redo'])
        menu.addAction(actions['open'])
        menu.addAction(actions['capture'])
        menu.addAction(actions['copy'])
        menu.addAction(actions['paste'])
        menu.addAction(actions['save'])
        menu.addAction(actions['clear'])
        menu.exec_(event.globalPos())

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
            # to fit the width
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

        self.image = QImage(
            self.width(),
            self.height(),
            QImage.Format_RGB32,
        )
        self.image.fill(Qt.white)
        painter = QPainter(self.image)
        painter.drawImage(0, 0, new)
        painter.end()
        self.update()
        self.originalImage = self.image

    def saveForUndo(self):
        """Save current state for undo"""
        if len(self.undoStack) >= self.undoLimit:
            self.undoStack.pop(0)
        self.undoStack.append(self.image.copy())
        self.redoStack.clear()  # clear redo on new action

    def undo(self):
        """Undo the last action"""
        if self.undoStack:
            self.redoStack.append(self.image.copy())
            self.image = self.undoStack.pop()
            self.update()

    def redo(self):
        """Redo the last undo action"""
        if self.redoStack:
            self.undoStack.append(self.image.copy())
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

    def set_brush_size(self, size):
        """
        Set the brush size

        :param size: Brush size
        """
        self.brushSize = size

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
            painter.setPen(
                QPen(
                    self.brushColor,
                    self.brushSize,
                    Qt.SolidLine,
                    Qt.RoundCap,
                    Qt.RoundJoin,
                )
            )
            painter.drawPoint(self.lastPoint)
            self.update()

    def mouseMoveEvent(self, event):
        """
        Mouse move event

        :param event: Event
        """
        if (event.buttons() & Qt.LeftButton) and self.drawing:
            painter = QPainter(self.image)
            painter.setPen(
                QPen(
                    self.brushColor,
                    self.brushSize,
                    Qt.SolidLine,
                    Qt.RoundCap,
                    Qt.RoundJoin,
                )
            )
            painter.drawLine(self.lastPoint, event.pos())
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
            self.image = new
