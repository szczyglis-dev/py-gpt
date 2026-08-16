#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.08.16 18:20:00                  #
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
        prompt = (
            "IMAGE GENERATION: When the user asks to create or generate an image, use the image tool. "
            "Write the image query in English as a clear, detailed prompt that preserves the user's intent. "
            "After the image is generated, continue the conversation normally."
        )
        prompt_func = (
            "Generate an image requested by the user. Put a clear, detailed English image-generation prompt "
            "in the query parameter and preserve the user's intent."
        )
        plugin.add_option(
            "model",
            type="combo",
            use="models",
            use_params={
                "mode": ["img"],
            },
            value="gpt-image-1",
            label="Model",
            description="Image generation model, default: gpt-image-1",
            tooltip="Model",
        )
        plugin.add_cmd(
            "image",
            instruction=prompt_func,
            params=[
                {
                    "name": "query",
                    "type": "str",
                    "description": "Prompt describing the image to generate",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable image generation in chat.",
        )
        plugin.add_option(
            "prompt",
            type="textarea",
            value=prompt,
            label="Prompt",
            description="Image generation instructions appended to the system prompt.",
            tooltip="Prompt",
            advanced=False,
        )
        plugin.add_option(
            "append_prompt",
            type="bool",
            value=True,
            label="Append image prompt to system prompt",
            description="Append image generation instructions to the system prompt.",
            advanced=False,
        )
