#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.26 22:00:00                  #
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
        self.window.core.debug.add(self.id, 'filters', str(self.window.core.ctx.filters))
        self.window.core.debug.add(self.id, 'sys_prompt (tmp)', str(self.window.core.ctx.current_sys_prompt))
        self.window.core.debug.add(self.id, 'allowed_modes', str(self.window.core.ctx.allowed_modes))

        current = None
        if self.window.core.ctx.current is not None:
            if self.window.core.ctx.current in self.window.core.ctx.meta:
                current = self.window.core.ctx.meta[self.window.core.ctx.current]
            if current is not None:
                data = {
                    "id": current.id,
                    "external_id": current.external_id,
                    "uuid": current.uuid,
                    "name": current.name,
                    "date": current.date,
                    "created": current.created,
                    "updated": current.updated,
                    "indexed": current.indexed,
                    "indexes": current.indexes,
                    "mode": current.mode,
                    "model": current.model,
                    "last_mode": current.last_mode,
                    "last_model": current.last_model,
                    "thread": current.thread,
                    "assistant": current.assistant,
                    "preset": current.preset,
                    "run": current.run,
                    "status": current.status,
                    "label": current.label,
                    "initialized": current.initialized,
                    "deleted": current.deleted,
                    "important": current.important,
                    "archived": current.archived,
                    "extra": current.extra,
                }
                self.window.core.debug.add(self.id, '*** (current)', str(data))

        i = 0
        self.window.core.debug.add(self.id, 'items[]', '')
        for item in self.window.core.ctx.items:
            data = {
                "id": item.id,
                "meta_id": item.meta_id,
                "external_id": item.external_id,
                "cmds": item.cmds,
                "results": item.results,
                "urls": item.urls,
                "images": item.images,
                "files": item.files,
                "attachments": item.attachments,
                "reply": item.reply,
                "input": item.input,
                "output": item.output,
                "mode": item.mode,
                "model": item.model,
                "thread": item.thread,
                "msg_id": item.msg_id,
                "run_id": item.run_id,
                "input_name": item.input_name,
                "output_name": item.output_name,
                "input_timestamp": item.input_timestamp,
                "output_timestamp": item.output_timestamp,
                "input_tokens": item.input_tokens,
                "output_tokens": item.output_tokens,
                "total_tokens": item.total_tokens,
                "extra": item.extra,
                "is_vision": item.is_vision,
                "idx": item.idx,
                "first": item.first,
                "tool_calls": item.tool_calls,
            }
            self.window.core.debug.add(self.id, str(item.id), str(data))
            i += 1

        self.window.core.debug.end(self.id)
