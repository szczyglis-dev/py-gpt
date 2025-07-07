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

from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_AGENT_LLAMA,
    MODE_AUDIO,
    MODE_LANGCHAIN,
    MODE_LLAMA_INDEX,
    MODE_VISION,
    MODE_CHAT,
    MODE_RESEARCH,
)
from pygpt_net.plugin.base.plugin import BasePlugin
from pygpt_net.item.ctx import CtxItem
from pygpt_net.core.events import Event

from .config import Config
from .worker import Worker

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
        self.prefix = "Vision"
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
            "analyze_image_attachment",
            "analyze_screenshot",
            "analyze_camera_capture",
        ]
        self.disabled_mode_switch = [
            MODE_CHAT,
            MODE_VISION,
            MODE_AGENT,
            MODE_AGENT_LLAMA,
            MODE_LLAMA_INDEX,
            MODE_LANGCHAIN,
            MODE_AUDIO,
            MODE_RESEARCH,
        ]
        self.worker = None
        self.config = Config(self)
        self.init_options()

    def init_options(self):
        """Initialize options"""
        self.config.from_defaults(self)

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
            if "mode" in data and data["mode"] == MODE_VISION:
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
            mode = data["mode"]
            if mode in [MODE_AGENT, MODE_AGENT_LLAMA] and not self.window.core.config.get("cmd"):
                pass
            else:
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

        elif name in [
            Event.CMD_INLINE,  # inline is allowed
            Event.CMD_EXECUTE,
        ]:
            self.cmd(
                ctx,
                data['commands'],
            )

        if name == Event.AGENT_PROMPT:
            silent = False
            if 'silent' in data and data['silent']:
                silent = True
            data['value'] = self.on_agent_prompt(
                data['value'],
                silent,
            )

        elif name == Event.MODELS_CHANGED:
            # update models list
            self.refresh_option("model")

    def cmd_syntax(self, data: dict):
        """
        Event: CMD_SYNTAX

        :param data: event data dict
        """
        if self.has_cmd("camera_capture"):
            data['cmd'].append(self.get_cmd("camera_capture"))
        """
        if self.has_cmd("make_screenshot"):
            data['cmd'].append(self.get_cmd("make_screenshot"))
        """
        if self.has_cmd("analyze_image_attachment"):
            data['cmd'].append(self.get_cmd("analyze_image_attachment"))
        if self.has_cmd("analyze_screenshot"):
            data['cmd'].append(self.get_cmd("analyze_screenshot"))
        if self.has_cmd("analyze_camera_capture"):
            data['cmd'].append(self.get_cmd("analyze_camera_capture"))

    def cmd(self, ctx: CtxItem, cmds: list):
        """
        Event: CMD_EXECUTE

        :param ctx: CtxItem
        :param cmds: commands dict
        """
        is_cmd = False
        needed_lock = False
        my_commands = []
        for item in cmds:
            if item["cmd"] in self.allowed_cmds:
                if item["cmd"] == "analyze_image_attachment":
                    needed_lock = True
                my_commands.append(item)
                is_cmd = True

        if not is_cmd:
            return

        # set state: busy
        self.cmd_prepare(ctx, my_commands)

        # don't allow to clear attachments list
        if needed_lock:
            self.window.controller.attachment.lock()
        else:
            self.window.controller.attachment.unlock()

        try:
            worker = Worker()
            worker.from_defaults(self)
            worker.cmds = my_commands
            worker.ctx = ctx
            if not self.is_async(ctx):
                worker.run()
                return
            worker.run_async()

        except Exception as e:
            self.error(e)

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
        if not self.is_vision_provided():
            return prompt
        prompt = "Image attachment has been already sent.\n\n" + prompt
        return prompt

    def on_pre_prompt(self, prompt: str) -> str:
        """
        Event: PRE_PROMPT

        :param prompt: prompt
        :return: updated prompt
        """
        # append vision prompt only if vision is provided or enabled
        if not self.is_vision_provided():
            return prompt

        if self.window.core.config.get("cmd"):
            return prompt  # vision handled by command

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
        # abort if already in vision mode or command enabled
        if mode == MODE_VISION or mode in self.disabled_mode_switch:
            return mode  # keep current mode

        # if already used in this ctx then keep vision mode
        if self.is_vision_provided():
            ctx.is_vision = True
            return MODE_VISION

        return mode  # keep current mode

    def on_agent_prompt(self, prompt: str, silent: bool = False) -> str:
        """
        Event: AGENT_PROMPT

        :param prompt: prompt
        :param silent: silent mode (no logs)
        :return: updated prompt
        """
        if not self.is_vision_provided():
            return prompt

        prompt = "Image attachment has been already sent.\n\n" + prompt
        return prompt
