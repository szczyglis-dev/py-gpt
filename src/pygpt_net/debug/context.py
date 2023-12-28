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
        self.window.core.debug.add(self.id, 'current (id)', str(self.window.core.ctx.current))
        self.window.core.debug.add(self.id, 'len(meta)', len(self.window.core.ctx.meta))
        self.window.core.debug.add(self.id, 'len(items)', len(self.window.core.ctx.items))
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

        current = None
        if self.window.core.ctx.current is not None:
            if self.window.core.ctx.current in self.window.core.ctx.meta:
                current = self.window.core.ctx.meta[self.window.core.ctx.current]
            if current is not None:
                self.window.core.debug.add(self.id, '** [current] id', str(current.id))
                self.window.core.debug.add(self.id, '** [current] external_id', str(current.external_id))
                self.window.core.debug.add(self.id, '** [current] uuid', str(current.uuid))
                self.window.core.debug.add(self.id, '** [current] name', str(current.name))
                self.window.core.debug.add(self.id, '** [current] date', str(current.date))
                self.window.core.debug.add(self.id, '** [current] created', str(current.created))
                self.window.core.debug.add(self.id, '** [current] updated', str(current.updated))
                self.window.core.debug.add(self.id, '** [current] mode', str(current.mode))
                self.window.core.debug.add(self.id, '** [current] model', str(current.model))
                self.window.core.debug.add(self.id, '** [current] last_mode', str(current.last_mode))
                self.window.core.debug.add(self.id, '** [current] last_model', str(current.last_model))
                self.window.core.debug.add(self.id, '** [current] thread', str(current.thread))
                self.window.core.debug.add(self.id, '** [current] assistant', str(current.assistant))
                self.window.core.debug.add(self.id, '** [current] preset', str(current.preset))
                self.window.core.debug.add(self.id, '** [current] run', str(current.run))
                self.window.core.debug.add(self.id, '** [current] status', str(current.status))
                self.window.core.debug.add(self.id, '** [current] extra', str(current.extra))
                self.window.core.debug.add(self.id, '** [current] initialized', str(current.initialized))
                self.window.core.debug.add(self.id, '** [current] deleted', str(current.deleted))
                self.window.core.debug.add(self.id, '** [current] important', str(current.important))
                self.window.core.debug.add(self.id, '** [current] archived', str(current.archived))

        i = 0
        for item in self.window.core.ctx.items:
            prefix = '[{}] '.format(i)
            self.window.core.debug.add(self.id, prefix + 'id', str(item.id))
            self.window.core.debug.add(self.id, prefix + 'meta_id', str(item.meta_id))
            self.window.core.debug.add(self.id, prefix + 'external_id', str(item.external_id))
            self.window.core.debug.add(self.id, prefix + 'stream', str(item.stream))
            self.window.core.debug.add(self.id, prefix + 'cmds', str(item.cmds))
            self.window.core.debug.add(self.id, prefix + 'results', str(item.results))
            self.window.core.debug.add(self.id, prefix + 'urls', str(item.urls))
            self.window.core.debug.add(self.id, prefix + 'images', str(item.images))
            self.window.core.debug.add(self.id, prefix + 'files', str(item.files))
            self.window.core.debug.add(self.id, prefix + 'attachments', str(item.attachments))
            self.window.core.debug.add(self.id, prefix + 'reply', str(item.reply))
            self.window.core.debug.add(self.id, prefix + 'input', str(item.input))
            self.window.core.debug.add(self.id, prefix + 'output', str(item.output))
            self.window.core.debug.add(self.id, prefix + 'mode', str(item.mode))
            self.window.core.debug.add(self.id, prefix + 'model', str(item.model))
            self.window.core.debug.add(self.id, prefix + 'thread', str(item.thread))
            self.window.core.debug.add(self.id, prefix + 'msg_id', str(item.msg_id))
            self.window.core.debug.add(self.id, prefix + 'run_id', str(item.run_id))
            self.window.core.debug.add(self.id, prefix + 'input_name', str(item.input_name))
            self.window.core.debug.add(self.id, prefix + 'output_name', str(item.output_name))
            self.window.core.debug.add(self.id, prefix + 'input_timestamp', str(item.input_timestamp))
            self.window.core.debug.add(self.id, prefix + 'output_timestamp', str(item.output_timestamp))
            self.window.core.debug.add(self.id, prefix + 'input_tokens', str(item.input_tokens))
            self.window.core.debug.add(self.id, prefix + 'output_tokens', str(item.output_tokens))
            self.window.core.debug.add(self.id, prefix + 'total_tokens', str(item.total_tokens))
            self.window.core.debug.add(self.id, prefix + 'extra', str(item.extra))
            self.window.core.debug.add(self.id, '------', '')
            i += 1

        self.window.core.debug.end(self.id)
