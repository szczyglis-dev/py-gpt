#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Created Date: 2023.04.09 20:00:00                  #
# ================================================== #

class ContextDebug:
    def __init__(self, window=None):
        """
        Context debug

        :param window: main window object
        """
        self.window = window
        self.id = 'context'

    def update(self):
        """Updates debug window."""
        self.window.debugger.begin(self.id)

        self.window.debugger.add(self.id, 'current_ctx', str(self.window.gpt.context.current_ctx))
        self.window.debugger.add(self.id, 'current_thread', str(self.window.gpt.context.current_thread))
        self.window.debugger.add(self.id, 'current_run', str(self.window.gpt.context.current_run))
        self.window.debugger.add(self.id, 'current_status', str(self.window.gpt.context.current_status))
        self.window.debugger.add(self.id, 'current_mode', str(self.window.gpt.context.current_mode))

        current = None
        if self.window.gpt.context.current_ctx is not None:
            if self.window.gpt.context.current_ctx in self.window.gpt.context.contexts:
                current = self.window.gpt.context.contexts[self.window.gpt.context.current_ctx]
            if current is not None:
                if 'id' in current:
                    self.window.debugger.add(self.id, '[current] id', str(current['id']))
                if 'name' in current:
                    self.window.debugger.add(self.id, '[current] name', str(current['name']))
                if 'date' in current:
                    self.window.debugger.add(self.id, '[current] date', str(current['date']))
                if 'thread' in current:
                    self.window.debugger.add(self.id, '[current] thread', str(current['thread']))
                if 'run' in current:
                    self.window.debugger.add(self.id, '[current] run', str(current['run']))
                if 'status' in current:
                    self.window.debugger.add(self.id, '[current] status', str(current['status']))
                if 'mode' in current:
                    self.window.debugger.add(self.id, '[current] mode', str(current['mode']))

        self.window.debugger.add(self.id, 'len(contexts)', str(len(self.window.gpt.context.contexts)))
        self.window.debugger.add(self.id, 'len(items)', str(len(self.window.gpt.context.items)))

        i = 0
        for item in self.window.gpt.context.items:
            prefix = '[{}] '.format(i)
            self.window.debugger.add(self.id, prefix + 'mode', str(item.mode))
            self.window.debugger.add(self.id, prefix + 'input_name', str(item.input_name))
            self.window.debugger.add(self.id, prefix + 'input', str(item.input))
            self.window.debugger.add(self.id, prefix + 'output_name', str(item.output_name))
            self.window.debugger.add(self.id, prefix + 'output', str(item.output))
            self.window.debugger.add(self.id, prefix + 'input_tokens',
                                     str(item.input_tokens))
            self.window.debugger.add(self.id, prefix + 'output_tokens',
                                     str(item.output_tokens))
            self.window.debugger.add(self.id, prefix + 'total_tokens', str(item.total_tokens))
            self.window.debugger.add(self.id, '------', '')
            i += 1

        self.window.debugger.end(self.id)
