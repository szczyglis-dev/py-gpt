#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Created Date: 2023.04.09 20:00:00                  #
# ================================================== #

import os
import shutil
from showinfm import show_in_file_manager

from PySide6 import QtGui, QtCore
import webbrowser

from PySide6.QtWidgets import QFileDialog

from ..context import ContextItem
from ..utils import trans


class Image:
    def __init__(self, window=None):
        """
        Images controller

        :param window: main window
        """
        self.window = window

    def send_text(self, text):
        """
        Sends prompt to DALL-E and opens generated image in dialog

        :param text: text to send
        """
        try:
            num_of_images = int(self.window.config_option['img_variants'].input.text())
        except:
            num_of_images = 1
            if num_of_images < 1:
                num_of_images = 1
            elif num_of_images > 4:
                num_of_images = 4

        self.window.set_status(trans('status.sending'))

        # create ctx item
        ctx = ContextItem()
        ctx.set_input(text, self.window.config.data['user_name'])
        self.window.gpt.context.add(ctx)
        self.window.controller.output.append_input(ctx)

        # call DALL-E 2 API and generate images
        try:
            paths = self.window.images.generate(text, num_of_images)
            string = ""
            i = 1
            for path in paths:
                string += "{} - {}".format(i, path) + "\n"
                i += 1
            self.open_images(paths)
            ctx.set_output(string.strip())
            self.window.controller.output.append_output(ctx)
            self.window.gpt.context.store()
            self.window.set_status("OK.")
        except Exception as e:
            print(e)
            self.window.ui.dialogs.alert(str(e))
            self.window.set_status(trans('status.error'))

    def open_images(self, paths):
        """
        Opens image in dialog

        :param path: path to image
        """
        num_images = len(paths)
        resize_to = 512
        if num_images == 1:
            resize_to = 512
        elif num_images > 1:
            resize_to = 256

        i = 0
        for path in paths:
            pixmap = QtGui.QPixmap(path)
            pixmap = pixmap.scaled(resize_to, resize_to, QtCore.Qt.KeepAspectRatio)
            self.window.data['dialog.image.pixmap'][i].path = path
            self.window.data['dialog.image.pixmap'][i].setPixmap(pixmap)
            self.window.data['dialog.image.pixmap'][i].setVisible(True)
            i += 1

        # hide unused images
        for j in range(i, 4):
            self.window.data['dialog.image.pixmap'][j].setVisible(False)

        # resize
        self.window.dialog['image'].resize(520, 520)
        self.window.dialog['image'].show()

    def img_action_open(self, path):
        """
        Opens image in default image viewer

        :param path: path to image
        """
        webbrowser.open(path)

    def img_action_open_dir(self, path):
        """
        Opens image in default image viewer

        :param path: path to image
        """
        if os.path.exists(path):
            show_in_file_manager(path)

    def img_action_save(self, path):
        """
        Saves image

        :param path: path to image
        """
        # get basename from path
        save_path = QFileDialog.getSaveFileName(self.window, trans('img.save.title'), os.path.basename(path),
                                                "PNG (*.png)")
        if save_path:
            # copy file
            try:
                shutil.copyfile(path, save_path[0])
                self.window.set_status(trans('status.img.saved'))
            except Exception as e:
                print(e)

    def img_action_delete(self, path, force=False):
        """
        Deletes image

        :param path: path to image
        :param force: force delete without confirmation
        """
        if not force:
            self.window.ui.dialogs.confirm('img_delete', path, trans('confirm.img.delete'))
            return

        # delete file
        try:
            os.remove(path)
            for i in range(0, 4):
                if self.window.data['dialog.image.pixmap'][i].path == path:
                    self.window.data['dialog.image.pixmap'][i].setVisible(False)
        except Exception as e:
            print(e)
