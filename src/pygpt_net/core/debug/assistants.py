#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.04 12:00:00                  #
# ================================================== #

import os


class AssistantsDebug:
    def __init__(self, window=None):
        """
        Presets debug

        :param window: main window object
        """
        self.window = window
        self.id = 'assistants'

    def update(self):
        """Updates debug window."""
        self.window.debugger.begin(self.id)

        # assistants
        for key in self.window.config.assistants:
            prefix = "[{}] ".format(key)
            assistant = self.window.config.assistants[key]
            path = os.path.join(self.window.config.path,  'assistants.json')
            self.window.debugger.add(self.id, prefix + 'ID', str(key))
            self.window.debugger.add(self.id, prefix + 'File', str(path))
            if 'name' in assistant:
                self.window.debugger.add(self.id, 'name', str(assistant['name']))
            if 'description' in assistant:
                self.window.debugger.add(self.id, 'description', str(assistant['description']))
            if 'model' in assistant:
                self.window.debugger.add(self.id, 'model', str(assistant['model']))
            if 'instructions' in assistant:
                self.window.debugger.add(self.id, 'instructions', str(assistant['instructions']))
            if 'tool.code_interpreter' in assistant:
                self.window.debugger.add(self.id, 'tool.code_interpreter', str(assistant['tool.code_interpreter']))
            if 'tool.retrieval' in assistant:
                self.window.debugger.add(self.id, 'tool.retrieval', str(assistant['tool.retrieval']))
            if 'tool.function' in assistant:
                self.window.debugger.add(self.id, 'tool.function', str(assistant['tool.function']))

        self.window.debugger.end(self.id)
