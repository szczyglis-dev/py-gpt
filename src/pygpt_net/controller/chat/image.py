#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.06 23:00:00                  #
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
        Image controller

        :param window: Window instance
        """
        self.window = window

    def send(self, text: str) -> CtxItem:
        """
        Send prompt for image generate

        :param text: prompt for image generation
        :return: ctx item
        """
        num = int(self.window.ui.config['global']['img_variants'].input.text() or 1)
        if num < 1:
            num = 1
        elif num > 4:
            num = 4

        # force one image if dall-e-3 model is used
        model = self.window.core.config.get('model')
        model_id = self.window.core.models.get_id(model)
        if model_id == 'dall-e-3':
            num = 1

        self.window.ui.status(trans('status.sending'))

        # create ctx item
        ctx = CtxItem()
        ctx.set_input(text, self.window.core.config.get('user_name'))

        # event: ctx.before
        event = Event('ctx.before')
        event.ctx = ctx
        self.window.core.dispatcher.dispatch(event)

        # add ctx to DB
        self.window.core.ctx.add(ctx)
        self.window.controller.chat.render.append_input(ctx)

        # process events to update UI
        QApplication.processEvents()

        # handle ctx name (generate title from summary if not initialized)
        if self.window.core.config.get('ctx.auto_summary'):
            self.window.controller.ctx.prepare_name(ctx)

        # call DALL-E API and generate images
        try:
            # run async worker
            self.window.core.image.generate(ctx, text, model_id, num)

        except Exception as e:
            self.window.core.debug.log(e)
            self.window.ui.dialogs.alert(str(e))
            self.window.ui.status(trans('status.error'))

        return ctx

    def handle_response(self, ctx: CtxItem, paths: list, prompt: str):
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
        self.open_images(paths)  # TODO: MAYBE DON'T OPEN IMAGES IN DIALOG, JUST APPEND TO CHAT ?

        if not self.window.core.config.get('img_raw'):
            string += "\nPrompt: "
            string += prompt

        ctx.images = paths  # save images paths
        ctx.set_output(string.strip())

        # event: ctx.after
        event = Event('ctx.after')
        event.ctx = ctx
        self.window.core.dispatcher.dispatch(event)

        # store last mode (in text mode this is handled in send_text)
        mode = self.window.core.config.get('mode')
        self.window.core.ctx.post_update(mode)  # post update context, store last mode, etc.

        self.window.controller.chat.render.append_output(ctx)
        self.window.core.ctx.store()  # save current ctx to DB
        self.window.ui.status(trans('status.img.generated'))

        # update ctx in DB
        self.window.core.ctx.update_item(ctx)

        # append extra output to chat
        self.window.controller.chat.render.append_extra(ctx)
        self.window.controller.chat.render.end_extra()

    def handle_response_inline(self, ctx: CtxItem, paths: list, prompt: str):
        """
        Handle inline response from DALL-E

        :param ctx: ctx item
        :param paths: list with paths to downloaded images
        :param prompt: prompt used to generate images
        """
        string = ""
        i = 1
        for path in paths:
            string += "{}) `{}`".format(i, path) + "\n"
            i += 1

        ctx.images = paths  # save images paths in ctx item here
        self.window.core.ctx.update_item(ctx)  # update in DB
        self.window.ui.status(trans('status.img.generated'))  # update status

        # WARNING:
        # if internal (sync) mode, then re-send OK status response, if not, append only img result
        # it will only inform system that image was generated, user will see it in chat with image after render
        # of ctx item (link to images are appended to ctx item)
        if ctx.internal:
            ctx.results.append({"request": {"cmd": "image"}, "result": "OK. Generated"})
            ctx.reply = True
            self.window.controller.chat.render.append_extra(ctx)  # show image first
            self.window.controller.chat.render.end_extra()
            self.window.core.dispatcher.reply(ctx)
            return

        # NOT internal-mode, user called, so append only img output to chat (show images now)
        self.window.controller.chat.render.append_extra(ctx)
        self.window.controller.chat.render.end_extra()

    def open_images(self, paths: list):
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

    def open(self, path: str):
        """
        Open image in default image viewer

        :param path: path to image
        """
        webbrowser.open(path)

    def open_dir(self, path: str):
        """
        Open image in default image viewer

        :param path: path to image
        """
        if os.path.exists(path):
            self.window.controller.files.open_in_file_manager(path)

    def save(self, path: str):
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
                self.window.ui.status(trans('status.img.saved'))
            except Exception as e:
                self.window.core.debug.log(e)

    def delete(self, path: str, force: bool = False):
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
