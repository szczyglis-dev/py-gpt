#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.28 16:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QApplication

from pygpt_net.core.ctx.reply import ReplyContext


class Reply:
    def __init__(self, window=None):
        """
        Reply stack controller

        :param window: Window instance
        """
        self.window = window
        self.current = None
        self.locked = False
        self.processed = False

    def add(self, context: ReplyContext):
        """
        Add reply to stack

        :param context: ReplyContext
        """
        self.current = context
        self.unlock()
        self.processed = False

    def has(self):
        """
        Check if reply stack has any item

        :return: True if has
        """
        return self.current is not None

    def clear(self):
        """
        Clear reply stack
        """
        self.current = None
        self.unlock()

    def execute(self, context: ReplyContext):
        """
        Execute reply context

        :param context: ReplyContext
        """
        # expert call
        if context.type == ReplyContext.EXPERT_CALL:
            self.window.core.experts.call(
                context.ctx,  # master ctx
                context.parent_id,  # expert id
                context.input,  # query
            )
        elif context.type == ReplyContext.CMD_EXECUTE:
            self.window.controller.plugins.apply_cmds(
                context.ctx,  # current ctx
                context.cmds,  # commands
            )
        elif context.type == ReplyContext.CMD_EXECUTE_INLINE:
            self.window.controller.plugins.apply_cmds_inline(
                context.ctx,  # current ctx
                context.cmds,  # commands
            )
        elif context.type == ReplyContext.AGENT_CONTINUE:
            self.window.controller.chat.input.send(
                text=context.input,
                force=True,
                internal=True,
                prev_ctx=context.ctx,
            )

    def is_locked(self) -> bool:
        """
        Check if reply stack is locked

        :return: True if locked
        """
        return self.locked

    def lock(self):
        """Lock reply stack"""
        self.locked = True

    def unlock(self):
        """Unlock reply stack"""
        self.locked = False

    def handle(self):
        """Handle reply stack"""
        if self.window.controller.chat.common.stopped():
            self.clear()
            return

        if self.waiting():
            self.lock()
            QApplication.processEvents()
            self.execute(self.current)
            self.processed = True

    def waiting(self):
        """
        Check if reply stack is waiting

        :return: True if waiting
        """
        return self.has() and not self.is_locked()

    def log(self, data: any):
        """
        Log data to debug

        :param data: Data to log
        """
        self.window.core.debug.info(data)
