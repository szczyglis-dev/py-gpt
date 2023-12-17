#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.17 03:00:00                  #
# ================================================== #

from ..utils import trans


class Context:
    def __init__(self, window=None):
        """
        Context controller

        :param window: main window object
        """
        self.window = window
        self.allowed_modes = {
            'chat': ['chat', 'completion', 'img', 'langchain', 'vision', 'assistant'],
            'completion': ['chat', 'completion', 'img', 'langchain', 'vision', 'assistant'],
            'img': ['img'],
            'langchain': ['chat', 'completion', 'img', 'langchain', 'vision', 'assistant'],
            'vision': ['vision'],
            'assistant': ['assistant'],
        }

    def setup(self):
        """Setups context"""
        self.window.gpt.context.load_list()
        if len(self.window.gpt.context.contexts) == 0:
            self.new()
        else:
            ctx = self.window.config.get('ctx')
            if ctx is not None and ctx in self.window.gpt.context.contexts:
                self.window.gpt.context.current_ctx = ctx
            else:
                self.window.gpt.context.current_ctx = self.window.gpt.context.get_first_ctx()

        self.load(self.window.gpt.context.current_ctx)

    def context_change_locked(self):
        """
        Checks if context change is locked

        :return: bool
        """
        if self.window.controller.input.generating:
            return True
        return False

    def new(self, force=False):
        """
        Creates new context

        :param force: force context creation
        """
        # lock if generating response is in progress
        if not force and self.context_change_locked():
            return

        self.window.gpt.context.new()
        self.window.config.set('assistant_thread', None)  # reset thread
        self.update()
        self.window.controller.output.clear()

        if not force:  # only if real click on new context button
            self.window.controller.input.unlock_input()

        # update context label
        mode = self.window.gpt.context.current_mode
        assistant_id = None
        if mode == 'assistant':
            assistant_id = self.window.config.get('assistant')
        self.update_ctx_label(mode, assistant_id)

    def handle_allowed(self, mode):
        """
        Checks if context is allowed for this mode, if not then switch to new context

        :param mode: mode name
        :return: bool
        """
        if not self.is_allowed_for_mode(mode):
            self.new(True)
            return False
        return True

    def is_allowed_for_mode(self, mode, check_assistant=True):
        """
        Checks if context is allowed for this mode

        :param mode: mode name
        :param check_assistant: True if check also current assistant
        :return: bool
        """
        ctx = self.window.config.get('ctx')

        if ctx is None or ctx == '':
            return True
        ctx_data = self.window.gpt.context.get_context_by_name(ctx)
        if 'last_mode' not in ctx_data or ctx_data['last_mode'] is None:
            return True
        prev_mode = ctx_data['last_mode']
        if prev_mode not in self.allowed_modes[mode]:
            # exception for assistant (if before was assistant then allow)
            if mode == 'assistant':
                if 'assistant' in ctx_data and ctx_data['assistant'] is not None:
                    if ctx_data['assistant'] == self.window.config.get('assistant'):
                        return True
                else:
                    return True  # if no assistant in context then allow

            # in other modes, then always return False
            return False

        # check allowed assistant
        if mode == 'assistant' and check_assistant:
            if 'assistant' not in ctx_data or ctx_data['assistant'] is None:
                return True
            # check if current assistant is allowed
            if ctx_data['assistant'] != self.window.config.get('assistant'):
                return False
        return True

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
            self.window.config.set('ctx', ctx)
            self.window.config.set('assistant_thread', thread)
            self.window.config.save()

    def update_ctx(self):
        """Updates current context mode if allowed"""
        mode = self.window.config.get('mode')
        # update ctx mode only if current ctx is allowed for this mode
        if self.is_allowed_for_mode(mode, False):  # do not check assistant match
            self.window.gpt.context.update()
            # set current context label
            assistant_id = None
            if mode == 'assistant':
                # get from context if defined
                ctx_assistant_id = self.window.gpt.context.current_assistant
                if ctx_assistant_id is not None:
                    assistant_id = ctx_assistant_id
                else:
                    assistant_id = self.window.config.get('assistant')
            self.update_ctx_label(mode, assistant_id)

    def load(self, ctx):
        """
        Loads context

        :param ctx: context name (id)
        """
        self.window.gpt.context.select(ctx)

        # set current thread
        thread = self.window.gpt.context.current_thread
        mode = self.window.gpt.context.current_mode
        assistant_id = self.window.gpt.context.current_assistant

        self.window.config.set('assistant_thread', thread)

        # update output and context list
        self.window.controller.output.clear()
        self.window.controller.output.append_context()
        self.update()

        # change to saved mode
        if mode is not None:
            self.window.controller.model.set_mode(mode)
            # if assistant then select stored assistant
            if mode == 'assistant':
                if assistant_id is not None:
                    self.window.controller.assistant.select_by_id(assistant_id)

        # set current context label
        self.update_ctx_label(mode, assistant_id)

    def refresh(self):
        """Refreshes context"""
        self.load(self.window.gpt.context.current_ctx)

    def update_ctx_label_by_current(self):
        """
        Updates context label by current context
        """
        mode = self.window.gpt.context.current_mode
        assistant_id = self.window.gpt.context.current_assistant
        mode_str = trans('mode.' + mode)
        if mode == 'assistant' and assistant_id is not None:
            assistant = self.window.controller.assistant.assistants.get_by_id(assistant_id)
            if assistant is not None:
                mode_str += ' (' + assistant.name + ')'
        # update context label
        self.set_ctx_label(mode_str)

    def update_ctx_label(self, mode, assistant_id=None):
        """
        Updates context label

        :param mode: Mode
        :param assistant_id: Assistant id
        """
        if mode is None:
            return
        mode_str = trans('mode.' + mode)
        if mode == 'assistant' and assistant_id is not None:
            assistant = self.window.controller.assistant.assistants.get_by_id(assistant_id)
            if assistant is not None:
                mode_str += ' (' + assistant.name + ')'
        # update context label
        self.set_ctx_label(mode_str)

    def set_ctx_label(self, label):
        """
        Sets context label

        :param label: label
        """
        self.window.data['chat.label'].setText(label)

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
        # lock if generating response is in progress
        if self.context_change_locked():
            return

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
