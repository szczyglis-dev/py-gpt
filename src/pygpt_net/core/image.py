#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.26 18:00:00                  #
# ================================================== #

import os
from PySide6.QtCore import Slot

from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class Image:
    def __init__(self, window=None):
        """
        Image generation core

        :param window: Window instance
        """
        self.window = window

    def install(self):
        """Install provider data, img dir, etc."""
        img_dir = os.path.join(self.window.core.config.get_user_dir("img"))
        if not os.path.exists(img_dir):
            os.mkdir(img_dir)

    def get_prompt(self, allow_custom: bool = True) -> str:
        """
        Return image generate prompt command

        :param allow_custom: allow custom prompt
        :return: system command for generate image prompt
        """
        default = '''
        Whenever I provide a basic idea or concept for an image, such as 'a picture of mountains', 
        I want you to ALWAYS translate it into English and expand and elaborate on this idea. Use your knowledge and 
        creativity to add details that would make the image more vivid and interesting. This could include specifying 
        the time of day, weather conditions, surrounding environment, and any additional elements that could enhance 
        the scene. Your goal is to create a detailed and descriptive prompt that provides DALL-E with enough 
        information to generate a rich and visually appealing image. Remember to maintain the original intent of my 
        request while enriching the description with your imaginative details. '''

        # get custom prompt from config if exists
        if allow_custom:
            if self.window.core.config.has('img_prompt'):
                prompt = self.window.core.config.get('img_prompt')
                if prompt is not None and prompt != '':
                    default = prompt
        return default

    @Slot(str, object)
    def handle_finished(self, ctx: CtxItem, paths: list, prompt: str):
        """
        Handle finished image generation

        :param ctx: CtxItem
        :param paths: images paths list
        :param prompt: prompt used for generate images
        """
        self.window.controller.chat.image.handle_response(ctx, paths, prompt)

    @Slot(str, object)
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
