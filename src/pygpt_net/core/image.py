#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.29 21:00:00                  #
# ================================================== #

import datetime
import os
import requests
from PySide6.QtCore import QObject, Signal, QRunnable, Slot

from pygpt_net.utils import trans


class Image:
    DIRNAME = "img"

    def __init__(self, window=None):
        """
        DALL-E Wrapper

        :param window: Window instance
        """
        self.window = window

    def install(self):
        """Install provider data"""
        img_dir = os.path.join(self.window.core.config.path, self.DIRNAME)
        if not os.path.exists(img_dir):
            os.mkdir(img_dir)

    def get_prompt(self, allow_custom=True):
        """
        Return image generate prompt command

        :param allow_custom: allow custom prompt
        :return: system command for generate image prompt
        """
        cmd = '''
        1. Apply these rules if the request is related to image generation or image description; otherwise, return the user's prompt as is.
        2. Translate any non-English image prompts accurately into English.
        3. Start from "A photograph of..." or "An image of...", etc. DO NOT use asking, like "Please generate...", "I want to see...", etc.
        4. Use as many details as possible to describe the image.
        5. If the user only wants to talk, then return the user's prompt as is (AND ONLY their prompt, without adding any text to it).
        '''
        # get custom prompt from config if exists
        if allow_custom:
            if self.window.core.config.has('img_prompt'):
                prompt = self.window.core.config.get('img_prompt')
                if prompt is not None and prompt != '':
                    cmd = prompt
        return cmd

    @Slot(str, object)
    def handle_finished(self, ctx, paths, prompt):
        """
        Handle finished image generation

        :param ctx: CtxItem
        :param paths: images paths list
        :param prompt: prompt used for generate images
        """
        self.window.controller.chat.image.handle_response(ctx, paths, prompt)

    @Slot()
    def handle_status(self, msg):
        """Handle thread status"""
        self.window.set_status(msg)
        print(msg)

    @Slot()
    def handle_error(self, e):
        """Handle thread error"""
        self.window.set_status(e)
        self.window.core.debug.log(e)

    def generate(self, ctx, prompt, model="dall-e-3", num=1):
        """
        Call DALL-E API

        :param ctx: CtxItem
        :param prompt: prompt
        :param model: model name
        :param num: number of variants
        :return: images paths list
        :rtype: list
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

        # signals
        worker.signals.finished.connect(self.handle_finished)
        worker.signals.status.connect(self.handle_status)
        worker.signals.error.connect(self.handle_error)

        # start
        self.window.threadpool.start(worker)


class ImageSignals(QObject):
    finished = Signal(object, object, object)
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
        self.num = 1

    @Slot()
    def run(self):
        if not self.raw:
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
            self.signals.finished.emit(self.ctx, paths, self.input_prompt)

        except Exception as e:
            self.signals.error.emit(e)
            print(trans('img.status.error') + ": " + str(e))
            return

    def save_image(self, path, image):
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

    def make_safe_filename(self, name):
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
