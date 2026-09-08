#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.04 13:00:00                  #
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
            "The image tool accepts an optional resolution and an optional reference_image path. "
            "When the user asks to edit, transform, extend, remix, refine, or otherwise modify a referenced image, "
            "pass that image path in reference_image. If the user explicitly requests image dimensions, pass them "
            "in resolution; it overrides the configured image resolution for that tool call when supported by the "
            "selected image model/provider. "
            "Generated images are attached to the chat automatically. Do not include or invent sandbox:, file://, "
            "or local filesystem image links/paths in the user-facing reply. "
            "After the image is generated, continue the conversation normally."
        )
        prompt_func = (
            "Generate an image requested by the user. Put a clear, detailed English image-generation prompt "
            "in the query parameter and preserve the user's intent. Optionally pass resolution to override the "
            "configured image size for this call. Optionally pass reference_image when editing/remixing an existing "
            "image; use the exact path supplied in the runtime image context. The generated image is attached to "
            "the chat automatically; do not expose sandbox:, file://, or local filesystem paths to the user."
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
                {
                    "name": "resolution",
                    "type": "str",
                    "description": (
                        "Optional output resolution, e.g. 1024x1024. Overrides the configured image resolution "
                        "for this tool call when supported by the selected image model/provider."
                    ),
                    "required": False,
                },
                {
                    "name": "reference_image",
                    "type": "str",
                    "description": (
                        "Optional local reference image path for edit/remix/extend operations. Use the exact path "
                        "provided in the runtime image context when the user refers to an attached or previously "
                        "generated image."
                    ),
                    "required": False,
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
