#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.23 22:00:00                  #
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
        self.window.app.debug.begin(self.id)

        # presets
        for key in self.window.app.presets.items:
            prefix = "[{}] ".format(key)
            preset = self.window.app.presets.items[key]
            path = os.path.join(self.window.app.config.path, 'presets', key + '.json')
            self.window.app.debug.add(self.id, prefix + 'ID', str(key))
            self.window.app.debug.add(self.id, prefix + 'File', str(path))
            if 'name' in preset:
                self.window.app.debug.add(self.id, prefix + 'name', str(preset['name']))
            if 'ai_name' in preset:
                self.window.app.debug.add(self.id, prefix + 'ai_name', str(preset['ai_name']))
            if 'user_name' in preset:
                self.window.app.debug.add(self.id, prefix + 'user_name', str(preset['user_name']))
            if 'prompt' in preset:
                self.window.app.debug.add(self.id, prefix + 'prompt', str(preset['prompt']))
            if 'chat' in preset:
                self.window.app.debug.add(self.id, prefix + 'chat', str(preset['chat']))
            if 'completion' in preset:
                self.window.app.debug.add(self.id, prefix + 'completion', str(preset['completion']))
            if 'img' in preset:
                self.window.app.debug.add(self.id, prefix + 'img', str(preset['img']))
            if 'vision' in preset:
                self.window.app.debug.add(self.id, prefix + 'vision', str(preset['vision']))
            if 'langchain' in preset:
                self.window.app.debug.add(self.id, prefix + 'langchain', str(preset['langchain']))
            if 'assistant' in preset:
                self.window.app.debug.add(self.id, prefix + 'assistant', str(preset['assistant']))
            if 'temperature' in preset:
                self.window.app.debug.add(self.id, prefix + 'temperature', str(preset['temperature']))

        self.window.app.debug.end(self.id)
