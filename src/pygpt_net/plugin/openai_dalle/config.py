#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.06.30 02:00:00                  #
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
        prompt = 'IMAGE GENERATION: Whenever I provide a basic idea or concept for an image, such as \'a picture of ' \
                 'mountains\', I want you to ALWAYS translate it into English and expand and elaborate on this idea. ' \
                 'Use your  knowledge and creativity to add details that would make the image more vivid and ' \
                 'interesting. This could include specifying the time of day, weather conditions, surrounding ' \
                 'environment, and any additional elements that could enhance the scene. Your goal is to create a ' \
                 'detailed and descriptive prompt that provides DALL-E  with enough information to generate a rich ' \
                 'and visually appealing image. Remember to maintain the original  intent of my request while ' \
                 'enriching the description with your imaginative details. HOW TO START IMAGE GENERATION: to start ' \
                 'image generation return to me prepared prompt in JSON format, all in one line,  using following ' \
                 'syntax: ~###~{"cmd": "image", "params": {"query": "your query here"}}~###~. Use ONLY this syntax ' \
                 'and remember to surround JSON string with ~###~. DO NOT use any other syntax. Use English in the ' \
                 'generated JSON command, but conduct all the remaining parts of the discussion with me in the ' \
                 'language in which I am speaking to you. The image will be generated on my machine  immediately ' \
                 'after the command is issued, allowing us to discuss the photo once it has been created.  Please ' \
                 'engage with me about the photo itself, not only by giving the generate command. '
        prompt_func = 'IMAGE GENERATION: Whenever I provide a basic idea or concept for an image, such as \'give me a picture of ' \
                      'mountains\', I want you to translate it into English and expand and elaborate on this idea. ' \
                      'Use your knowledge and creativity to add details that would make the image more vivid and ' \
                      'interesting. This could include specifying the time of day, weather conditions, surrounding ' \
                      'environment, and any additional elements that could enhance the scene. Your goal is to create a ' \
                      'detailed and descriptive prompt (query) that provides DALL-E with enough information to generate a rich ' \
                      'and visually appealing image. Use this command to start image generation. Use English in the image query.  ' \
                      'The image will be generated on my machine immediately after the command is issued, allowing us to ' \
                      'discuss the photo once it has been created. Please engage with me about the photo itself, not only by giving the generate command. '
        plugin.add_option(
            "model",
            type="combo",
            use="models",
            use_params={
                "mode": ["img"],
            },
            value="dall-e-3",
            label="Model",
            description="Model used for generating images, "
                        "default: dall-e-3",
            tooltip="Model",
        )
        plugin.add_cmd(
            "image",
            instruction=prompt_func,
            params=[
                {
                    "name": "query",
                    "type": "str",
                    "description": "image generation query (prompt for DALL-E)",
                    "required": True,
                },
            ],
            enabled=True,
            description="If enabled, DALL-E 3 image generation is available in chat.",
        )
        plugin.add_option(
            "prompt",
            type="textarea",
            value=prompt,
            label="Prompt",
            description="Prompt used for generating a query for DALL-E in background.",
            tooltip="Prompt",
            advanced=False,
        )