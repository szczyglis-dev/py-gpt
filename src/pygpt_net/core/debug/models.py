#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.05 22:00:00                  #
# ================================================== #

import os


class ModelsDebug:
    def __init__(self, window=None):
        """
        Models debug

        :param window: main window object
        """
        self.window = window
        self.id = 'models'

    def update(self):
        """Updates debug window."""
        self.window.debugger.begin(self.id)

        path = os.path.join(self.window.config.path, '', 'models.json')
        self.window.debugger.add(self.id, 'Models File', str(path))

        # models
        for key in self.window.config.models:
            if key == '__meta__':
                self.window.debugger.add(self.id, '__meta__', str(self.window.config.models[key]))
                continue
            prefix = "[{}] ".format(key)
            model = self.window.config.models[key]
            self.window.debugger.add(self.id, '----', '')
            self.window.debugger.add(self.id, str(key), '')
            self.window.debugger.add(self.id, prefix + 'Key', str(key))
            self.window.debugger.add(self.id, prefix + 'id', str(model['id']))
            self.window.debugger.add(self.id, prefix + 'name', str(model['name']))
            self.window.debugger.add(self.id, prefix + 'mode', str(model['mode']))
            self.window.debugger.add(self.id, prefix + 'tokens', str(model['tokens']))

        self.window.debugger.end(self.id)
