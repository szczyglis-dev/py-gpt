#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.31 04:00:00                  #
# ================================================== #

from pygpt_net.plugin.base import BasePlugin
from pygpt_net.core.dispatcher import Event
from pygpt_net.item.ctx import CtxItem


class Plugin(BasePlugin):
    def __init__(self):
        super(Plugin, self).__init__()
        self.id = "openai_dalle"
        self.name = "DALL-E 3: Image generation"
        self.description = "Integrates DALL-E 3 image generation with any chat"
        self.allowed_cmds = [
            "image"
        ]
        self.window = None
        self.order = 100
        self.use_locale = True
        self.init_options()

    def init_options(self):
        """Initialize options"""
        prompt = """IMAGE GENERATION: Whenever I provide a basic idea or concept for an image, such as 'a picture of 
        mountains', I want you to ALWAYS translate it into English and expand and elaborate on this idea. Use your 
        knowledge and creativity to add details that would make the image more vivid and interesting. This could 
        include specifying the time of day, weather conditions, surrounding environment, and any additional elements 
        that could enhance the scene. Your goal is to create a detailed and descriptive prompt that provides DALL-E 
        with enough information to generate a rich and visually appealing image. Remember to maintain the original 
        intent of my request while enriching the description with your imaginative details. HOW TO START IMAGE 
        GENARATION: to start image generation return to me prepared prompt in JSON format, all in one line, 
        using following syntax: # ~###~{"cmd": "image", "params": {"query": "your query here"}}~###~. Use ONLY this 
        syntax and remember to surround JSON string with ~###~ and start command with single # - like comment in code. 
        DO NOT use any other syntax. Use English in the generated JSON command, but conduct all the remaining parts 
        of the discussion with me in the language in which I am speaking to you. The image will be generated on my machine 
        immediately after the command is issued, allowing us to discuss the photo once it has been created. 
        Please engage with me about the photo itself, not only by giving the generate command.
        """
        self.add_option("prompt", "textarea", prompt,
                        "Prompt",
                        "Prompt used for generating a query for DALL-E in background - please DO NOT EDIT if you do "
                        "not know what you are doing.",
                        tooltip="Prompt", advanced=True)

    def setup(self):
        """
        Return available config options

        :return: config options
        :rtype: dict
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
        ctx = event.ctx

        if name == 'system.prompt':
            data['value'] = self.on_system_prompt(data['value'])
        elif name == 'cmd.only':
            self.cmd(ctx, data['commands'])

    def log(self, msg: str):
        """
        Log message to console

        :param msg: message to log
        """
        full_msg = '[CMD] ' + str(msg)
        self.debug(full_msg)
        self.window.ui.status(full_msg)
        print(full_msg)

    def on_system_prompt(self, prompt: str, silent: bool = False):
        """
        Event: On prepare system prompt

        :param prompt: prompt
        :param silent: silent mode
        :return: updated prompt
        :rtype: str
        """
        prompt += self.get_option_value("prompt")
        return prompt

    def cmd(self, ctx: CtxItem, cmds: list):
        """
        Event: On command

        :param ctx: CtxItem
        :param cmds: commands dict
        """
        is_cmd = False
        my_commands = []
        for item in cmds:
            if item["cmd"] in self.allowed_cmds:
                my_commands.append(item)
                is_cmd = True

        if not is_cmd:
            return

        for item in my_commands:
            try:
                if item["cmd"] == "image":
                    query = item["params"]["query"]
                    self.window.core.image.generate(ctx, query, 'dall-e-3', 1, inline=True)
            except Exception as e:
                self.log("Error: " + str(e))
                return
