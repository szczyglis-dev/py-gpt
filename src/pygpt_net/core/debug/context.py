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
        self.window.app.debug.begin(self.id)
        self.window.app.debug.add(self.id, 'current', str(self.window.app.ctx.current))
        self.window.app.debug.add(self.id, 'assistant', str(self.window.app.ctx.assistant))
        self.window.app.debug.add(self.id, 'mode', str(self.window.app.ctx.mode))
        self.window.app.debug.add(self.id, 'preset', str(self.window.app.ctx.preset))
        self.window.app.debug.add(self.id, 'run', str(self.window.app.ctx.run))
        self.window.app.debug.add(self.id, 'status', str(self.window.app.ctx.status))
        self.window.app.debug.add(self.id, 'thread', str(self.window.app.ctx.thread))

        current = None
        if self.window.app.ctx.current is not None:
            if self.window.app.ctx.current in self.window.app.ctx.meta:
                current = self.window.app.ctx.meta[self.window.app.ctx.current]
            if current is not None:
                self.window.app.debug.add(self.id, '[current] id', str(current.id))
                self.window.app.debug.add(self.id, '[current] assistant', str(current.assistant))
                self.window.app.debug.add(self.id, '[current] date', str(current.date))
                self.window.app.debug.add(self.id, '[current] last_mode', str(current.last_mode))
                self.window.app.debug.add(self.id, '[current] mode', str(current.mode))
                self.window.app.debug.add(self.id, '[current] name', str(current.name))
                self.window.app.debug.add(self.id, '[current] preset', str(current.preset))
                self.window.app.debug.add(self.id, '[current] run', str(current.run))
                self.window.app.debug.add(self.id, '[current] status', str(current.status))
                self.window.app.debug.add(self.id, '[current] thread', str(current.thread))

        self.window.app.debug.add(self.id, 'len(contexts)', str(len(self.window.app.ctx.meta)))
        self.window.app.debug.add(self.id, 'len(items)', str(len(self.window.app.ctx.items)))

        i = 0
        for item in self.window.app.ctx.items:
            prefix = '[{}] '.format(i)
            self.window.app.debug.add(self.id, prefix + 'mode', str(item.mode))
            self.window.app.debug.add(self.id, prefix + 'input_name', str(item.input_name))
            self.window.app.debug.add(self.id, prefix + 'input', str(item.input))
            self.window.app.debug.add(self.id, prefix + 'output_name', str(item.output_name))
            self.window.app.debug.add(self.id, prefix + 'output', str(item.output))
            self.window.app.debug.add(self.id, prefix + 'input_tokens',
                                      str(item.input_tokens))
            self.window.app.debug.add(self.id, prefix + 'output_tokens',
                                      str(item.output_tokens))
            self.window.app.debug.add(self.id, prefix + 'total_tokens', str(item.total_tokens))
            self.window.app.debug.add(self.id, '------', '')
            i += 1

        self.window.app.debug.end(self.id)
