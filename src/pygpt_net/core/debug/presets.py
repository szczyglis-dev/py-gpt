#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.25 22:00:00                  #
# ================================================== #

import os


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
                'chat': preset.chat,
                'completion': preset.completion,
                'img': preset.img,
                'vision': preset.vision,
                'langchain': preset.langchain,
                'assistant': preset.assistant,
                'llama_index': preset.llama_index,
                'agent': preset.agent,
                'temperature': preset.temperature,
                'version': preset.version,
            }
            self.window.core.debug.add(self.id, str(key), str(data))

        self.window.core.debug.end(self.id)
