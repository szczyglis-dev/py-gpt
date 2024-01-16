#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.16 04:00:00                  #
# ================================================== #

from pygpt_net.item.ctx import CtxItem
from pygpt_net.plugin.base import BasePlugin
from pygpt_net.core.dispatcher import Event


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "openai_vision"
        self.name = "GPT-4 Vision (inline, for use in any chat)"
        self.type = ['vision']
        self.description = "Integrates GPT-4 Vision abilities with any chat mode"
        self.order = 100
        self.use_locale = True
        self.init_options()

    def init_options(self):
        self.add_option("model", "text", 'gpt-4-vision-preview',
                        "Model",
                        "Model used to temporarily providing vision abilities, default: gpt-4-vision-preview",
                        tooltip="Model")

        prompt = "IMAGE ANALYSIS: You are an expert in analyzing photos. Each time I send you a photo, you will " \
                 "analyze it as accurately as you can, answer all my questions, and offer any help on the subject " \
                 "related to the photo.  Remember to always describe in great detail all the aspects related to the " \
                 "photo, try to place them in the context of the conversation, and make a full analysis of what you " \
                 "see. "
        self.add_option("prompt", "textarea", prompt,
                        "Prompt",
                        "Prompt used for vision mode. It will append or replace current system prompt when using "
                        "vision model",
                        tooltip="Prompt", advanced=False)

        self.add_option("replace_prompt", "bool", False,
                        "Replace prompt",
                        "Replace whole system prompt with vision prompt against appending it to the current prompt",
                        tooltip="Replace whole system prompt with vision prompt against appending it to the current "
                                "prompt")

    def setup(self) -> dict:
        """
        Return available config options

        :return: config options
        """
        return self.options

    def attach(self, window):
        """
        Attach window

        :param window: Window instance
        """
        self.window = window

    def is_allowed(self, mode: str) -> bool:
        """
        Check if plugin is allowed in given mode

        :param mode: mode name
        :return: True if allowed, False otherwise
        """
        return mode in self.window.controller.chat.vision.allowed_modes

    def handle(self, event: Event, *args, **kwargs):
        """
        Handle dispatched event

        :param event: event object
        """
        name = event.name
        data = event.data
        ctx = event.ctx

        if name == 'mode.before':
            if self.is_allowed(data['value']):
                data['value'] = self.on_mode_before(ctx, data['value'], data['prompt'])  # handle mode change
        elif name == 'model.before':
            if "mode" in data and data["mode"] == "vision":
                data['model'] = self.get_option_value("model")
        elif name == 'pre.prompt':
            if self.is_allowed(data['mode']):
                data['value'] = self.on_pre_prompt(data['value'])
        elif name == 'system.prompt':
            if self.is_allowed(data['mode']):
                data['value'] = self.on_system_prompt(data['value'])
        elif name == 'ui.attachments':
            data['value'] = True  # allow render attachments UI elements
        elif name == 'ui.vision':
            if self.is_allowed(data['mode']):
                data['value'] = True  # allow render vision UI elements
        elif name == 'ctx.select' or name == 'mode.select' or name == 'model.select':
            self.on_toggle(False)  # always reset vision flag / disable vision mode

    def log(self, msg: str):
        """
        Log message to console

        :param msg: message to log
        """
        full_msg = '[Vision] ' + str(msg)
        self.debug(full_msg)
        self.window.ui.status(full_msg)
        print(full_msg)

    def on_toggle(self, value: bool):
        """
        Event: On toggle vision mode

        :param value: vision mode value
        """
        if not value:
            self.window.controller.chat.vision.is_enabled = False

    def on_system_prompt(self, prompt: str):
        """
        Event: On prepare system prompt

        :param prompt: prompt
        :return: updated prompt
        """
        # append vision prompt only if vision is provided or enabled
        if not self.is_vision_provided() and not self.window.controller.chat.vision.enabled():
            return prompt

        # append vision prompt
        if not self.get_option_value("replace_prompt"):
            prompt += "\n" + self.get_option_value("prompt")
        return prompt

    def on_pre_prompt(self, prompt: str):
        """
        Event: On pre-prepare system prompt

        :param prompt: prompt
        :return: updated prompt
        """
        # append vision prompt only if vision is provided or enabled
        if not self.is_vision_provided() and not self.window.controller.chat.vision.enabled():
            return prompt

        # replace vision prompt
        if self.get_option_value("replace_prompt"):
            return self.get_option_value("prompt")
        else:
            return prompt

    def is_vision_provided(self) -> bool:
        """
        Check if vision is provided (images, attachments)

        :return: True if vision is provided in this ctx
        """
        result = False
        mode = self.window.core.config.get('mode')
        attachments = self.window.core.attachments.get_all(mode)
        self.window.core.gpt.vision.build_content("", attachments)  # tmp build content

        built_attachments = self.window.core.gpt.vision.attachments
        built_urls = self.window.core.gpt.vision.urls

        # check for images in URLs
        img_ext = ['.jpg', '.png', '.jpeg', '.gif', '.webp']
        img_urls = []
        for url in built_urls:
            for ext in img_ext:
                if url.lower().endswith(ext):
                    img_urls.append(url)
                    break

        if len(built_attachments) > 0 or len(img_urls) > 0:
            result = True

        return result

    def on_mode_before(self, ctx: CtxItem, mode: str, prompt: str):
        """
        Event: On before mode execution

        :param ctx: current ctx
        :param mode: current mode
        :param prompt: current prompt
        :return: updated mode
        """
        # abort if already in vision mode
        if mode == 'vision':
            return mode  # keep current mode

        # if already used in this ctx then keep vision mode
        if self.window.controller.chat.vision.enabled():
            ctx.is_vision = True
            return 'vision'

        if self.is_vision_provided():
            self.window.controller.chat.vision.enable()
            ctx.is_vision = True
            return 'vision'  # jump to vision mode (only for this call)

        return mode  # keep current mode
