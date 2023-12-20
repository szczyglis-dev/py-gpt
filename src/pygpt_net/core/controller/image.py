#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.20 18:00:00                  #
# ================================================== #

import os
import shutil
import webbrowser
from pathlib import PurePath

from PySide6 import QtGui, QtCore
from PySide6.QtWidgets import QFileDialog

from ..context import ContextItem
from ..dispatcher import Event
from ..utils import trans


class Image:
    def __init__(self, window=None):
        """
        Images controller

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup images"""
        if self.window.config.get('img_raw'):
            self.window.ui.config_option['img_raw'].setChecked(True)
        else:
            self.window.ui.config_option['img_raw'].setChecked(False)

    def send_text(self, text):
        """
        Send prompt to DALL-E and opens generated image in dialog

        :param text: prompt to send
        """
        try:
            num_of_images = int(self.window.ui.config_option['img_variants'].input.text())
        except:
            num_of_images = 1
            if num_of_images < 1:
                num_of_images = 1
            elif num_of_images > 4:
                num_of_images = 4

        self.window.set_status(trans('status.sending'))

        # create ctx item
        ctx = ContextItem()
        ctx.set_input(text, self.window.config.get('user_name'))

        # dispatch event
        event = Event('ctx.before')
        event.ctx = ctx
        self.window.dispatch(event)

        self.window.app.context.add(ctx)
        self.window.controller.output.append_input(ctx)

        # call DALL-E API and generate images
        try:
            paths, prompt = self.window.app.images.generate(text, self.window.config.get('model'), num_of_images)
            string = ""
            i = 1
            for path in paths:
                string += "{}) `{}`".format(i, path) + "\n"
                i += 1
            self.open_images(paths)

            if not self.window.config.get('img_raw'):
                string += "\nPrompt: "
                string += prompt

            ctx.set_output(string.strip())

            # dispatch event
            event = Event('ctx.after')
            event.ctx = ctx
            self.window.dispatch(event)

            self.window.controller.output.append_output(ctx)
            self.window.app.context.store()
            self.window.set_status("OK.")
        except Exception as e:
            print(e)
            self.window.ui.dialogs.alert(str(e))
            self.window.set_status(trans('status.error'))

    def open_images(self, paths):
        """
        Open image in dialog

        :param paths: paths to images
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
            self.window.ui.nodes['dialog.image.pixmap'][i].path = path
            self.window.ui.nodes['dialog.image.pixmap'][i].setPixmap(pixmap)
            self.window.ui.nodes['dialog.image.pixmap'][i].setVisible(True)
            i += 1

        # hide unused images
        for j in range(i, 4):
            self.window.ui.nodes['dialog.image.pixmap'][j].setVisible(False)

        # resize
        self.window.ui.dialog['image'].resize(520, 520)
        self.window.ui.dialog['image'].show()

    def img_action_open(self, path):
        """
        Open image in default image viewer

        :param path: path to image
        """
        webbrowser.open(path)

    def img_action_open_dir(self, path):
        """
        Open image in default image viewer

        :param path: path to image
        """
        if os.path.exists(path):
            self.window.controller.files.open_in_file_manager(path)

    def img_action_save(self, path):
        """
        Save image

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
        Delete image

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
                if self.window.ui.nodes['dialog.image.pixmap'][i].path == path:
                    self.window.ui.nodes['dialog.image.pixmap'][i].setVisible(False)
        except Exception as e:
            print(e)

    def enable_raw(self):
        """
        Enable help for images
        """
        self.window.config.set('img_raw', True)
        self.window.config.save()

    def disable_raw(self):
        """
        Disable help for images
        """
        self.window.config.set('img_raw', False)
        self.window.config.save()

    def toggle_raw(self, state):
        """
        Toggle help for images
        """
        if not state:
            self.disable_raw()
        else:
            self.enable_raw()
