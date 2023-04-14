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
