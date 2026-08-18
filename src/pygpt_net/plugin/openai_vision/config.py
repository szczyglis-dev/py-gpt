#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.08.18 17:30:00                  #
# ================================================== #

from pygpt_net.plugin.base.config import BaseConfig, BasePlugin


class Config(BaseConfig):
    def __init__(self, plugin: BasePlugin = None, *args, **kwargs):
        super(Config, self).__init__(plugin)
        self.plugin = plugin

    def from_defaults(self, plugin: BasePlugin = None):
        """
        Set default options for plugin

        :param plugin: plugin instance
        """
        prompt = "IMAGE ANALYSIS: You are an expert in analyzing photos. Each time I send you a photo, you will " \
                 "analyze it as accurately as you can, answer all my questions, and offer any help on the subject " \
                 "related to the photo.  Remember to always describe in great detail all the aspects related to the " \
                 "photo, try to place them in the context of the conversation, and make a full analysis of what you " \
                 "see. "
        plugin.add_option(
            "model",
            type="combo",
            use="models",
            use_params={
                "mode": ["chat"],
                "input": ["image"],
            },
            value="gpt-4o",
            label="Model",
            description="Image-capable Chat model used temporarily for vision analysis. "
                        "It can use any supported provider; default: gpt-4o",
            tooltip="Model",
        )
        plugin.add_option(
            "prompt",
            type="textarea",
            value=prompt,
            label="Prompt",
            description="Prompt used for inline image analysis. It can append to or replace the current "
                        "system prompt while the temporary image-capable model is used in Chat mode",
            tooltip="Prompt",
            advanced=True,
        )
        plugin.add_option(
            "replace_prompt",
            type="bool",
            value=False,
            label="Replace prompt",
            description="Replace the whole system prompt with the image-analysis prompt instead of appending "
                        "it to the current prompt",
            tooltip="Replace the whole system prompt with the image-analysis prompt instead of appending it to the "
                    "current prompt",
            advanced=True,
        )
        plugin.add_cmd(
            "analyze_image_attachment",
            instruction="send the user's image to the configured image-capable model and request an image analysis. Use this function whenever the user asks for an analysis of a given image. The image will be automatically attached during execution.",
            params=[
                {
                    "name": "prompt",
                    "type": "str",
                    "description": "prompt with instructions for image analysis",
                    "required": True,
                },
                {
                    "name": "path",
                    "type": "str",
                    "description": "path to image, if not provided then current image will be used",
                    "required": False,
                },
            ],
            enabled=True,
        )
        plugin.add_cmd(
            "analyze_screenshot",
            instruction="make a screenshot and send it to the configured image-capable model for analysis",
            params=[
                {
                    "name": "prompt",
                    "type": "str",
                    "description": "prompt with instructions for image analysis",
                    "required": True,
                },
            ],
            enabled=True,
        )
        plugin.add_cmd(
            "analyze_camera_capture",
            instruction="capture an image from the camera and send it to the configured image-capable model for analysis",
            params=[
                {
                    "name": "prompt",
                    "type": "str",
                    "description": "prompt with instructions for image analysis",
                    "required": True,
                },
            ],
            enabled=True,
        )
        plugin.add_cmd(
            "camera_capture",
            instruction="capture image from webcam",
            params=[],
            enabled=True,
        )
        plugin.add_cmd(
            "make_screenshot",
            instruction="make desktop screenshot",
            params=[],
            enabled=True,
        )