#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.17 22:00:00                  #
# ================================================== #

from ..utils import trans


class Context:
    def __init__(self, window=None):
        """
        Context controller

        :param window: Window instance
        """
        self.window = window

        # modes allowed for switch from (key: from, data: to)
        self.allowed_modes = {
            'chat': ['chat', 'completion', 'img', 'langchain', 'vision', 'assistant'],
            'completion': ['chat', 'completion', 'img', 'langchain', 'vision', 'assistant'],
            'img': ['img'],
            'langchain': ['chat', 'completion', 'img', 'langchain', 'vision', 'assistant'],
            'vision': ['chat', 'completion', 'img', 'langchain', 'vision', 'assistant'],
            'assistant': ['assistant'],
        }

    def setup(self):
        """Setup ctx"""
        # load ctx list
        self.window.context.load_list()

        # if no context yet then create one
        if len(self.window.context.contexts) == 0:
            self.new()
        else:
            # get last ctx from config
            ctx = self.window.config.get('ctx')
            if ctx is not None and ctx in self.window.context.contexts:
                self.window.context.current_ctx = ctx
            else:
                # if no ctx then get first ctx
                self.window.context.current_ctx = self.window.context.get_first_ctx()

        # load selected ctx
        self.load(self.window.context.current_ctx)

    def update(self, reload=True):
        """
        Update ctx list

        :param reload: reload ctx list items
        """
        # reload ctx list items
        if reload:
            self.reload()
            self.select_ctx_by_current()  # select on list

        # update all
        self.window.controller.ui.update()
        self.window.debugger.update(True)

        # append ctx and thread id (assistants API) to config
        ctx = self.window.context.current_ctx
        if ctx is not None:
            self.window.config.set('ctx', ctx)
            self.window.config.set('assistant_thread', self.window.context.current_thread)
            self.window.config.save()

    def select(self, ctx):
        """
        Select ctx

        :param ctx: context id
        """
        self.window.context.current_ctx = ctx
        self.load(ctx)

    def select_by_idx(self, idx):
        """
        Select ctx by index

        :param idx: context index
        """
        # lock if generating response is in progress
        if self.context_change_locked():
            return

        ctx = self.window.context.get_name_by_idx(idx)
        self.select(ctx)

    def select_ctx_by_current(self):
        """Select ctx by current"""
        ctx = self.window.context.current_ctx
        items = self.window.context.get_list()
        if ctx in items:
            idx = self.window.context.get_idx_by_name(ctx)
            current = self.window.models['ctx.contexts'].index(idx, 0)
            self.window.data['ctx.contexts'].unlocked = True  # tmp allow change if locked (enable)
            self.window.data['ctx.contexts'].setCurrentIndex(current)
            self.window.data['ctx.contexts'].unlocked = False  # tmp allow change if locked (disable)

    def new(self, force=False):
        """
        Create new ctx

        :param force: force context creation
        """
        # lock if generating response is in progress
        if not force and self.context_change_locked():
            return

        self.window.context.new()
        self.window.config.set('assistant_thread', None)  # reset assistant thread id
        self.update()
        self.window.controller.output.clear()

        if not force:  # only if real click on new context button
            self.window.controller.input.unlock_input()

        # update context label
        mode = self.window.context.current_mode
        assistant_id = None
        if mode == 'assistant':
            assistant_id = self.window.config.get('assistant')
        self.update_ctx_label(mode, assistant_id)

    def reload(self):
        """Reload current ctx list"""
        items = self.window.context.get_list()
        self.window.ui.contexts.update_list('ctx.contexts', items)

    def refresh(self):
        """Refresh context"""
        self.load(self.window.context.current_ctx)

    def load(self, ctx):
        """
        Load ctx data

        :param ctx: context name (id)
        """
        # select ctx
        self.window.context.select(ctx)

        # get current settings stored in ctx
        thread = self.window.context.current_thread
        mode = self.window.context.current_mode
        assistant_id = self.window.context.current_assistant
        preset = self.window.context.current_preset

        # restore thread from ctx
        self.window.config.set('assistant_thread', thread)

        # clear before output and append ctx to output
        self.window.controller.output.clear()
        self.window.controller.output.append_context()

        # switch mode to ctx mode
        if mode is not None:
            self.window.controller.model.set_mode(mode)  # preset reset here

            # switch preset to ctx preset
            if preset is not None:
                self.window.controller.model.set_preset(mode, preset)
                self.window.controller.model.update_presets()  # update presets only

            # if ctx mode == assistant then switch assistant to ctx assistant
            if mode == 'assistant':
                # if assistant defined then select it
                if assistant_id is not None:
                    self.window.controller.assistant.select_by_id(assistant_id)
                else:
                    # if empty ctx assistant then get assistant from current selected
                    assistant_id = self.window.config.get('assistant')

        # reload ctx list and select current ctx on list
        self.update()

        # update current ctx label
        self.update_ctx_label(mode, assistant_id)

    def update_ctx(self):
        """Update current ctx mode if allowed"""
        mode = self.window.config.get('mode')

        # update ctx mode only if current ctx is allowed for this mode
        if self.is_allowed_for_mode(mode, False):  # do not check assistant match
            self.window.context.update()

            # update current context label
            id = None
            if mode == 'assistant':
                if self.window.context.current_assistant is not None:
                    # get assistant id from ctx if defined in ctx
                    id = self.window.context.current_assistant
                else:
                    # or get assistant id from current selected assistant
                    id = self.window.config.get('assistant')

            # update ctx label
            self.update_ctx_label(mode, id)

    def update_ctx_label_by_current(self):
        """
        Update ctx label from current ctx
        """
        mode = self.window.context.current_mode

        # if no ctx mode then use current mode
        if mode is None:
            mode = self.window.config.get('mode')

        label = trans('mode.' + mode)

        # append assistant name to ctx name label
        if mode == 'assistant':
            id = self.window.context.current_assistant
            assistant = self.window.controller.assistant.assistants.get_by_id(id)
            if assistant is not None:
                # get ctx assistant
                label += ' (' + assistant.name + ')'
            else:
                # get current assistant
                id = self.window.config.get('assistant')
                assistant = self.window.controller.assistant.assistants.get_by_id(id)
                if assistant is not None:
                    label += ' (' + assistant.name + ')'

        # update ctx label
        self.window.controller.ui.update_ctx_label(label)

    def update_ctx_label(self, mode, assistant_id=None):
        """
        Update ctx label

        :param mode: Mode
        :param assistant_id: Assistant id
        """
        if mode is None:
            return
        label = trans('mode.' + mode)
        if mode == 'assistant' and assistant_id is not None:
            assistant = self.window.controller.assistant.assistants.get_by_id(assistant_id)
            if assistant is not None:
                label += ' (' + assistant.name + ')'

        # update ctx label
        self.window.controller.ui.update_ctx_label(label)

    def delete(self, idx, force=False):
        """
        Delete ctx

        :param idx: context index
        :param force: force delete
        """
        if not force:
            self.window.ui.dialogs.confirm('ctx_delete', idx, trans('ctx.delete.confirm'))
            return

        ctx = self.window.context.get_name_by_idx(idx)
        self.window.context.delete_ctx(ctx)

        # reset current if current ctx deleted
        if self.window.context.current_ctx == ctx:
            self.window.context.current_ctx = None
            self.window.controller.output.clear()
        self.update()

    def delete_history(self, force=False):
        """
        Delete ctx history item

        :param force: force delete
        """
        if not force:
            self.window.ui.dialogs.confirm('ctx_delete_all', '', trans('ctx.delete.all.confirm'))
            return

        # delete all ctx
        self.window.context.delete_all_ctx()
        self.update()

    def rename(self, idx):
        """
        Ctx name rename (shows dialog)

        :param idx: context index
        """
        ctx = self.window.context.get_name_by_idx(idx)
        ctx_data = self.window.context.get_context_by_name(ctx)
        self.window.dialog['rename'].id = 'ctx'
        self.window.dialog['rename'].input.setText(ctx_data['name'])
        self.window.dialog['rename'].current = ctx
        self.window.dialog['rename'].show()
        self.update()

    def update_name(self, ctx, name):
        """
        Update ctx name

        :param ctx: context name (id)
        :param name: context name
        """
        if ctx not in self.window.context.contexts:
            return
        self.window.context.contexts[ctx]['name'] = name
        self.window.context.set_ctx_initialized()
        self.window.context.dump_context(ctx)
        self.window.dialog['rename'].close()
        self.update()

    def dismiss_rename(self):
        """Dismiss rename dialog"""
        self.window.dialog['rename'].close()

    def add(self, ctx):
        """
        Add ctx

        :param ctx: context name (id)
        """
        self.window.context.add(ctx)
        self.update()

    def handle_allowed(self, mode):
        """
        Check if ctx is allowed for this mode, if not then switch to new context

        :param mode: mode name
        :return: True if allowed
        :rtype: bool
        """
        if not self.is_allowed_for_mode(mode):
            self.new(True)  # force new context
            return False
        return True

    def is_allowed_for_mode(self, mode, check_assistant=True):
        """
        Check if ctx is allowed for this mode

        :param mode: mode name
        :param check_assistant: True if check also current assistant
        :return: True if allowed for mode
        :rtype: bool
        """
        # always allow if lock_modes is disabled
        if not self.window.config.get('lock_modes'):
            return True

        # always allow if no ctx
        ctx = self.window.config.get('ctx')
        if ctx is None or ctx == '':
            return True

        ctx_data = self.window.context.get_context_by_name(ctx)

        # always allow if no last mode
        if 'last_mode' not in ctx_data or ctx_data['last_mode'] is None:
            return True

        # get last used mode from ctx
        prev_mode = ctx_data['last_mode']
        if prev_mode not in self.allowed_modes[mode]:
            # exception for assistant (if assistant exists in ctx then allow)
            if mode == 'assistant':
                if 'assistant' in ctx_data and ctx_data['assistant'] is not None:
                    # if the same assistant then allow
                    if ctx_data['assistant'] == self.window.config.get('assistant'):
                        return True
                else:
                    return True  # if no assistant in ctx then allow
            # if other mode, then always disallow
            return False

        # check if the same assistant
        if mode == 'assistant' and check_assistant:
            # allow if no assistant yet in ctx
            if 'assistant' not in ctx_data or ctx_data['assistant'] is None:
                return True
            # disallow if different assistant
            if ctx_data['assistant'] != self.window.config.get('assistant'):
                return False
        return True

    def selection_change(self):
        """
        Select ctx on list change
        """
        # TODO: implement this
        # idx = self.window.data['ctx.contexts'].currentIndex().row()
        # self.select(idx)
        pass

    def context_change_locked(self):
        """
        Check if ctx change is locked

        :return: True if locked
        :rtype: bool
        """
        if self.window.controller.input.generating:
            return True
        return False
