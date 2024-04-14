#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.14 18:00:00                  #
# ================================================== #

import hashlib
import os
import shutil

from PySide6 import QtGui, QtCore
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QFileDialog

from pygpt_net.tools.base import BaseTool
from pygpt_net.tools.image_viewer.ui.dialogs import DialogSpawner
from pygpt_net.utils import trans


class ImageViewer(BaseTool):
    def __init__(self, *args, **kwargs):
        """
        Image viewer

        :param window: Window instance
        """
        super(ImageViewer, self).__init__(*args, **kwargs)
        self.id = "viewer"
        self.width = 640
        self.height = 400
        self.instance_id = 0
        self.spawner = None

    def setup(self):
        """Setup tool"""
        self.spawner = DialogSpawner(self.window)

    def prepare_id(self, file: str):
        """
        Prepare unique id for file

        :param file: file name
        :return: unique id
        """
        return 'image_viewer_' + hashlib.md5(file.encode('utf-8')).hexdigest()

    def new(self):
        """New image viewer dialog"""
        self.open_preview()

    def open_file(self, id: str, auto_close: bool = True,):
        """
        Open image file dialog

        :param id: dialog id
        :param auto_close: auto close current dialog
        """
        path, _ = QFileDialog.getOpenFileName(
            self.window,
            trans("action.open"),
            "",
            "Image files (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *webp);; All files (*.*)")
        if path:
            self.open_preview(path, id, auto_close)

    def open_preview(
            self,
            path: str = None,
            current_id: str = None,
            auto_close: bool = True):
        """
        Open image preview in dialog

        :param path: path to image
        :param current_id: current dialog id
        :param auto_close: auto close current dialog
        """
        if path:
            id = self.prepare_id(path)
            if current_id and auto_close:
                if id != current_id:
                    self.close_preview(current_id)
        else:
            # new instance id
            id = 'image_viewer_' + str(self.instance_id)
            self.instance_id += 1

        self.window.ui.dialogs.open_instance(
            id,
            width=self.width,
            height=self.height,
            type="image_viewer",
        )

        w = self.width
        h = self.height
        img_suffix = ""

        if path is None:
            path = self.window.ui.dialog[id].source.path  # previous img

        if path is None:
            pixmap = QtGui.QPixmap(0, 0)  # blank image
            self.window.ui.dialog[id].source.setPixmap(pixmap)
            self.window.ui.dialog[id].pixmap.path = None
            self.window.ui.dialog[id].pixmap.resize(w, h)
        else:
            pixmap = QtGui.QPixmap(path)
            img_suffix = " ({}x{}px)".format(pixmap.width(), pixmap.height())
            file_size = self.window.core.filesystem.sizeof_fmt(os.path.getsize(path))
            img_suffix += " - {}".format(file_size)
            self.window.ui.dialog[id].source.setPixmap(pixmap)
            self.window.ui.dialog[id].pixmap.path = path
            self.window.ui.dialog[id].pixmap.resize(w, h)

        if path is not None:
            self.window.ui.dialog[id].path = path
            self.window.ui.dialog[id].setWindowTitle(os.path.basename(path) + img_suffix)
        else:
            self.window.ui.dialog[id].path = None
            self.window.ui.dialog[id].setWindowTitle("Image Viewer")

        self.window.ui.dialog[id].resize(w - 1, h - 1)  # redraw fix
        self.window.ui.dialog[id].resize(w, h)
        self.window.ui.dialog[id].show()

    def close_preview(self, id: str):
        """
        Close image preview dialog

        :param id: dialog id
        """
        self.window.ui.dialog[id].resize(self.width - 1, self.height - 1)  # redraw fix
        self.window.ui.dialog[id].close()

    def open_images(self, paths: list):
        """
        Open image in dialog

        :param paths: paths to images
        """
        num_images = len(paths)
        resize_to = 512
        if num_images > 1:
            resize_to = 256
        w = 520
        h = 520
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
        self.window.ui.dialog['image'].resize(w, h)
        self.window.ui.dialog['image'].show()

    def close_images(self):
        """Close image dialog"""
        self.window.ui.dialog['image'].close()

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
    def save_by_id(self, id: str):
        """
        Save image by dialog id

        :param id: dialog id
        """
        if id in self.window.ui.dialog:
            path = self.window.ui.dialog[id].path
            if path:
                self.save(path)
            else:
                self.window.ui.status("No image to save")

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
            "Image files (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *webp);; All files (*.*)"
        )
        if save_path:
            try:
                if save_path[0] == '':
                    return
                shutil.copyfile(path, save_path[0])
                self.window.ui.status(trans('status.img.saved') + ": {}".format(os.path.basename(save_path[0])))
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

    def setup_menu(self) -> dict:
        """
        Setup main menu

        :return dict with menu actions
        """
        actions = {}
        actions["image.viewer"] = QAction(
            QIcon(":/icons/image.svg"),
            trans("menu.tools.image.viewer"),
            self.window,
            checkable=False,
        )
        actions["image.viewer"].triggered.connect(
            lambda: self.open_preview()
        )
        return actions

    def get_instance(self, type_id: str, dialog_id: str = None):
        """
        Spawn and return dialog instance

        :param type_id: dialog instance type ID
        :param dialog_id: dialog instance ID
        :return dialog instance
        """
        if type_id == "image_viewer":
            return self.spawner.setup(dialog_id)

    def get_lang_mappings(self) -> dict:
        """
        Get language mappings

        :return: dict with language mappings
        """
        return {
            'menu.text': {
                'tools.image.viewer': 'menu.tools.image.viewer',
            }
        }