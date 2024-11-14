#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.14 01:00:00                  #
# ================================================== #

from pygpt_net.core.bridge import BridgeContext
from pygpt_net.item.model import ModelItem
from pygpt_net.plugin.base import BasePlugin
from pygpt_net.core.dispatcher import Event
from pygpt_net.item.ctx import CtxItem


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "openai_dalle"
        self.name = "DALL-E 3: Image generation"
        self.description = "Integrates DALL-E 3 image generation with any chat"
        self.type = [
            "cmd.inline",
        ]
        self.allowed_modes = [
            "chat",
            "langchain",
            "vision",
            "llama_index",
            "assistant",
            "agent",
        ]
        self.allowed_cmds = [
            "image",
        ]
        self.order = 100
        self.use_locale = True
        self.init_options()

    def init_options(self):
        """Initialize options"""
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
        self.add_cmd(
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
        self.add_option(
            "prompt",
            type="textarea",
            value=prompt,
            label="Prompt",
            description="Prompt used for generating a query for DALL-E in background.",
            tooltip="Prompt",
            advanced=False,
        )

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
        :param args: args
        :param kwargs: kwargs
        """
        name = event.name
        data = event.data
        ctx = event.ctx

        if name == Event.SYSTEM_PROMPT:
            if self.is_native_cmd():  # only if native commands are disabled, otherwise use commands only
                return

            mode = ""
            if "mode" in data:
                mode = data["mode"]
            if mode not in self.allowed_modes:
                return
            data['value'] = self.on_system_prompt(data['value'])

        elif name in [
            Event.CMD_SYNTAX_INLINE,  # inline is allowed
            Event.CMD_SYNTAX,
        ]:
            if not self.is_native_cmd():  # only if native commands are enabled, otherwise use prompt only
                return

            self.cmd_syntax(data)

        elif name in [
            Event.CMD_INLINE,
            Event.CMD_EXECUTE,
        ]:
            self.cmd(
                ctx,
                data['commands'],
            )

    def cmd_syntax(self, data: dict):
        """
        Event: CMD_SYNTAX or CMD_SYNTAX_INLINE

        :param data: event data dict
        """
        for option in self.allowed_cmds:
            if not self.has_cmd(option):
                continue
            data['cmd'].append(self.get_cmd(option))  # append command

    def on_system_prompt(self, prompt: str) -> str:
        """
        Event: SYSTEM_PROMPT

        :param prompt: prompt
        :return: updated prompt
        """
        prompt += "\n" + self.get_option_value("prompt")
        return prompt

    def cmd(self, ctx: CtxItem, cmds: list):
        """
        Events: CMD_INLINE, CMD_EXECUTE

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
                    # if internal call (ctx.internal = True), then re-send OK response
                    # if not internal call, then append image to chat only
                    model = ModelItem()
                    model.id = "dall-e-3"
                    bridge_context = BridgeContext(
                        ctx=ctx,
                        mode="image",
                        model=model,  # model instance
                        prompt=query,
                    )
                    extra = {
                        "num": 1,  # force 1 image if dall-e-3 model is used
                        "inline": True, # force inline mode
                    }
                    sync = False
                    if self.window.core.config.get("mode") == "agent_llama":
                        sync = True
                    self.window.core.gpt.image.generate(bridge_context, extra, sync)  # force inline mode, async call
            except Exception as e:
                self.log("Error: " + str(e))
                return

    def log(self, msg: str):
        """
        Log message to console

        :param msg: message to log
        """
        if self.is_threaded():
            return
        full_msg = '[DALL-E] ' + str(msg)
        self.debug(full_msg)
        self.window.ui.status(full_msg)
        if self.is_log():
            print(full_msg)
