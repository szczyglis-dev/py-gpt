#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 18:00:00                  #
# ================================================== #

import base64
import os

from pygpt_net.core.types import (
    MODE_AUDIO,
)
from pygpt_net.core.bridge.context import MultimodalContext, BridgeContext
from pygpt_net.core.events import KernelEvent
from pygpt_net.item.ctx import CtxItem


class Audio:
    def __init__(self, window=None):
        """
        Chat audio controller

        :param window: Window instance
        """
        self.window = window
        self.audio_file = "chat_output.wav"
        self.tmp_input = False
        self.tmp_output = False

    def setup(self):
        """Set up UI"""
        pass

    def update(self):
        """Update input/output audio"""
        mode = self.window.core.config.get("mode")
        if mode == MODE_AUDIO:
            if not self.window.controller.audio.is_output_enabled():
                self.window.controller.audio.enable_output()
                self.tmp_output = True
            else:
                self.tmp_output = False
            if not self.window.controller.audio.is_input_enabled():
                self.window.controller.audio.enable_input()
                self.tmp_input = True
            else:
                self.tmp_input = False
        else:
            if self.tmp_output:
                self.window.controller.audio.disable_output()
            if self.tmp_input:
                self.window.controller.audio.disable_input()

    def handle_output(self, ctx: CtxItem):
        """
        Handle output audio

        :param ctx: Context item
        """
        wav_path = os.path.join(self.window.core.config.get_user_path(), self.audio_file)
        if ctx.is_audio and ctx.audio_output and ctx.audio_read_allowed():
            wav_bytes = base64.b64decode(ctx.audio_output)
            with open(wav_path, "wb") as f:
                f.write(wav_bytes)
            self.window.controller.audio.play_chat_audio(wav_path)

    def handle_input(self, path: str):
        """
        Handle input audio

        :param path: audio file path
        """
        multimodal_ctx = MultimodalContext()
        with open(path, "rb") as f:
            multimodal_ctx.audio_data = f.read()
        multimodal_ctx.is_audio_input = True

        bridge_ctx = BridgeContext()
        bridge_ctx.prompt = self.window.ui.nodes['input'].toPlainText()  # attach text input
        bridge_ctx.multimodal_ctx = multimodal_ctx
        event = KernelEvent(KernelEvent.INPUT_USER, {
            'context': bridge_ctx,
            'extra': {},
        })
        self.window.dispatch(event)

    def enabled(self) -> bool:
        """
        Check if audio mode is enabled

        :return: bool True if enabled
        """
        return self.window.core.config.get("mode") == MODE_AUDIO

