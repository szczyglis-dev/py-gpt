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
        self.window.core.debug.add(self.id, 'current', str(self.window.core.ctx.current))
        self.window.core.debug.add(self.id, 'assistant', str(self.window.core.ctx.assistant))
        self.window.core.debug.add(self.id, 'mode', str(self.window.core.ctx.mode))
        self.window.core.debug.add(self.id, 'preset', str(self.window.core.ctx.preset))
        self.window.core.debug.add(self.id, 'run', str(self.window.core.ctx.run))
        self.window.core.debug.add(self.id, 'status', str(self.window.core.ctx.status))
        self.window.core.debug.add(self.id, 'thread', str(self.window.core.ctx.thread))

        current = None
        if self.window.core.ctx.current is not None:
            if self.window.core.ctx.current in self.window.core.ctx.meta:
                current = self.window.core.ctx.meta[self.window.core.ctx.current]
            if current is not None:
                self.window.core.debug.add(self.id, '[current] id', str(current.id))
                self.window.core.debug.add(self.id, '[current] assistant', str(current.assistant))
                self.window.core.debug.add(self.id, '[current] date', str(current.date))
                self.window.core.debug.add(self.id, '[current] last_mode', str(current.last_mode))
                self.window.core.debug.add(self.id, '[current] mode', str(current.mode))
                self.window.core.debug.add(self.id, '[current] name', str(current.name))
                self.window.core.debug.add(self.id, '[current] preset', str(current.preset))
                self.window.core.debug.add(self.id, '[current] run', str(current.run))
                self.window.core.debug.add(self.id, '[current] status', str(current.status))
                self.window.core.debug.add(self.id, '[current] thread', str(current.thread))

        self.window.core.debug.add(self.id, 'len(contexts)', str(len(self.window.core.ctx.meta)))
        self.window.core.debug.add(self.id, 'len(items)', str(len(self.window.core.ctx.items)))

        i = 0
        for item in self.window.core.ctx.items:
            prefix = '[{}] '.format(i)
            self.window.core.debug.add(self.id, prefix + 'mode', str(item.mode))
            self.window.core.debug.add(self.id, prefix + 'input_name', str(item.input_name))
            self.window.core.debug.add(self.id, prefix + 'input', str(item.input))
            self.window.core.debug.add(self.id, prefix + 'output_name', str(item.output_name))
            self.window.core.debug.add(self.id, prefix + 'output', str(item.output))
            self.window.core.debug.add(self.id, prefix + 'input_tokens',
                                      str(item.input_tokens))
            self.window.core.debug.add(self.id, prefix + 'output_tokens',
                                      str(item.output_tokens))
            self.window.core.debug.add(self.id, prefix + 'total_tokens', str(item.total_tokens))
            self.window.core.debug.add(self.id, '------', '')
            i += 1

        self.window.core.debug.end(self.id)
