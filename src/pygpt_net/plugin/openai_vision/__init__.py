#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.31 22:00:00                  #
# ================================================== #

from pygpt_net.plugin.base import BasePlugin
from pygpt_net.core.dispatcher import Event


class Plugin(BasePlugin):
    def __init__(self):
        super(Plugin, self).__init__()
        self.id = "openai_vision"
        self.name = "GPT-4 Vision (inline, for use in any chat)"
        self.type = ['vision']
        self.description = "Integrates GPT-4 Vision abilities with any chat mode"
        self.window = None
        self.order = 100
        self.use_locale = True
        self.is_vision = False
        self.init_options()

    def init_options(self):
        self.add_option("model", "text", 'gpt-4-vision-preview',
                        "Model",
                        "Model used to temporarily providing vision abilities, default: gpt-4-vision-preview",
                        tooltip="Model")
        self.add_option("keep", "bool", True,
                        "Keep vision",
                        "Keep vision model after image or capture detection",
                        tooltip="Keep vision model after image or capture detection")

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

    def handle(self, event: Event, *args, **kwargs):
        """
        Handle dispatched event

        :param event: event object
        """
        name = event.name
        data = event.data

        if name == 'mode.before':
            data['value'] = self.on_mode_before(data['value'], data['prompt'])  # handle mode change
        if name == 'model.before':
            mode = data['mode']
            if mode == 'vision':
                data['model'] = self.get_option_value("model")  # force choose correct vision model
        elif name == 'ui.vision':
            data['value'] = True  # allow render vision UI elements
        elif name == 'ui.attachments':
            data['value'] = True  # allow render attachments UI elements
        elif name == 'ctx.select' or name == 'mode.select' or name == 'model.select':
            self.is_vision = False  # reset vision flag

    def log(self, msg: str):
        """
        Log message to console

        :param msg: message to log
        """
        full_msg = '[Vision] ' + str(msg)
        self.debug(full_msg)
        self.window.ui.status(full_msg)
        print(full_msg)

    def on_mode_before(self, mode: str, prompt: str):
        """
        Event: On before mode execution

        :param mode: current mode
        :param prompt: current prompt
        :return: updated mode
        """
        # abort if already in vision mode
        if mode == 'vision':
            return mode  # keep current mode

        if self.is_vision and self.get_option_value("keep"):  # if already used in this ctx then keep vision mode
            return 'vision'

        # check for attachments
        attachments = self.window.core.attachments.get_all(mode)
        self.window.core.gpt.vision.build_content(prompt, attachments)  # tmp build content

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
            self.is_vision = True  # set vision flag
            return 'vision'  # jump to vision mode (only for this call)

        return mode  # keep current mode
