#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.28 21:00:00                  #
# ================================================== #


class AssistantsDebug:
    def __init__(self, window=None):
        """
        Assistants debug

        :param window: Window instance
        """
        self.window = window
        self.id = 'assistants'

    def update(self):
        """Update debug window."""
        self.window.core.debug.begin(self.id)

        # assistants
        assistants = self.window.core.assistants.get_all()
        for key in list(assistants):
            prefix = "[{}] ".format(key)
            assistant = assistants[key]
            self.window.core.debug.add(self.id, '----', '')
            self.window.core.debug.add(self.id, str(key), '')
            self.window.core.debug.add(self.id, 'id', str(assistant.id))
            self.window.core.debug.add(self.id, 'name', str(assistant.name))
            self.window.core.debug.add(self.id, 'description', str(assistant.description))
            self.window.core.debug.add(self.id, 'model', str(assistant.model))
            self.window.core.debug.add(self.id, 'instructions', str(assistant.instructions))
            self.window.core.debug.add(self.id, 'meta', str(assistant.meta))
            self.window.core.debug.add(self.id, 'tools', str(assistant.tools))
            self.window.core.debug.add(self.id, 'files', str(assistant.files))
            self.window.core.debug.add(self.id, 'tools[function]', str(assistant.tools['function']))

        self.window.core.debug.end(self.id)
