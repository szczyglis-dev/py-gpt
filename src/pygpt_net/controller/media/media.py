#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.12.25 20:00:00                  #
# ================================================== #

from typing import Any


class Media:
    def __init__(self, window=None):
        """
        Media (video, image, music) controller

        :param window: Window instance
        """
        self.window = window
        self.initialized = False

    def setup(self):
        """Setup UI"""
        # raw mode for images/video
        if self.window.core.config.get('img_raw'):
            self.window.ui.config['global']['img_raw'].setChecked(True)
        else:
            self.window.ui.config['global']['img_raw'].setChecked(False)

        # mode (image|video|music)
        mode = self.window.core.config.get('img_mode', 'image')
        self.window.controller.config.apply_value(
            parent_id="global",
            key="img_mode",
            option=self.window.core.image.get_mode_option(),
            value=mode,
        )

        # image: resolution
        resolution = self.window.core.config.get('img_resolution', '1024x1024')
        self.window.controller.config.apply_value(
            parent_id="global",
            key="img_resolution",
            option=self.window.core.image.get_resolution_option(),
            value=resolution,
        )

        # video: aspect ratio
        aspect_ratio = self.window.core.config.get('video.aspect_ratio', '16:9')
        self.window.controller.config.apply_value(
            parent_id="global",
            key="video.aspect_ratio",
            option=self.window.core.video.get_aspect_ratio_option(),
            value=aspect_ratio,
        )

        # -- add hooks --
        if not self.initialized:
            self.window.ui.add_hook("update.global.img_resolution", self.hook_update)
            self.window.ui.add_hook("update.global.img_mode", self.hook_update)
            self.window.ui.add_hook("update.global.video.aspect_ratio", self.hook_update)

    def reload(self):
        """Reload UI"""
        self.setup()

    def hook_update(self, key: str, value: Any, caller, *args, **kwargs):
        """
        Hook for updating media options

        :param key: config key
        :param value: new value
        :param caller: caller object
        """
        if key == "img_resolution":
            if not value:
                return
            self.window.core.config.set('img_resolution', value)
        elif key == "img_mode":
            if not value:
                return
            self.window.core.config.set('img_mode', value)
            self.window.controller.ui.mode.update() # switch image|video options
        elif key == "video.aspect_ratio":
            if not value:
                return
            self.window.core.config.set('video.aspect_ratio', value)

    def enable_raw(self):
        """Enable prompt enhancement for images"""
        self.window.core.config.set('img_raw', True)
        self.window.core.config.save()

    def disable_raw(self):
        """Disable prompt enhancement for media"""
        self.window.core.config.set('img_raw', False)
        self.window.core.config.save()

    def toggle_raw(self):
        """Save prompt enhancement option for media"""
        state = self.window.ui.config['global']['img_raw'].isChecked()
        if not state:
            self.disable_raw()
        else:
            self.enable_raw()

    def get_mode(self) -> str:
        """Get media generation mode (image/video/music)"""
        return self.window.core.config.get("img_mode", "image")

    def is_image_model(self) -> bool:
        """
        Check if the model is an image generation model

        :return: True if the model is an image generation model
        """
        current = self.window.core.config.get("model")
        model_data = self.window.core.models.get(current)
        if model_data:
            return model_data.is_image_output()

    def is_video_model(self) -> bool:
        """
        Check if the model is a video generation model

        :return: True if the model is a video generation model
        """
        current = self.window.core.config.get("model")
        model_data = self.window.core.models.get(current)
        if model_data:
            return model_data.is_video_output()

    def play_video(self, path: str):
        """
        Play video file

        :param path: path to video file
        """
        self.window.tools.get("player").play(path)