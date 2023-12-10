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

from ..utils import trans


class Context:
    def __init__(self, window=None):
        """
        Context controller

        :param window: main window object
        """
        self.window = window

    def setup(self):
        """Setups context"""
        self.window.gpt.context.load_list()
        if len(self.window.gpt.context.contexts) == 0:
            self.new()
        else:
            ctx = self.window.config.data['ctx']
            if ctx is not None and ctx in self.window.gpt.context.contexts:
                self.window.gpt.context.current_ctx = ctx
            else:
                self.window.gpt.context.current_ctx = self.window.gpt.context.get_first_ctx()

        self.load(self.window.gpt.context.current_ctx)

    def new(self):
        """Creates new context"""
        self.window.gpt.context.new()
        self.window.config.data['assistant_thread'] = None  # reset thread
        self.update()
        self.window.controller.output.clear()
        self.window.controller.input.unlock_input()  # force unlock input

    def update(self):
        """Updates context list"""
        items = self.window.gpt.context.get_list()
        self.window.ui.contexts.update_list('ctx.contexts', items)
        self.select_ctx_by_current()
        self.window.controller.ui.update()
        self.window.debugger.update(True)
        self.window.debugger.update(True)

        ctx = self.window.gpt.context.current_ctx
        thread = self.window.gpt.context.current_thread
        if ctx is not None:
            self.window.config.data['ctx'] = ctx
            self.window.config.data['assistant_thread'] = thread
            self.window.config.save()

    def update_ctx(self):
        """Updates context list"""
        self.window.gpt.context.update()

    def load(self, ctx):
        """
        Loads context

        :param ctx: context name (id)
        """
        self.window.gpt.context.select(ctx)

        # set current thread
        thread = self.window.gpt.context.current_thread
        mode = self.window.gpt.context.current_mode
        self.window.config.data['assistant_thread'] = thread

        # update output and context list
        self.window.controller.output.clear()
        self.window.controller.output.append_context()
        self.update()

        # change to saved mode
        if mode is not None:
            self.window.controller.model.set_mode(mode)

    def refresh(self):
        """Refreshes context"""
        self.load(self.window.gpt.context.current_ctx)

    def selection_change(self):
        """
        Selects context on list change
        """
        # TODO: implement this
        # idx = self.window.data['ctx.contexts'].currentIndex().row()
        # self.select(idx)
        pass

    def select(self, idx):
        """
        Selects context

        :param idx: context index
        """
        ctx = self.window.gpt.context.get_name_by_idx(idx)
        self.window.gpt.context.current_ctx = ctx
        self.load(ctx)

    def delete(self, idx, force=False):
        """
        Deletes context

        :param idx: context index
        :param force: force delete
        """
        if not force:
            self.window.ui.dialogs.confirm('ctx_delete', idx, trans('ctx.delete.confirm'))
            return

        ctx = self.window.gpt.context.get_name_by_idx(idx)
        self.window.gpt.context.delete_ctx(ctx)
        if self.window.gpt.context.current_ctx == ctx:
            self.window.gpt.context.current_ctx = None
            self.window.controller.output.clear()
        self.update()

    def delete_history(self, force=False):
        """
        Deletes context history item

        :param force: force delete
        """
        if not force:
            self.window.ui.dialogs.confirm('ctx_delete_all', '', trans('ctx.delete.all.confirm'))
            return

        self.window.gpt.context.delete_all_ctx()
        self.update()

    def rename(self, idx):
        """
        Renames context

        :param idx: context index
        """
        ctx = self.window.gpt.context.get_name_by_idx(idx)
        ctx_data = self.window.gpt.context.get_context_by_name(ctx)
        self.window.dialog['rename'].id = 'ctx'
        self.window.dialog['rename'].input.setText(ctx_data['name'])
        self.window.dialog['rename'].current = ctx
        self.window.dialog['rename'].show()
        self.update()

    def select_ctx_by_current(self):
        """Selects ctx by current"""
        ctx = self.window.gpt.context.current_ctx
        items = self.window.gpt.context.get_list()
        if ctx in items:
            idx = list(items.keys()).index(ctx)
            current = self.window.models['ctx.contexts'].index(idx, 0)
            self.window.data['ctx.contexts'].setCurrentIndex(current)

    def update_name(self, ctx, name):
        """
        Updates context name

        :param ctx: context name (id)
        :param name: context name
        """
        if ctx not in self.window.gpt.context.contexts:
            return
        self.window.gpt.context.contexts[ctx]['name'] = name
        self.window.gpt.context.set_ctx_initialized()
        self.window.gpt.context.dump_context(ctx)
        self.window.dialog['rename'].close()
        self.update()

    def dismiss_rename(self):
        """Dismisses rename dialog"""
        self.window.dialog['rename'].close()

    def add(self, ctx):
        """
        Adds context

        :param ctx: context name (id)
        """
        self.window.gpt.context.add(ctx)
        self.update()
