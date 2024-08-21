#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.22 00:00:00                  #
# ================================================== #

from pygpt_net.item.ctx import CtxItem
from pygpt_net.plugin.base import BasePlugin
from pygpt_net.core.dispatcher import Event


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "openai_vision"
        self.name = "GPT-4 Vision (inline)"
        self.type = [
            "vision",
            "cmd.inline",
        ]
        self.description = "Integrates GPT-4 Vision abilities with any chat mode"
        self.order = 100
        self.use_locale = True
        self.prompt = ""
        self.allowed_urls_ext = [
            ".jpg",
            ".png",
            ".jpeg",
            ".gif",
            ".webp",
        ]
        self.allowed_cmds = [
            "camera_capture",
            "make_screenshot",
        ]
        self.init_options()

    def init_options(self):
        prompt = "IMAGE ANALYSIS: You are an expert in analyzing photos. Each time I send you a photo, you will " \
                 "analyze it as accurately as you can, answer all my questions, and offer any help on the subject " \
                 "related to the photo.  Remember to always describe in great detail all the aspects related to the " \
                 "photo, try to place them in the context of the conversation, and make a full analysis of what you " \
                 "see. "
        self.add_option(
            "model",
            type="combo",
            use="models",
            value="gpt-4o",
            label="Model",
            description="Model used to temporarily providing vision abilities, "
                        "default: gpt-4o",
            tooltip="Model",
        )
        self.add_option(
            "prompt",
            type="textarea",
            value=prompt,
            label="Prompt",
            description="Prompt used for vision mode. It will append or replace current system prompt "
                        "when using vision model",
            tooltip="Prompt",
            advanced=True,
        )
        self.add_option(
            "replace_prompt",
            type="bool",
            value=False,
            label="Replace prompt",
            description="Replace whole system prompt with vision prompt against appending "
                        "it to the current prompt",
            tooltip="Replace whole system prompt with vision prompt against appending it to the "
                    "current prompt",
            advanced=True,
        )
        self.add_cmd(
            "camera_capture",
            instruction="capture image from webcam",
            params=[],
            enabled=True,
        )
        self.add_cmd(
            "make_screenshot",
            instruction="make desktop screenshot",
            params=[],
            enabled=True,
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
        :param args: event args
        :param kwargs: event kwargs
        """
        name = event.name
        data = event.data
        ctx = event.ctx

        if name == Event.MODE_BEFORE:
            if self.is_allowed(data['value']):
                data['value'] = self.on_mode_before(
                    ctx,
                    mode=data['value'],
                )  # mode change

        elif name == Event.MODEL_BEFORE:
            if "mode" in data and data["mode"] == "vision":
                key = self.get_option_value("model")
                if self.window.core.models.has(key):
                    data['model'] = self.window.core.models.get(key)

        elif name == Event.PRE_PROMPT:
            if self.is_allowed(data['mode']):
                data['value'] = self.on_pre_prompt(data['value'])

        elif name == Event.INPUT_BEFORE:
            self.prompt = str(data['value'])

        elif name == Event.SYSTEM_PROMPT:
            if self.is_allowed(data['mode']):
                data['value'] = self.on_system_prompt(data['value'])

        elif name == Event.UI_ATTACHMENTS:
            data['value'] = True  # allow render attachments UI elements

        elif name == Event.UI_VISION:
            if self.is_allowed(data['mode']):
                data['value'] = True  # allow render vision UI elements

        elif name in [
            Event.CTX_SELECT,
            Event.MODE_SELECT,
            Event.MODEL_SELECT,
        ]:
            self.on_toggle(False)  # always reset vision flag / disable vision mode

        elif name in [
            Event.CMD_SYNTAX,
            Event.CMD_SYNTAX_INLINE,
        ]:
            self.cmd_syntax(data)

        elif name == Event.CMD_EXECUTE:
            self.cmd(
                ctx,
                data['commands'],
            )

    def cmd_syntax(self, data: dict):
        """
        Event: CMD_SYNTAX

        :param data: event data dict
        """
        if not self.has_cmd("camera_capture") and not self.has_cmd("make_screenshot"):
            return
        if self.has_cmd("camera_capture"):
            data['cmd'].append(self.get_cmd("camera_capture"))  # append command
        if self.has_cmd("make_screenshot"):
            data['cmd'].append(self.get_cmd("make_screenshot"))  # append command

    def cmd(self, ctx: CtxItem, cmds: list):
        """
        Event: CMD_EXECUTE

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

        responses = []
        for item in my_commands:
            response = None

            if item["cmd"] == "camera_capture" and self.has_cmd(item["cmd"]):
                response = self.cmd_camera_capture(item)

            elif item["cmd"] == "make_screenshot" and self.has_cmd(item["cmd"]):
                response = self.cmd_make_screenshot(item)

            if response:
                responses.append(response)

        # send response
        if len(responses) > 0:
            for response in responses:
                self.reply(response, ctx)

    def cmd_camera_capture(self, item: dict) -> dict:
        """
        Capture image from camera

        :param item: command item
        :return: response item
        """
        request = self.prepare_request(item)
        self.window.controller.camera.manual_capture(force=True)
        response = {
            "request": request,
            "result": "OK",
        }
        return response

    def cmd_make_screenshot(self, item: dict) -> dict:
        """
        Make desktop screenshot

        :param item: command item
        :return: response item
        """
        request = self.prepare_request(item)
        self.window.controller.painter.capture.screenshot()
        response = {
            "request": request,
            "result": "OK",
        }
        return response

    def prepare_request(self, item) -> dict:
        """
        Prepare request item for result

        :param item: item with parameters
        :return: request item
        """
        return {"cmd": item["cmd"]}

    def on_toggle(self, value: bool):
        """
        Events: CTX_SELECT, MODE_SELECT, MODEL_SELECT

        :param value: vision mode state
        """
        if not value:
            self.window.controller.chat.vision.is_enabled = False

    def on_system_prompt(self, prompt: str) -> str:
        """
        Event: SYSTEM_PROMPT

        :param prompt: prompt
        :return: updated prompt
        """
        # append vision prompt only if vision is provided or enabled
        if not self.is_vision_provided() \
                and not self.window.controller.chat.vision.enabled():
            return prompt

        # append vision prompt
        if not self.get_option_value("replace_prompt"):
            prompt += "\n" + self.get_option_value("prompt")
        return prompt

    def on_pre_prompt(self, prompt: str) -> str:
        """
        Event: PRE_PROMPT

        :param prompt: prompt
        :return: updated prompt
        """
        # append vision prompt only if vision is provided or enabled
        if not self.is_vision_provided() \
                and not self.window.controller.chat.vision.enabled():
            return prompt

        # replace vision prompt
        if self.get_option_value("replace_prompt"):
            return self.get_option_value("prompt")
        else:
            return prompt

    def is_vision_provided(self) -> bool:
        """
        Check if content for vision is provided (images, attachments)

        :return: True if vision is provided in this ctx
        """
        result = False
        mode = self.window.core.config.get('mode')
        attachments = self.window.core.attachments.get_all(mode)  # from global mode
        self.window.core.gpt.vision.build_content(
            str(self.prompt),
            attachments,
        )  # tmp build content, provide attachments from global mode

        built_attachments = self.window.core.gpt.vision.attachments
        built_urls = self.window.core.gpt.vision.urls

        # check for images in URLs found in prompt
        img_urls = []
        for url in built_urls:
            for ext in self.allowed_urls_ext:
                if url.lower().endswith(ext):
                    img_urls.append(url)
                    break

        if len(built_attachments) > 0 or len(img_urls) > 0:
            result = True

        return result

    def on_mode_before(self, ctx: CtxItem, mode: str) -> str:
        """
        Event: MODE_BEFORE

        :param ctx: current ctx
        :param mode: current mode
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

    def log(self, msg: str):
        """
        Log message to console

        :param msg: message to log
        """
        full_msg = '[Vision] ' + str(msg)
        self.debug(full_msg)
        self.window.ui.status(full_msg)
        if self.is_log():
            print(full_msg)
