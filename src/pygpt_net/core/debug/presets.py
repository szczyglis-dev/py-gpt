#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.06.28 16:00:00                  #
# ================================================== #

import os

from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_AGENT_LLAMA,
    MODE_ASSISTANT,
    MODE_AUDIO,
    MODE_CHAT,
    MODE_COMPLETION,
    MODE_EXPERT,
    MODE_IMAGE,
    MODE_LANGCHAIN,
    MODE_LLAMA_INDEX,
    MODE_VISION,
    MODE_RESEARCH,
)

class PresetsDebug:
    def __init__(self, window=None):
        """
        Presets debug

        :param window: Window instance
        """
        self.window = window
        self.id = 'presets'

    def update(self):
        """Update debug window."""
        self.window.core.debug.begin(self.id)

        self.window.core.debug.add(
            self.id, 'Options',
            str(self.window.controller.presets.editor.get_options())
        )

        # presets
        for key in list(dict(self.window.core.presets.items)):
            preset = self.window.core.presets.items[key]
            path = os.path.join(self.window.core.config.path, 'presets', key + '.json')
            data = {
                'id': key,
                'file': path,
                'name': preset.name,
                'ai_name': preset.ai_name,
                'user_name': preset.user_name,
                'prompt': preset.prompt,
                MODE_CHAT: preset.chat,
                MODE_COMPLETION: preset.completion,
                MODE_IMAGE: preset.img,
                MODE_VISION: preset.vision,
                # MODE_LANGCHAIN: preset.langchain,
                MODE_ASSISTANT: preset.assistant,
                MODE_LLAMA_INDEX: preset.llama_index,
                MODE_AGENT: preset.agent,
                MODE_AGENT_LLAMA: preset.agent_llama,
                MODE_EXPERT: preset.expert,
                MODE_AUDIO: preset.audio,
                MODE_RESEARCH: preset.research,
                'temperature': preset.temperature,
                'version': preset.version,
            }
            self.window.core.debug.add(self.id, str(key), str(data))

        self.window.core.debug.end(self.id)
