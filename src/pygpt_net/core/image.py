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

import datetime
import os
import requests
from PySide6.QtCore import QObject, Signal, QRunnable, Slot

from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class Image:
    DIRNAME = "img"

    def __init__(self, window=None):
        """
        Image generation core

        :param window: Window instance
        """
        self.window = window

    def install(self):
        """Install provider data"""
        img_dir = os.path.join(self.window.core.config.path, self.DIRNAME)
        if not os.path.exists(img_dir):
            os.mkdir(img_dir)

    def get_prompt(self, allow_custom: bool = True) -> str:
        """
        Return image generate prompt command

        :param allow_custom: allow custom prompt
        :return: system command for generate image prompt
        """
        cmd = '''
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
                    cmd = prompt
        return cmd

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
        self.window.controller.chat.image.handle_response_inline(ctx, paths, prompt)

    @Slot()
    def handle_status(self, msg: str):
        """Handle thread status"""
        self.window.ui.status(msg)
        print(msg)

    @Slot()
    def handle_error(self, e):
        """Handle thread error"""
        self.window.ui.status(e)
        self.window.core.debug.log(e)

    def generate(self, ctx: CtxItem, prompt: str, model: str = "dall-e-3", num: int = 1, inline: bool = False):
        """
        Call DALL-E API

        :param ctx: CtxItem
        :param prompt: prompt
        :param model: model name
        :param num: number of variants
        :param inline: inline mode
        :return: images paths list
        """

        # worker
        worker = ImageWorker()
        worker.window = self.window
        worker.client = self.window.core.gpt.get_client()
        worker.ctx = ctx
        worker.raw = self.window.core.config.get('img_raw')
        worker.model = model
        worker.model_prompt = self.window.core.config.get('img_prompt_model')
        worker.resolution = self.window.core.config.get('img_resolution')
        worker.dirname = self.DIRNAME
        worker.input_prompt = prompt
        worker.system_prompt = self.get_prompt()
        worker.num = num
        worker.inline = inline

        # signals
        worker.signals.finished.connect(self.handle_finished)
        worker.signals.finished_inline.connect(self.handle_finished_inline)
        worker.signals.status.connect(self.handle_status)
        worker.signals.error.connect(self.handle_error)

        # INTERNAL MODE (sync)
        # if internal (autonomous) call then use synchronous call
        if ctx.internal:
            worker.run()
            return

        # start
        self.window.threadpool.start(worker)


class ImageSignals(QObject):
    finished = Signal(object, object, object)
    finished_inline = Signal(object, object, object)
    status = Signal(object)
    error = Signal(object)


class ImageWorker(QRunnable):
    def __init__(self, *args, **kwargs):
        super(ImageWorker, self).__init__()
        self.signals = ImageSignals()
        self.args = args
        self.kwargs = kwargs
        self.window = None
        self.client = None
        self.ctx = None
        self.raw = False
        self.model = "dall-e-3"
        self.resolution = None
        self.dirname = None
        self.model_prompt = None
        self.input_prompt = None
        self.system_prompt = None
        self.inline = False
        self.num = 1

    @Slot()
    def run(self):
        if not self.raw and not self.inline:  # disable on inline and raw
            max_tokens = 200
            temperature = 1.0
            try:
                # call GPT for generate best image generate prompt
                self.signals.status.emit(trans('img.status.prompt.wait'))
                response = self.window.core.gpt.quick_call(self.input_prompt, self.system_prompt, False, max_tokens,
                                                           self.model_prompt, temperature)
                if response is not None and response != "":
                    self.input_prompt = response
            except Exception as e:
                self.signals.error.emit(e)
                self.signals.status.emit(trans('img.status.prompt.error') + ": " + str(e))

        self.signals.status.emit(trans('img.status.generating') + ": {}...".format(self.input_prompt))
        paths = []
        try:
            # send to API
            response = self.client.images.generate(
                model=self.model,
                prompt=self.input_prompt,
                n=self.num,
                size=self.window.core.config.get('img_resolution'),
            )

            # download images
            for i in range(self.num):
                if i >= len(response.data):
                    break
                url = response.data[i].url
                res = requests.get(url)

                # generate filename
                name = self.make_safe_filename(self.input_prompt) + "-" + datetime.date.today().strftime(
                    "%Y-%m-%d") + "_" + datetime.datetime.now().strftime("%H-%M-%S") + "-" + str(i + 1) + ".png"
                path = os.path.join(self.window.core.config.path, self.dirname, name)

                msg = trans('img.status.downloading') + " (" + str(i + 1) + " / " + str(self.num) + ") -> " + path
                self.signals.status.emit(msg)

                # save image
                if self.save_image(path, res.content):
                    paths.append(path)

            # send finished signal
            if self.inline:
                self.signals.finished_inline.emit(self.ctx, paths, self.input_prompt)
            else:
                self.signals.finished.emit(self.ctx, paths, self.input_prompt)

        except Exception as e:
            self.signals.error.emit(e)
            print(trans('img.status.error') + ": " + str(e))
            return

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
            self.signals.error.emit(e)
            print(trans('img.status.save.error') + ": " + str(e))
            return False

    def make_safe_filename(self, name: str) -> str:
        """
        Make safe filename

        :param name: filename to make safe
        :return: safe filename
        :rtype: str
        """

        def safe_char(c):
            if c.isalnum():
                return c
            else:
                return "_"

        return "".join(safe_char(c) for c in name).rstrip("_")[:30]
