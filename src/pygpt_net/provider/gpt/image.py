#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.30 15:00:00                  #
# ================================================== #

import datetime
import os
import requests
from PySide6.QtCore import QObject, Signal, QRunnable, Slot

from pygpt_net.core.bridge import BridgeContext
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class Image:
    def __init__(self, window=None):
        """
        Image generation core

        :param window: Window instance
        """
        self.window = window

    def generate(self, context: BridgeContext, extra: dict = None):
        """
        Call images API

        :param context: Bridge context
        :param extra: Extra arguments
        """
        prompt = context.prompt
        ctx = context.ctx
        model = context.model
        num = extra.get("num", 1)
        inline = extra.get("inline", False)

        if ctx is None:
            ctx = CtxItem()  # create empty context

        prompt_model = self.window.core.models.from_defaults()
        tmp_model = self.window.core.config.get('img_prompt_model')
        if self.window.core.models.has(tmp_model):
            prompt_model = self.window.core.models.get(tmp_model)

        # worker
        worker = ImageWorker()
        worker.window = self.window
        worker.client = self.window.core.gpt.get_client()
        worker.ctx = ctx
        worker.raw = self.window.core.config.get('img_raw')
        worker.model = model.id  # model ID for generate image, e.g. "dall-e-3"
        worker.model_prompt = prompt_model  # model for generate prompt, not image!
        worker.input_prompt = prompt
        worker.system_prompt = self.window.core.prompt.get('img')
        worker.num = num
        worker.inline = inline

        # config
        if self.window.core.config.has('img_quality'):
            worker.quality = self.window.core.config.get('img_quality')
        if self.window.core.config.has('img_resolution'):
            worker.resolution = self.window.core.config.get('img_resolution')

        # signals
        worker.signals.finished.connect(self.window.core.image.handle_finished)
        worker.signals.finished_inline.connect(self.window.core.image.handle_finished_inline)
        worker.signals.status.connect(self.window.core.image.handle_status)
        worker.signals.error.connect(self.window.core.image.handle_error)

        # check if async allowed
        if not self.window.core.dispatcher.async_allowed(ctx):
            worker.run()
            return

        # start
        self.window.threadpool.start(worker)


class ImageSignals(QObject):
    finished = Signal(object, object, object)  # ctx, paths, prompt
    finished_inline = Signal(object, object, object)  # ctx, paths, prompt
    status = Signal(object)  # status message
    error = Signal(object)  # error message


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
        self.quality = "standard"
        self.resolution = "1792x1024"
        self.model_prompt = None
        self.input_prompt = None
        self.system_prompt = None
        self.inline = False
        self.num = 1
        self.allowed_max_num = {
            "dall-e-2": 4,
            "dall-e-3": 1,
        }
        self.allowed_resolutions = {
            "dall-e-2": [
                "1024x1024",
                "512x512",
                "256x256",
            ],
            "dall-e-3": [
                "1792x1024",
                "1024x1792",
                "1024x1024",
            ],
        }

    @Slot()
    def run(self):
        """Run worker"""
        if not self.raw and not self.inline:  # disable on inline and raw modes
            try:
                # call GPT for generate better image generate prompt
                self.signals.status.emit(trans('img.status.prompt.wait'))
                bridge_context = BridgeContext(
                    prompt=self.input_prompt,
                    system_prompt=self.system_prompt,
                    model=self.model_prompt,  # model instance
                    max_tokens=200,
                    temperature=1.0,
                )
                response = self.window.core.bridge.quick_call(
                    context=bridge_context,
                )
                if response is not None and response != "":
                    self.input_prompt = response

            except Exception as e:
                self.signals.error.emit(e)
                self.signals.status.emit(trans('img.status.prompt.error') + ": " + str(e))

        self.signals.status.emit(trans('img.status.generating') + ": {}...".format(self.input_prompt))

        paths = []  # downloaded images paths

        try:
            # check if number of images is supported
            if self.model in self.allowed_max_num:
                if self.num > self.allowed_max_num[self.model]:
                    self.num = self.allowed_max_num[self.model]

            # check if resolution is supported
            resolution = self.resolution
            if self.model in self.allowed_resolutions:
                if resolution not in self.allowed_resolutions[self.model]:
                    resolution = self.allowed_resolutions[self.model][0]

            # send to API
            response = None
            if self.model == "dall-e-2":
                response = self.client.images.generate(
                    model=self.model,
                    prompt=self.input_prompt,
                    n=self.num,
                    size=resolution,
                )
            elif self.model == "dall-e-3":
                response = self.client.images.generate(
                    model=self.model,
                    prompt=self.input_prompt,
                    n=self.num,
                    quality=self.quality,
                    size=resolution,
                )

            # check response
            if response is None:
                self.signals.status.emit("API Error: empty response")
                return

            # download images
            for i in range(self.num):
                if i >= len(response.data):
                    break
                url = response.data[i].url
                res = requests.get(url)

                # generate filename
                name = datetime.date.today().strftime(
                    "%Y-%m-%d") + "_" + datetime.datetime.now().strftime("%H-%M-%S") + "-" \
                    + self.window.core.image.make_safe_filename(self.input_prompt) + "-" + str(i + 1) + ".png"
                path = os.path.join(self.window.core.config.get_user_dir("img"), name)

                msg = trans('img.status.downloading') + " (" + str(i + 1) + " / " + str(self.num) + ") -> " + str(path)
                self.signals.status.emit(msg)

                # save image
                if self.window.core.image.save_image(path, res.content):
                    paths.append(path)
                else:
                    self.signals.error.emit("Error saving image")

            # send finished signal
            if self.inline:
                self.signals.finished_inline.emit(  # separated signal for inline mode
                    self.ctx,
                    paths,
                    self.input_prompt,
                )
            else:
                self.signals.finished.emit(
                    self.ctx,
                    paths,
                    self.input_prompt,
                )

        except Exception as e:
            self.signals.error.emit(e)
            print(trans('img.status.error') + ": " + str(e))
            return
