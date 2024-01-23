#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.23 19:00:00                  #
# ================================================== #

import datetime

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QImage, QPainter, QPen, QAction, QIcon
from PySide6.QtWidgets import QMenu, QWidget, QFileDialog, QMessageBox, QApplication

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
        self.undoStack = []
        self.undoLimit = 10
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: Event
        """
        actions = {}
        actions['undo'] = QAction(QIcon.fromTheme("undo"), trans('action.undo'), self)
        actions['undo'].triggered.connect(
            lambda: self.undo())
        actions['open'] = QAction(QIcon.fromTheme("document-open"), trans('action.open'), self)
        actions['open'].triggered.connect(
            lambda: self.action_open())
        actions['capture'] = QAction(QIcon.fromTheme("view-fullscreen"), trans('painter.btn.capture'), self)
        actions['capture'].triggered.connect(
            lambda: self.action_capture())
        actions['save'] = QAction(QIcon.fromTheme("document-save"), trans('img.action.save'), self)
        actions['save'].triggered.connect(
            lambda: self.action_save())
        actions['clear'] = QAction(QIcon.fromTheme("edit-delete"), trans('painter.btn.clear'), self)
        actions['clear'].triggered.connect(
            lambda: self.action_clear())

        menu = QMenu(self)
        menu.addAction(actions['undo'])
        menu.addAction(actions['open'])
        menu.addAction(actions['capture'])
        menu.addAction(actions['save'])
        menu.addAction(actions['clear'])
        menu.exec_(event.globalPos())

    def action_open(self):
        """Open the image"""
        path, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Images (*.png *.jpg *.jpeg)")
        if path:
            self.open_image(path)

    def action_capture(self):
        """Capture the image"""
        self.saveForUndo()
        self.window.controller.painter.capture.use()

    def action_save(self):
        """Save image to file"""
        name = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".png"
        path, _ = QFileDialog.getSaveFileName(self, "Save Image", name,
                                              "PNG(*.png);;JPEG(*.jpg *.jpeg);;All Files(*.*) ")
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
            height = (image.height() * self.width()) / image.width()
            new = image.scaled(self.width(), int(height), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)

        self.image = QImage(self.width(), self.height(), QImage.Format_RGB32)
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

    def undo(self):
        """Undo the last action"""
        if self.undoStack:
            self.image = self.undoStack.pop()
            self.update()

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

    def mouseMoveEvent(self, event):
        """
        Mouse move event

        :param event: Event
        """
        if (event.buttons() & Qt.LeftButton) and self.drawing:
            painter = QPainter(self.image)
            painter.setPen(QPen(self.brushColor, self.brushSize, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
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
