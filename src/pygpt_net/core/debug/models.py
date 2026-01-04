#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.05 20:00:00                  #
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
        debug = self.window.core.debug
        models_controller = self.window.controller.model
        models_core = self.window.core.models
        command_core = self.window.core.command
        config_core = self.window.core.config

        debug.begin(self.id)

        path = os.path.join(config_core.path, '', 'models.json')
        debug.add(self.id, 'Models File', str(path))
        debug.add(self.id, 'editor.selected[]', str(models_controller.editor.selected))
        debug.add(self.id, '[func] is_native_enabled()', str(command_core.is_native_enabled()))

        debug.add(
            self.id, 'Options',
            str(models_controller.model.editor.get_options())
        )

        # models
        for key in models_core.items:
            if key == '__meta__':
                debug.add(self.id, '__meta__', str(models_core.items[key]))
                continue

            model = models_core.items[key]
            data = {
                'id': model.id,
                'name': model.name,
                'provider': model.provider,
                'mode': model.mode,
                'input': model.input,
                'output': model.output,
                'langchain': model.langchain,
                'llama_index': model.llama_index,
                'tool_calls': model.tool_calls,
                'tokens': model.tokens,
                'ctx': model.ctx,
                'default': model.default,
                'imported': model.imported,
            }
            debug.add(self.id, str(key), str(data))

        debug.end(self.id)
