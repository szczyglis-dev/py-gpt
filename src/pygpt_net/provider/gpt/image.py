#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.06.30 18:00:00                  #
# ================================================== #

import base64
import datetime
import os
from typing import Optional, Dict, Any

import requests

from PySide6.QtCore import QObject, Signal, QRunnable, Slot

from pygpt_net.core.events import KernelEvent
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class Image:

    MODE_GENERATE = "generate"
    MODE_EDIT = "edit"

    def __init__(self, window=None):
        """
        Image generation core

        :param window: Window instance
        """
        self.window = window
        self.worker = None

    def generate(
            self,
            context: BridgeContext,
            extra: Optional[Dict[str, Any]] = None,
            sync: bool = True
    ):
        """
        Call images API

        :param context: Bridge context
        :param extra: Extra arguments
        :param sync: Synchronous mode
        """
        prompt = context.prompt
        ctx = context.ctx
        model = context.model
        num = extra.get("num", 1)
        inline = extra.get("inline", False)
        sub_mode = self.MODE_GENERATE

        # if attachments then switch mode to EDIT
        attachments = context.attachments
        if attachments and len(attachments) > 0:
            sub_mode = self.MODE_EDIT

        if ctx is None:
            ctx = CtxItem()  # create empty context

        prompt_model = self.window.core.models.from_defaults()
        tmp_model = self.window.core.config.get('img_prompt_model')
        if self.window.core.models.has(tmp_model):
            prompt_model = self.window.core.models.get(tmp_model)

        # worker
        self.worker = ImageWorker()
        self.worker.window = self.window
        self.worker.client = self.window.core.gpt.get_client()
        self.worker.ctx = ctx
        self.worker.mode = sub_mode  # mode can be "generate" or "edit"
        self.worker.attachments = attachments  # attachments for edit mode
        self.worker.raw = self.window.core.config.get('img_raw')
        self.worker.model = model.id  # model ID for generate image, e.g. "dall-e-3"
        self.worker.model_prompt = prompt_model  # model for generate prompt, not image!
        self.worker.input_prompt = prompt
        self.worker.system_prompt = self.window.core.prompt.get('img')
        self.worker.num = num
        self.worker.inline = inline

        # config
        if self.window.core.config.has('img_quality'):
            self.worker.quality = self.window.core.config.get('img_quality')
        if self.window.core.config.has('img_resolution'):
            self.worker.resolution = self.window.core.config.get('img_resolution')

        # signals
        self.worker.signals.finished.connect(self.window.core.image.handle_finished)
        self.worker.signals.finished_inline.connect(self.window.core.image.handle_finished_inline)
        self.worker.signals.status.connect(self.window.core.image.handle_status)
        self.worker.signals.error.connect(self.window.core.image.handle_error)

        # sync
        if sync:
            self.worker.run()
            return True

        # check if async allowed
        if not self.window.controller.kernel.async_allowed(ctx):
            self.worker.run()
            return True

        # start
        self.window.dispatch(KernelEvent(KernelEvent.STATE_BUSY, {
            "id": "img",
        }))
        self.window.threadpool.start(self.worker)
        return True


class ImageSignals(QObject):
    finished = Signal(object, list, str)  # ctx, paths, prompt
    finished_inline = Signal(object, list, str)  # ctx, paths, prompt
    status = Signal(object)  # status message
    error = Signal(object)  # error message


class ImageWorker(QObject, QRunnable):
    def __init__(self, *args, **kwargs):
        QObject.__init__(self)
        QRunnable.__init__(self)
        self.signals = ImageSignals()
        self.args = args
        self.kwargs = kwargs
        self.window = None
        self.client = None
        self.ctx = None
        self.raw = False
        self.mode = Image.MODE_GENERATE  # default mode is generate
        self.model = "dall-e-3"
        self.quality = "standard"
        self.resolution = "1792x1024"
        self.attachments = {}  # attachments for edit mode
        self.model_prompt = None
        self.input_prompt = None
        self.system_prompt = None
        self.inline = False
        self.num = 1
        self.allowed_max_num = {
            "dall-e-2": 4,
            "dall-e-3": 1,
            "gpt-image-1": 1,
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
            "gpt-image-1": [
                "1536x1024",
                "1024x1536",
                "1024x1024",
                "auto",
            ],
        }
        self.allowed_quality = {
            "dall-e-2": [
                "standard",
            ],
            "dall-e-3": [
                "standard",
                "hd",
            ],
            "gpt-image-1": [
                "auto",
                "high",
                "medium",
                "low",
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
                event = KernelEvent(KernelEvent.CALL, {
                    'context': bridge_context,
                    'extra': {},
                })
                self.window.dispatch(event)
                response = event.data.get('response')
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

            quality = self.quality
            if self.model in self.allowed_quality:
                if quality not in self.allowed_quality[self.model]:
                    quality = self.allowed_quality[self.model][0]

            # send to API
            response = None
            if self.mode == Image.MODE_GENERATE:
                if self.model == "dall-e-2":
                    response = self.client.images.generate(
                        model=self.model,
                        prompt=self.input_prompt,
                        n=self.num,
                        size=resolution,
                    )
                elif self.model == "dall-e-3" or self.model == "gpt-image-1":
                    response = self.client.images.generate(
                        model=self.model,
                        prompt=self.input_prompt,
                        n=self.num,
                        quality=quality,
                        size=resolution,
                    )
            elif self.mode == Image.MODE_EDIT:
                images = []
                for uuid in self.attachments:
                    attachment = self.attachments[uuid]
                    if attachment.path and os.path.exists(attachment.path):
                        images.append(open(attachment.path, "rb"))
                response = self.client.images.edit(
                    model=self.model,
                    image=images,
                    prompt=self.input_prompt,
                )

            # check response
            if response is None:
                self.signals.status.emit("API Error: empty response")
                return

            # download images
            for i in range(self.num):
                if i >= len(response.data):
                    break

                # generate filename
                name = datetime.date.today().strftime(
                    "%Y-%m-%d") + "_" + datetime.datetime.now().strftime("%H-%M-%S") + "-" \
                       + self.window.core.image.make_safe_filename(self.input_prompt) + "-" + str(i + 1) + ".png"
                path = os.path.join(self.window.core.config.get_user_dir("img"), name)

                msg = trans('img.status.downloading') + " (" + str(i + 1) + " / " + str(self.num) + ") -> " + str(path)
                self.signals.status.emit(msg)

                if response.data[i] is None:
                    self.signals.error.emit("API Error: empty image data")
                    return
                if response.data[i].url:  # dall-e 2 and 3 returns URL
                    res = requests.get(response.data[i].url)
                    data = res.content
                else:  # gpt-image-1 returns base64 encoded image
                    data = base64.b64decode(response.data[i].b64_json)

                # save image
                if data and self.window.core.image.save_image(path, data):
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
