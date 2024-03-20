#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.20 06:00:00                  #
# ================================================== #

import os
import shutil

from PySide6 import QtGui, QtCore
from PySide6.QtWidgets import QFileDialog

from pygpt_net.utils import trans


class ImageViewer:
    def __init__(self, window=None):
        """
        Image viewer controller

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup"""
        pass

    def on_exit(self):
        """On exit"""
        pass

    def open_file(self):
        """Open image file dialog"""
        path, _ = QFileDialog.getOpenFileName(
            self.window,
            trans("action.open"))
        if path:
            self.close_preview()
            self.open_preview(path)

    def open_images(self, paths: list):
        """
        Open image in dialog

        :param paths: paths to images
        """
        num_images = len(paths)
        resize_to = 512
        if num_images > 1:
            resize_to = 256

        i = 0
        for path in paths:
            pixmap = QtGui.QPixmap(path)
            pixmap = pixmap.scaled(resize_to, resize_to, QtCore.Qt.KeepAspectRatio)
            self.window.ui.nodes['dialog.image.pixmap'][i].path = path
            self.window.ui.nodes['dialog.image.pixmap'][i].setPixmap(pixmap)
            self.window.ui.nodes['dialog.image.pixmap'][i].setVisible(True)
            i += 1

        # hide unused images
        for j in range(i, 4):
            self.window.ui.nodes['dialog.image.pixmap'][j].setVisible(False)

        # resize dialog
        self.window.ui.dialog['image'].resize(520, 520)
        self.window.ui.dialog['image'].show()

    def close_images(self):
        """Close image dialog"""
        self.window.ui.dialog['image'].close()

    def open_preview(self, path: str = None):
        """
        Open image preview in dialog

        :param path: path to image
        """
        if path is None:
            path = self.window.ui.nodes['dialog.image.preview.pixmap.source'].path  # previous img

        if path is None:
            pixmap = QtGui.QPixmap(0, 0)  # blank image
            self.window.ui.nodes['dialog.image.preview.pixmap.source'].setPixmap(pixmap)
            self.window.ui.nodes['dialog.image.preview.pixmap'].path = None
            self.window.ui.nodes['dialog.image.preview.pixmap'].resize(520, 520)
        else:
            pixmap = QtGui.QPixmap(path)
            self.window.ui.nodes['dialog.image.preview.pixmap.source'].setPixmap(pixmap)
            self.window.ui.nodes['dialog.image.preview.pixmap'].path = path
            self.window.ui.nodes['dialog.image.preview.pixmap'].resize(520, 520)

        if path is not None:
            self.window.ui.dialog['image_preview'].path = path
            self.window.ui.dialog['image_preview'].setWindowTitle(os.path.basename(path))
        else:
            self.window.ui.dialog['image_preview'].path = None
            self.window.ui.dialog['image_preview'].setWindowTitle("Image Viewer")

        self.window.ui.dialog['image_preview'].resize(520, 520)
        self.window.ui.dialog['image_preview'].show()

    def close_preview(self):
        """Close image preview dialog"""
        self.window.ui.dialog['image_preview'].resize(500, 500)
        self.window.ui.dialog['image_preview'].close()

    def open(self, path: str):
        """
        Open image in default image viewer

        :param path: path to image
        """
        if os.path.exists(path):
            self.window.controller.files.open(path)

    def open_dir(self, path: str):
        """
        Open image in default image viewer

        :param path: path to image
        """
        if os.path.exists(path):
            self.window.controller.files.open_dir(
                path,
                True,
            )

    def save(self, path: str):
        """
        Save image

        :param path: path to image
        """
        if path is None:
            self.window.ui.status("No image to save")
            return

        save_path = QFileDialog.getSaveFileName(
            self.window,
            trans('img.save.title'),
            os.path.basename(path),
            "PNG (*.png)",
        )
        if save_path:
            try:
                if save_path[0] == '':
                    return
                shutil.copyfile(path, save_path[0])
                self.window.ui.status(trans('status.img.saved'))
            except Exception as e:
                self.window.core.debug.log(e)

    def delete(self, path: str, force: bool = False):
        """
        Delete image

        :param path: path to image
        :param force: force delete without confirmation
        """
        if path is None:
            self.window.ui.status("No image to delete")
            return

        if not force:
            self.window.ui.dialogs.confirm(
                type='img_delete',
                id=path,
                msg=trans('confirm.img.delete'),
            )
            return
        try:
            os.remove(path)
            for i in range(0, 4):
                if self.window.ui.nodes['dialog.image.pixmap'][i].path == path:
                    self.window.ui.nodes['dialog.image.pixmap'][i].setVisible(False)
        except Exception as e:
            self.window.core.debug.log(e)
