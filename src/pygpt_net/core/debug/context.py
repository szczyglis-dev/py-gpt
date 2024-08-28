#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.27 22:00:00                  #
# ================================================== #
import json


class ContextDebug:
    def __init__(self, window=None):
        """
        Context debug

        :param window: Window instance
        """
        self.window = window
        self.id = 'context'

    def update(self):
        """Update debug window"""
        self.window.core.debug.begin(self.id)
        if self.window.core.bridge.last_context is not None:
            self.window.core.debug.add(self.id, 'bridge (last call)', str(self.window.core.bridge.last_context.to_dict()))
        else:
            self.window.core.debug.add(self.id, 'bridge (last call)', '---')
        if self.window.core.bridge.last_context_quick is not None:
            self.window.core.debug.add(self.id, 'bridge (last quick call)', str(self.window.core.bridge.last_context_quick.to_dict()))
        else:
            self.window.core.debug.add(self.id, 'bridge (last quick call)', '---')
        if self.window.controller.chat.reply.current is not None:
            self.window.core.debug.add(self.id, 'reply (queue)', str(self.window.controller.chat.reply.current.to_dict()))
        else:
            self.window.core.debug.add(self.id, 'reply (queue)', '---')
        self.window.core.debug.add(self.id, 'reply (locked)', str(self.window.controller.chat.reply.locked))
        self.window.core.debug.add(self.id, 'reply (processed)', str(self.window.controller.chat.reply.processed))
        self.window.core.debug.add(self.id, 'current (id)', str(self.window.core.ctx.current))
        self.window.core.debug.add(self.id, 'len(meta)', len(self.window.core.ctx.meta))
        self.window.core.debug.add(self.id, 'len(items)', len(self.window.core.ctx.items))
        if self.window.core.ctx.tmp_meta is not None:
            self.window.core.debug.add(self.id, 'tmp meta', str(self.window.core.ctx.tmp_meta.to_dict()))
        self.window.core.debug.add(self.id, 'group_id (active)', str(self.window.controller.ctx.group_id))
        self.window.core.debug.add(self.id, 'assistant', str(self.window.core.ctx.assistant))
        self.window.core.debug.add(self.id, 'mode', str(self.window.core.ctx.mode))
        self.window.core.debug.add(self.id, 'model', str(self.window.core.ctx.model))
        self.window.core.debug.add(self.id, 'preset', str(self.window.core.ctx.preset))
        self.window.core.debug.add(self.id, 'run', str(self.window.core.ctx.run))
        self.window.core.debug.add(self.id, 'status', str(self.window.core.ctx.status))
        self.window.core.debug.add(self.id, 'thread', str(self.window.core.ctx.thread))
        self.window.core.debug.add(self.id, 'last_mode', str(self.window.core.ctx.last_mode))
        self.window.core.debug.add(self.id, 'last_model', str(self.window.core.ctx.last_model))
        self.window.core.debug.add(self.id, 'search_string', str(self.window.core.ctx.search_string))
        self.window.core.debug.add(self.id, 'filters', str(self.window.core.ctx.filters))
        self.window.core.debug.add(self.id, 'filters_labels', str(self.window.core.ctx.filters_labels))
        self.window.core.debug.add(self.id, 'sys_prompt (current)', str(self.window.core.ctx.current_sys_prompt))
        self.window.core.debug.add(self.id, 'allowed_modes', str(self.window.core.ctx.allowed_modes))
        self.window.core.debug.add(self.id, 'CMD (current)', str(self.window.core.ctx.current_cmd))
        self.window.core.debug.add(self.id, 'CMD schema (current)', str(self.window.core.ctx.current_cmd_schema))
        self.window.core.debug.add(self.id, 'FUNCTIONS (current)', str(self.get_functions()))

        current = None
        if self.window.core.ctx.current is not None:
            if self.window.core.ctx.current in self.window.core.ctx.meta:
                current = self.window.core.ctx.meta[self.window.core.ctx.current]
            if current is not None:
                data = current.to_dict()
                self.window.core.debug.add(self.id, '*** (current)', str(data))

        i = 0
        self.window.core.debug.add(self.id, 'items[]', '')
        for item in self.window.core.ctx.items:
            data = item.to_dict()
            self.window.core.debug.add(self.id, str(item.id), str(data))
            i += 1

        self.window.core.debug.end(self.id)

    def get_functions(self) -> list:
        """
        Parse functions

        :return: List of functions
        """
        parsed = []
        functions = self.window.core.command.get_functions()
        for func in functions:
            try:
                item = {
                    "name": func['name'],
                    "desc": func['desc'],
                    "params": json.loads(func['params']),
                }
                parsed.append(item)
            except Exception as e:
                pass
        return parsed
