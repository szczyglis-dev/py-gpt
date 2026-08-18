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

import os
import re
from urllib.parse import urlsplit

from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_AGENT_LLAMA,
    MODE_AGENT_OPENAI,
    MODE_CHAT,
)
from pygpt_net.plugin.base.plugin import BasePlugin
from pygpt_net.item.ctx import CtxItem
from pygpt_net.core.events import Event

from .config import Config

class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "openai_vision"
        self.name = "Vision (inline)"
        self.type = [
            "vision",
            "cmd.inline",
        ]
        self.description = "Integrates image analysis with chat modes using any supported image-capable model"
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
            ".bmp",
            ".tif",
            ".tiff",
        ]
        self.allowed_cmds = [
            "camera_capture",
            "make_screenshot",
            "analyze_image_attachment",
            "analyze_screenshot",
            "analyze_camera_capture",
        ]
        # Agent runners manage their own execution flow and must not be bypassed.
        # Other supported modes can temporarily route an image turn through Chat.
        self.disabled_mode_switch = [
            MODE_AGENT,
            MODE_AGENT_LLAMA,
            MODE_AGENT_OPENAI,
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
            if data.get("mode") == MODE_CHAT and self.is_vision_provided():
                # Preserve the plugin's existing dedicated-model behavior, but
                # select by capabilities instead of the legacy Vision mode/provider.
                key = self.get_option_value("model")
                if self.window.core.models.has(key):
                    model = self.window.core.models.get(key)
                    if model.is_image_input() and model.is_supported(MODE_CHAT):
                        data['model'] = model
                        return

                # Invalid/removed plugin model: keep an already image-capable
                # current model, then try the historical default as a safe fallback.
                current_model = data.get("model")
                if (current_model is not None
                        and current_model.is_image_input()
                        and current_model.is_supported(MODE_CHAT)):
                    return
                if self.window.core.models.has("gpt-4o"):
                    fallback = self.window.core.models.get("gpt-4o")
                    if fallback.is_image_input() and fallback.is_supported(MODE_CHAT):
                        data['model'] = fallback

        elif name == Event.PRE_PROMPT:
            if self.is_allowed(data['mode']):
                data['value'] = self.on_pre_prompt(data['value'])

        elif name == Event.INPUT_BEFORE:
            self.prompt = str(data['value'])

        elif name == Event.SYSTEM_PROMPT:
            if self.is_allowed(data['mode']):
                data['value'] = self.on_system_prompt(data['value'])

        elif name == Event.UI_ATTACHMENTS:
            mode = data.get("mode")
            if mode in [MODE_AGENT, MODE_AGENT_LLAMA, MODE_AGENT_OPENAI] and not self.window.core.config.get("cmd"):
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
            self.on_toggle(False)  # always reset inline vision state

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

        # only if vision model is not used
        if self.has_cmd("analyze_image_attachment"):
            allow_inline = True
            if self.window.controller.vision.is_vision_model():
                if self.is_attachment_provided():
                    # don't allow inline if global image attachment is provided
                    allow_inline = False
            if allow_inline:
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
        from .worker import Worker

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
        return "Image attachment has been already sent.\n\n" + prompt

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

        image_prompt = str(self.get_option_value("prompt") or "").strip()
        if not image_prompt:
            return prompt

        # Replace or append the dedicated image-analysis instruction exactly as
        # described by the plugin option.
        if self.get_option_value("replace_prompt"):
            return image_prompt
        if not prompt:
            return image_prompt
        return str(prompt).rstrip() + "\n\n" + image_prompt

    def _is_image_ref(self, value: str) -> bool:
        """Check whether a local path or URL points to a supported image type."""
        if not value:
            return False
        value = str(value).strip()
        try:
            if value.lower().startswith(("http://", "https://")):
                value = urlsplit(value).path
        except ValueError:
            pass
        value = value.lower()
        return any(value.endswith(ext) for ext in self.allowed_urls_ext)

    def _get_image_attachments(self) -> dict:
        """Return current local image attachments without using a provider API helper."""
        mode = self.window.core.config.get('mode')
        attachments = self.window.core.attachments.get_all(mode)
        images = {}
        for attachment_id, attachment in attachments.items():
            path = getattr(attachment, "path", "")
            if path and os.path.exists(path) and self._is_image_ref(path):
                images[attachment_id] = attachment
        return images

    def _get_image_urls(self) -> list:
        """Return image URLs found in the current prompt."""
        urls = re.findall(r'https?://\S+', str(self.prompt))
        result = []
        for url in urls:
            clean = url.rstrip('.,;:!?)]}\"\'')
            if self._is_image_ref(clean):
                result.append(clean)
        return result

    def is_attachment_provided(self) -> bool:
        """
        Check if an image attachment is provided in this ctx

        :return: True if image attachment is provided in this ctx
        """
        return bool(self._get_image_attachments())

    def is_vision_provided(self) -> bool:
        """
        Check if content for vision is provided (images, attachments)

        :return: True if vision is provided in this ctx
        """
        return bool(self._get_image_attachments() or self._get_image_urls())

    def on_mode_before(self, ctx: CtxItem, mode: str) -> str:
        """
        Event: MODE_BEFORE

        :param ctx: current ctx
        :param mode: current mode
        :return: updated mode
        """
        if not self.is_vision_provided():
            return mode

        ctx.is_vision = True

        # Keep agent runners intact; their image-analysis commands use the
        # provider-aware analyzer instead of replacing the whole agent mode.
        if mode in self.disabled_mode_switch:
            return mode

        # The legacy Vision mode is deprecated. Route inline image turns
        # through Chat and let MODEL_BEFORE select an image-capable model.
        return MODE_CHAT

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
