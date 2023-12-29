#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.29 21:00:00                  #
# ================================================== #

from pygpt_net.utils import trans


class Ctx:
    def __init__(self, window=None):
        """
        Context controller

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup ctx"""
        # load ctx list
        self.window.core.ctx.load_meta()

        # if no context yet then create one
        if len(self.window.core.ctx.meta) == 0:
            self.new()
        else:
            # get last ctx from config
            id = self.window.core.config.get('ctx')
            if id is not None and id in self.window.core.ctx.meta:
                self.window.core.ctx.current = id
            else:
                # if no ctx then get first ctx
                self.window.core.ctx.current = self.window.core.ctx.get_first()

        # load selected ctx
        self.load(self.window.core.ctx.current)

        # restore search string if exists
        if self.window.core.config.has("ctx.search.string"):
            string = self.window.core.config.get("ctx.search.string")
            if string is not None and string != "":
                self.window.ui.nodes['ctx.search'].setText(string)
                self.search_string_change(string)

    def update(self, reload=True, all=True):
        """
        Update ctx list

        :param reload: reload ctx list items
        :param all: update all
        """
        # reload ctx list items
        if reload:
            self.reload(True)
            self.select_ctx_by_current()  # select on list

        # update all
        if all:
            self.window.controller.ui.update()

        # append ctx and thread id (assistants API) to config
        id = self.window.core.ctx.current
        if id is not None:
            self.window.core.config.set('ctx', id)
            self.window.core.config.set('assistant_thread', self.window.core.ctx.thread)
            self.window.core.config.save()

    def focus_chat(self):
        """Focus chat"""
        # set tab index to 0:
        self.window.ui.tabs['output'].setCurrentIndex(0)

    def select(self, id):
        """
        Select ctx

        :param id: context id
        """
        self.window.core.ctx.current = id
        self.load(id)
        self.focus_chat()

    def select_by_idx(self, idx):
        """
        Select ctx by index

        :param idx: context index
        """
        # lock if generating response is in progress
        if self.context_change_locked():
            return

        id = self.window.core.ctx.get_id_by_idx(idx)
        self.select(id)

    def select_ctx_by_current(self):
        """Select ctx by current"""
        id = self.window.core.ctx.current
        meta = self.window.core.ctx.get_meta()
        if id in meta:
            idx = self.window.core.ctx.get_idx_by_id(id)
            current = self.window.ui.models['ctx.list'].index(idx, 0)
            self.window.ui.nodes['ctx.list'].unlocked = True  # tmp allow change if locked (enable)
            self.window.ui.nodes['ctx.list'].setCurrentIndex(current)
            self.window.ui.nodes['ctx.list'].unlocked = False  # tmp allow change if locked (disable)

    def new(self, force=False):
        """
        Create new ctx

        :param force: force context creation
        """
        # lock if generating response is in progress
        if not force and self.context_change_locked():
            return

        self.window.core.ctx.new()
        self.window.core.config.set('assistant_thread', None)  # reset assistant thread id
        self.update()
        self.window.controller.output.clear()

        if not force:  # only if real click on new context button
            self.window.controller.input.unlock_input()

        # update context label
        mode = self.window.core.ctx.mode
        assistant_id = None
        if mode == 'assistant':
            assistant_id = self.window.core.config.get('assistant')
        self.update_ctx_label(mode, assistant_id)
        self.focus_chat()

    def reload(self, reload=False):
        """
        Reload current ctx list

        :param reload: reload ctx list items
        """
        meta = self.window.core.ctx.get_meta(reload)
        self.window.ui.contexts.ctx_list.update('ctx.list', meta)

    def refresh(self):
        """Refresh context"""
        self.load(self.window.core.ctx.current)

    def load(self, ctx):
        """
        Load ctx data

        :param ctx: context ID
        """
        # select ctx
        self.window.core.ctx.select(ctx)

        # get current settings stored in ctx
        thread = self.window.core.ctx.thread
        mode = self.window.core.ctx.mode
        assistant_id = self.window.core.ctx.assistant
        preset = self.window.core.ctx.preset

        # restore thread from ctx
        self.window.core.config.set('assistant_thread', thread)

        # clear before output and append ctx to output
        self.window.controller.output.clear()
        self.window.controller.output.append_context()

        # switch mode to ctx mode
        if mode is not None:
            self.window.controller.mode.set(mode)  # preset reset here

            # switch preset to ctx preset
            if preset is not None:
                self.window.controller.presets.set(mode, preset)
                self.window.controller.presets.refresh()  # update presets only

            # if ctx mode == assistant then switch assistant to ctx assistant
            if mode == 'assistant':
                # if assistant defined then select it
                if assistant_id is not None:
                    self.window.controller.assistant.select_by_id(assistant_id)
                else:
                    # if empty ctx assistant then get assistant from current selected
                    assistant_id = self.window.core.config.get('assistant')

        # reload ctx list and select current ctx on list
        self.update()

        # update current ctx label
        self.update_ctx_label(mode, assistant_id)

    def update_ctx(self):
        """Update current ctx mode if allowed"""
        mode = self.window.core.config.get('mode')

        id = None
        # update ctx mode only if current ctx is allowed for this mode
        if self.window.core.ctx.is_allowed_for_mode(mode, False):  # do not check assistant match
            self.window.core.ctx.update()

            # update current context label
            if mode == 'assistant':
                if self.window.core.ctx.assistant is not None:
                    # get assistant id from ctx if defined in ctx
                    id = self.window.core.ctx.assistant
                else:
                    # or get assistant id from current selected assistant
                    id = self.window.core.config.get('assistant')

        # update ctx label
        self.update_ctx_label(mode, id)

    def update_ctx_label_by_current(self):
        """Update ctx label from current ctx"""
        mode = self.window.core.ctx.mode

        # if no ctx mode then use current mode
        if mode is None:
            mode = self.window.core.config.get('mode')

        label = trans('mode.' + mode)

        # append assistant name to ctx name label
        if mode == 'assistant':
            id = self.window.core.ctx.assistant
            assistant = self.window.core.assistants.get_by_id(id)
            if assistant is not None:
                # get ctx assistant
                label += ' (' + assistant.name + ')'
            else:
                # get current assistant
                id = self.window.core.config.get('assistant')
                assistant = self.window.core.assistants.get_by_id(id)
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
            assistant = self.window.core.assistants.get_by_id(assistant_id)
            if assistant is not None:
                label += ' (' + assistant.name + ')'

        # update ctx label
        self.window.controller.ui.update_ctx_label(label)

    def delete(self, idx, force=False):
        """
        Delete ctx by idx

        :param idx: context idx
        :param force: force delete
        """
        if not force:
            self.window.ui.dialogs.confirm('ctx_delete', idx, trans('ctx.delete.confirm'))
            return

        id = self.window.core.ctx.get_id_by_idx(idx)
        self.window.core.ctx.remove(id)

        # reset current if current ctx deleted
        if self.window.core.ctx.current == id:
            self.window.core.ctx.current = None
            self.window.controller.output.clear()
        self.update()

    def delete_history(self, force=False):
        """
        Delete all ctx / truncate

        :param force: force delete
        """
        if not force:
            self.window.ui.dialogs.confirm('ctx_delete_all', '', trans('ctx.delete.all.confirm'))
            return

        # truncate ctx
        self.window.core.ctx.truncate()
        self.update()

    def rename(self, idx):
        """
        Ctx name rename (shows dialog)

        :param idx: context idx
        """
        id = self.window.core.ctx.get_id_by_idx(idx)
        meta = self.window.core.ctx.get_meta_by_id(id)
        self.window.ui.dialog['rename'].id = 'ctx'
        self.window.ui.dialog['rename'].input.setText(meta.name)
        self.window.ui.dialog['rename'].current = id
        self.window.ui.dialog['rename'].show()
        self.update()

    def update_name(self, id, name, close=True):
        """
        Update ctx name

        :param id: context id
        :param name: context name
        :param close: close dialog
        """
        if id not in self.window.core.ctx.meta:
            return
        self.window.core.ctx.meta[id].name = name
        self.window.core.ctx.set_initialized()
        self.window.core.ctx.save(id)
        if close:
            self.window.ui.dialog['rename'].close()
        self.update()

    def dismiss_rename(self):
        """Dismiss rename dialog"""
        self.window.ui.dialog['rename'].close()

    def add(self, ctx):
        """
        Add ctx item (CtxItem object)

        :param ctx: CtxItem
        """
        self.window.core.ctx.add(ctx)
        self.update()

    def handle_allowed(self, mode):
        """
        Check if ctx is allowed for this mode, if not then switch to new context

        :param mode: mode name
        :return: True if allowed
        :rtype: bool
        """
        if not self.window.core.ctx.is_allowed_for_mode(mode):
            self.new(True)  # force new context
            return False
        return True

    def selection_change(self):
        """Select ctx on list change"""
        # TODO: implement this
        # idx = self.window.ui.nodes['ctx.list'].currentIndex().row()
        # self.select(idx)
        self.window.ui.nodes['ctx.list'].lockSelection()

    def search_string_change(self, text):
        """
        Search string change

        :param text: search string
        """
        self.window.core.ctx.search_string = text
        self.window.core.config.set('ctx.search.string', text)
        self.update(reload=True, all=False)

    def context_change_locked(self):
        """
        Check if ctx change is locked

        :return: True if locked
        :rtype: bool
        """
        if self.window.controller.input.generating:
            return True
        return False
