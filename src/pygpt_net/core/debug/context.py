#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.22 04:00:00                  #
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
        debug = self.window.core.debug
        bridge = self.window.core.bridge
        controller = self.window.controller
        ctx_core = self.window.core.ctx
        attachments = self.window.core.attachments.context
        kernel_stack = controller.kernel.stack

        debug.begin(self.id)

        last_context = bridge.last_context
        last_context_quick = bridge.last_context_quick
        current_stack = kernel_stack.current

        debug.add(self.id, 'bridge (last call)', str(last_context.to_dict()) if last_context is not None else '---')
        debug.add(self.id, 'bridge (last quick call)',
                  str(last_context_quick.to_dict()) if last_context_quick is not None else '---')
        debug.add(self.id, 'reply (queue)', str(current_stack.to_dict()) if current_stack is not None else '---')

        debug.add(self.id, 'reply (locked)', str(kernel_stack.locked))
        debug.add(self.id, 'reply (processed)', str(kernel_stack.processed))
        debug.add(self.id, 'current (id)', str(ctx_core.get_current()))
        debug.add(self.id, 'len(meta)', len(ctx_core.meta))
        debug.add(self.id, 'len(items)', len(ctx_core.get_items()))
        debug.add(self.id, 'Stream PIDs', str(controller.chat.stream.get_pid_ids()))
        debug.add(self.id, 'SYS PROMPT (current)', str(ctx_core.current_sys_prompt))
        debug.add(self.id, 'CMD (current)', str(ctx_core.current_cmd))
        debug.add(self.id, 'CMD schema (current)', str(ctx_core.current_cmd_schema))
        debug.add(self.id, 'FUNCTIONS (current)', str(self.get_functions()))
        debug.add(self.id, 'Attachments: last used content', str(attachments.last_used_content))
        debug.add(self.id, 'Attachments: last used context', str(attachments.last_used_context))

        current_id = ctx_core.get_current()
        current = ctx_core.meta.get(current_id)

        if current is not None:
            debug.add(self.id, '*** (current)', str(current.to_dict()))

        tmp_meta = ctx_core.get_tmp_meta()
        if tmp_meta is not None:
            debug.add(self.id, 'tmp meta', str(tmp_meta.to_dict()))

        debug.add(self.id, 'selected[]', str(controller.ctx.selected))
        debug.add(self.id, 'group_id (active)', str(controller.ctx.group_id))
        debug.add(self.id, 'assistant', str(ctx_core.get_assistant()))
        debug.add(self.id, 'mode', str(ctx_core.get_mode()))
        debug.add(self.id, 'model', str(ctx_core.get_model()))
        debug.add(self.id, 'preset', str(ctx_core.get_preset()))
        debug.add(self.id, 'run', str(ctx_core.get_run()))
        debug.add(self.id, 'status', str(ctx_core.get_status()))
        debug.add(self.id, 'thread', str(ctx_core.get_thread()))
        debug.add(self.id, 'last_mode', str(ctx_core.get_last_mode()))
        debug.add(self.id, 'last_model', str(ctx_core.get_last_model()))
        debug.add(self.id, 'search_string', str(ctx_core.get_search_string()))
        debug.add(self.id, 'filters', str(ctx_core.filters))
        debug.add(self.id, 'filters_labels', str(ctx_core.filters_labels))
        debug.add(self.id, 'allowed_modes', str(ctx_core.allowed_modes))

        debug.add(self.id, 'items[]', '')
        for i, item in enumerate(ctx_core.get_items()):
            debug.add(self.id, str(item.id), str(item.to_dict()))

        debug.end(self.id)

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
