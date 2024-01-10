#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.10 10:00:00                  #
# ================================================== #

import datetime

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QImage, QPainter, QPen, QAction, QIcon
from PySide6.QtWidgets import QMenu, QWidget, QFileDialog, QMessageBox

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

    def contextMenuEvent(self, event):
        """
        Context menu event
        :param event: Event
        """
        actions = {}
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
        menu.addAction(actions['open'])
        menu.addAction(actions['capture'])
        menu.addAction(actions['save'])
        menu.addAction(actions['clear'])
        menu.exec_(event.globalPos())

    def action_open(self):
        """Open the image"""
        filePath, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Images (*.png *.jpg *.jpeg)")
        if filePath:
            loadedImage = QImage(filePath)
            if loadedImage.isNull():
                QMessageBox.information(self, "Image Loader", "Cannot load file.")
                return
            self.scaleImageToFit(loadedImage)

    def scaleImageToFit(self, image):
        if image.width() == self.width():
            newImage = image
        else:
            newHeight = (image.height() * self.width()) / image.width()
            newImage = image.scaled(self.width(), int(newHeight), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)

        self.image = QImage(self.width(), self.height(), QImage.Format_RGB32)
        self.image.fill(Qt.white)
        painter = QPainter(self.image)
        painter.drawImage(0, 0, newImage)
        painter.end()
        self.update()

    def action_capture(self):
        """Capture the image"""
        self.window.controller.drawing.capture()

    def action_save(self):
        """Save image to file"""
        name = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".png"
        filePath, _ = QFileDialog.getSaveFileName(self, "Save Image", name,
                                                  "PNG(*.png);;JPEG(*.jpg *.jpeg);;All Files(*.*) ")
        if filePath:
            self.image.save(filePath)

    def action_clear(self):
        """Clear the image"""
        self.clearImage()

    def mousePressEvent(self, event):
        """
        Mouse press event

        :param event: Event
        """
        self.drawing = True
        self.lastPoint = event.pos()

    def setBrushColor(self, color):
        """
        Set the brush color

        :param color: Color
        """
        self.brushColor = color

    def clearImage(self):
        """Clear the image"""
        self.image.fill(Qt.white)
        self.update()

    def setBrushSize(self, size):
        """
        Set the brush size

        :param size: Brush size
        """
        self.brushSize = size

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

    def paintEvent(self, event):
        """
        Paint event (draw)

        :param event: Event
        """
        canvasPainter = QPainter(self)
        canvasPainter.drawImage(self.rect(), self.image, self.image.rect())

    def resizeEvent(self, event):
        """
        Resize event (on window resize)

        :param event: Event
        """
        if self.image.size() != self.size():
            newImage = QImage(self.size(), QImage.Format_RGB32)
            newImage.fill(Qt.white)
            painter = QPainter(newImage)
            painter.drawImage(QPoint(0, 0), self.image)
            self.image = newImage
