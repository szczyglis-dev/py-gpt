#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.14 01:00:00                  #
# ================================================== #

import os

from PySide6.QtCore import Slot, QObject

from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class Image(QObject):
    def __init__(self, window=None):
        """
        Image generation core

        :param window: Window instance
        """
        super().__init__()
        self.window = window

    def install(self):
        """Install provider data, img dir, etc."""
        img_dir = os.path.join(self.window.core.config.get_user_dir("img"))
        if not os.path.exists(img_dir):
            os.makedirs(img_dir, exist_ok=True)

    @Slot(object, list, str)
    def handle_finished(self, ctx: CtxItem, paths: list, prompt: str):
        """
        Handle finished image generation

        :param ctx: CtxItem
        :param paths: images paths list
        :param prompt: prompt used for generate images
        """
        self.window.controller.chat.image.handle_response(ctx, paths, prompt)

    @Slot(object, list, str)
    def handle_finished_inline(self, ctx: CtxItem, paths: list, prompt: str):
        """
        Handle finished image generation

        :param ctx: CtxItem
        :param paths: images paths list
        :param prompt: prompt used for generate images
        """
        self.window.controller.chat.image.handle_response_inline(
            ctx,
            paths,
            prompt,
        )

    @Slot()
    def handle_status(self, msg: str):
        """
        Handle thread status message

        :param msg: status message
        """
        self.window.ui.status(msg)

        is_log = False
        if self.window.core.config.has("log.dalle") \
                and self.window.core.config.get("log.dalle"):
            is_log = True
        self.window.core.debug.info(msg, not is_log)
        if is_log:
            print(msg)

    @Slot()
    def handle_error(self, msg: any):
        """
        Handle thread error message

        :param msg: error message
        """
        self.window.ui.status(msg)
        self.window.core.debug.log(msg)

    def save_image(self, path: str, image: any) -> bool:
        """
        Save image to file

        :param path: path to save
        :param image: image data
        :return: True if success
        """
        try:
            with open(path, 'wb') as file:
                file.write(image)
            return True
        except Exception as e:
            print(trans('img.status.save.error') + ": " + str(e))
            return False

    def make_safe_filename(self, name: str) -> str:
        """
        Make safe filename

        :param name: filename to make safe
        :return: safe filename
        """
        def safe_char(c):
            if c.isalnum():
                return c
            else:
                return "_"
        return "".join(safe_char(c) for c in name).rstrip("_")[:30]
