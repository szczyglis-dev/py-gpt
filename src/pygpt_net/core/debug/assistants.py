#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.14 20:00:00                  #
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
        debug = self.window.core.debug
        assistant_threads = self.window.controller.assistant.threads
        assistant_editor = self.window.controller.assistant.editor
        assistants_core = self.window.core.assistants
        assistants_store = assistants_core.store

        debug.begin(self.id)
        debug.add(self.id, '(thread) started', str(assistant_threads.started))
        debug.add(self.id, '(thread) stop', str(assistant_threads.stop))
        debug.add(self.id, '(thread) run_id', str(assistant_threads.run_id))
        debug.add(self.id, '(thread) tool_calls', str(assistant_threads.tool_calls))
        debug.add(self.id, 'Options', str(assistant_editor.get_options()))
        debug.add(self.id, '----', '')

        # assistants
        assistants = assistants_core.get_all()
        for key in list(assistants):
            prefix = f"[{key}] "
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
            debug.add(self.id, str(assistant.name), str(data))

        debug.add(self.id, '----', '')

        store_items = {}
        for id in assistants_store.items:
            store_items[id] = assistants_store.items[id].to_dict()

        debug.add(self.id, 'Store (items)', str(store_items))
        debug.end(self.id)
