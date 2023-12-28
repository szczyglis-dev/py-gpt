#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.25 21:00:00                  #
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

        # models
        for key in self.window.core.models.items:
            if key == '__meta__':
                self.window.core.debug.add(self.id, '__meta__', str(self.window.core.models.items[key]))
                continue
            prefix = "[{}] ".format(key)
            model = self.window.core.models.items[key]
            self.window.core.debug.add(self.id, '----', '')
            self.window.core.debug.add(self.id, str(key), '')
            self.window.core.debug.add(self.id, prefix + 'Key', str(key))
            self.window.core.debug.add(self.id, prefix + 'id', str(model.id))
            self.window.core.debug.add(self.id, prefix + 'name', str(model.name))
            self.window.core.debug.add(self.id, prefix + 'mode', str(model.mode))
            self.window.core.debug.add(self.id, prefix + 'langchain', str(model.langchain))
            self.window.core.debug.add(self.id, prefix + 'tokens', str(model.tokens))
            self.window.core.debug.add(self.id, prefix + 'ctx', str(model.ctx))
            self.window.core.debug.add(self.id, prefix + 'default', str(model.default))

        self.window.core.debug.end(self.id)
