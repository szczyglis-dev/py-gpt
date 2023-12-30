#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.30 02:00:00                  #
# ================================================== #

import json
import os
import shutil
import webbrowser

from PySide6 import QtGui, QtCore
from PySide6.QtWidgets import QFileDialog, QApplication

from pygpt_net.item.ctx import CtxItem
from pygpt_net.core.dispatcher import Event
from pygpt_net.utils import trans


class Image:
    def __init__(self, window=None):
        """
        Images controller

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup images"""
        if self.window.core.config.get('img_raw'):
            self.window.ui.config_option['img_raw'].setChecked(True)
        else:
            self.window.ui.config_option['img_raw'].setChecked(False)

    def send_text(self, text):
        """
        Send prompt to API and open generated image in dialog

        :param text: prompt for image generation
        :return: ctx item
        :rtype: CtxItem
        """
        num = int(self.window.ui.config_option['img_variants'].input.text() or 1)
        if num < 1:
            num = 1
        elif num > 4:
            num = 4

        # force one image if dall-e-3 model is used
        model = self.window.core.config.get('model')
        if model == 'dall-e-3':
            num = 1

        self.window.set_status(trans('status.sending'))

        # create ctx item
        ctx = CtxItem()
        ctx.set_input(text, self.window.core.config.get('user_name'))

        # dispatch event
        event = Event('ctx.before')
        event.ctx = ctx
        self.window.core.dispatcher.dispatch(event)

        # add ctx to DB
        self.window.core.ctx.add(ctx)
        self.window.controller.chat.output.append_input(ctx)

        # handle ctx name (generate title from summary if not initialized)
        if self.window.core.config.get('ctx.auto_summary'):
            self.window.controller.chat.output.handle_ctx_name(ctx)

        # process events to update UI
        QApplication.processEvents()

        # call DALL-E API and generate images
        try:
            # run async worker
            self.window.core.image.generate(ctx, text, model, num)

        except Exception as e:
            self.window.core.debug.log(e)
            self.window.ui.dialogs.alert(str(e))
            self.window.set_status(trans('status.error'))

        return ctx

    def handle_response(self, ctx, paths, prompt):
        """
        Handle response from DALL-E API

        :param ctx: ctx item
        :param paths: list with paths to downloaded images
        :param prompt: prompt used to generate images
        """
        string = ""
        i = 1
        for path in paths:
            string += "{}) `{}`".format(i, path) + "\n"
            i += 1
        self.open_images(paths)

        if not self.window.core.config.get('img_raw'):
            string += "\nPrompt: "
            string += prompt

        ctx.images = json.dumps(paths)  # save images paths
        ctx.set_output(string.strip())

        # dispatch event
        event = Event('ctx.after')
        event.ctx = ctx
        self.window.core.dispatcher.dispatch(event)

        # store last mode (in text mode this is handled in send_text)
        mode = self.window.core.config.get('mode')
        self.window.core.ctx.post_update(mode)  # post update context, store last mode, etc.

        self.window.controller.chat.output.append_output(ctx)
        self.window.core.ctx.store()
        self.window.set_status(trans('status.img.generated'))

        # update ctx in DB
        self.window.core.ctx.update_item(ctx)

        # update ctx list
        self.window.controller.ctx.update()

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
                self.window.core.debug.log(e)

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
            self.window.core.debug.log(e)

    def enable_raw(self):
        """Enable help for images"""
        self.window.core.config.set('img_raw', True)
        self.window.core.config.save()

    def disable_raw(self):
        """Disable help for images"""
        self.window.core.config.set('img_raw', False)
        self.window.core.config.save()

    def toggle_raw(self, state):
        """
        Toggle help for images

        :param state: state of checkbox
        """
        if not state:
            self.disable_raw()
        else:
            self.enable_raw()
