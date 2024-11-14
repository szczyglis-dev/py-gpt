#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.15 00:00:00                  #
# ================================================== #

import os


class ModelsDebug:
    def __init__(self, window=None):
        """
        Models debug

        :param window: Window instance
        """
        self.window = window
        self.id = 'models'

    def update(self):
        """Update debug window."""
        self.window.core.debug.begin(self.id)

        path = os.path.join(self.window.core.config.path, '', 'models.json')
        self.window.core.debug.add(self.id, 'Models File', str(path))

        self.window.core.debug.add(
            self.id, 'Options',
            str(self.window.controller.model.editor.get_options())
        )

        # models
        for key in self.window.core.models.items:
            if key == '__meta__':
                self.window.core.debug.add(self.id, '__meta__', str(self.window.core.models.items[key]))
                continue
            model = self.window.core.models.items[key]
            data = {
                'id': model.id,
                'name': model.name,
                'mode': model.mode,
                'multimodal': model.multimodal,
                'langchain': model.langchain,
                'llama_index': model.llama_index,
                'tokens': model.tokens,
                'ctx': model.ctx,
                'default': model.default,
            }
            self.window.core.debug.add(self.id, str(key), str(data))

        self.window.core.debug.end(self.id)
