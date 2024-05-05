#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.05.05 12:00:00                  #
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

        self.window.core.debug.add(self.id, '(thread) started', str(self.window.controller.assistant.threads.started))
        self.window.core.debug.add(self.id, '(thread) stop', str(self.window.controller.assistant.threads.stop))
        self.window.core.debug.add(self.id, '(thread) run_id', str(self.window.controller.assistant.threads.run_id))
        self.window.core.debug.add(self.id, '(thread) tool_calls', str(self.window.controller.assistant.threads.tool_calls))

        self.window.core.debug.add(
            self.id, 'Options',
            str(self.window.controller.assistant.editor.get_options())
        )

        self.window.core.debug.add(self.id, '----', '')

        # assistants
        assistants = self.window.core.assistants.get_all()
        for key in list(assistants):
            prefix = "[{}] ".format(key)
            assistant = assistants[key]
            data = {
                'id': assistant.id,
                'name': assistant.name,
                'description': assistant.description,
                'model': assistant.model,
                'instructions': assistant.instructions,
                'meta': assistant.meta,
                'tools': assistant.tools,
                'files': assistant.files,
                'tools[function]': assistant.tools['function']
            }
            self.window.core.debug.add(self.id, str(assistant.name), str(data))

        self.window.core.debug.add(self.id, '----', '')

        store_items = {}
        for id in self.window.core.assistants.store.items:
            store_items[id] = self.window.core.assistants.store.items[id].to_dict()

        self.window.core.debug.add(self.id, 'Store (items)', str(store_items))
        #self.window.core.debug.add(self.id, 'Store (items)', str(self.window.core.assistants.store.items))

        self.window.core.debug.end(self.id)
