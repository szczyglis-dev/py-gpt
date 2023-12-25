#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.23 22:00:00                  #
# ================================================== #

from pygpt_net.core.utils import trans


class Ctx:
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
        self.window.app.ctx.load_meta()

        # if no context yet then create one
        if len(self.window.app.ctx.meta) == 0:
            self.new()
        else:
            # get last ctx from config
            id = self.window.app.config.get('ctx')
            if id is not None and id in self.window.app.ctx.meta:
                self.window.app.ctx.current = id
            else:
                # if no ctx then get first ctx
                self.window.app.ctx.current = self.window.app.ctx.get_first()

        # load selected ctx
        self.load(self.window.app.ctx.current)

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
        self.window.app.debug.update(True)

        # append ctx and thread id (assistants API) to config
        id = self.window.app.ctx.current
        if id is not None:
            self.window.app.config.set('ctx', id)
            self.window.app.config.set('assistant_thread', self.window.app.ctx.thread)
            self.window.app.config.save()

    def focus_chat(self):
        """Focus chat"""
        # set tab index to 0:
        self.window.ui.tabs['output'].setCurrentIndex(0)

    def select(self, id):
        """
        Select ctx

        :param id: context id
        """
        self.window.app.ctx.current = id
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

        id = self.window.app.ctx.get_id_by_idx(idx)
        self.select(id)

    def select_ctx_by_current(self):
        """Select ctx by current"""
        id = self.window.app.ctx.current
        meta = self.window.app.ctx.get_meta()
        if id in meta:
            idx = self.window.app.ctx.get_idx_by_id(id)
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

        self.window.app.ctx.new()
        self.window.app.config.set('assistant_thread', None)  # reset assistant thread id
        self.update()
        self.window.controller.output.clear()

        if not force:  # only if real click on new context button
            self.window.controller.input.unlock_input()

        # update context label
        mode = self.window.app.ctx.mode
        assistant_id = None
        if mode == 'assistant':
            assistant_id = self.window.app.config.get('assistant')
        self.update_ctx_label(mode, assistant_id)
        self.focus_chat()

    def reload(self):
        """Reload current ctx list"""
        meta = self.window.app.ctx.get_meta()
        self.window.ui.contexts.ctx_list.update('ctx.list', meta)

    def refresh(self):
        """Refresh context"""
        self.load(self.window.app.ctx.current)

    def load(self, ctx):
        """
        Load ctx data

        :param ctx: context name (id)
        """
        # select ctx
        self.window.app.ctx.select(ctx)

        # get current settings stored in ctx
        thread = self.window.app.ctx.thread
        mode = self.window.app.ctx.mode
        assistant_id = self.window.app.ctx.assistant
        preset = self.window.app.ctx.preset

        # restore thread from ctx
        self.window.app.config.set('assistant_thread', thread)

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
                    assistant_id = self.window.app.config.get('assistant')

        # reload ctx list and select current ctx on list
        self.update()

        # update current ctx label
        self.update_ctx_label(mode, assistant_id)

    def update_ctx(self):
        """Update current ctx mode if allowed"""
        mode = self.window.app.config.get('mode')

        id = None
        # update ctx mode only if current ctx is allowed for this mode
        if self.is_allowed_for_mode(mode, False):  # do not check assistant match
            self.window.app.ctx.update()

            # update current context label
            if mode == 'assistant':
                if self.window.app.ctx.assistant is not None:
                    # get assistant id from ctx if defined in ctx
                    id = self.window.app.ctx.assistant
                else:
                    # or get assistant id from current selected assistant
                    id = self.window.app.config.get('assistant')

        # update ctx label
        self.update_ctx_label(mode, id)

    def update_ctx_label_by_current(self):
        """
        Update ctx label from current ctx
        """
        mode = self.window.app.ctx.mode

        # if no ctx mode then use current mode
        if mode is None:
            mode = self.window.app.config.get('mode')

        label = trans('mode.' + mode)

        # append assistant name to ctx name label
        if mode == 'assistant':
            id = self.window.app.ctx.assistant
            assistant = self.window.app.assistants.get_by_id(id)
            if assistant is not None:
                # get ctx assistant
                label += ' (' + assistant.name + ')'
            else:
                # get current assistant
                id = self.window.app.config.get('assistant')
                assistant = self.window.app.assistants.get_by_id(id)
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
            assistant = self.window.app.assistants.get_by_id(assistant_id)
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

        id = self.window.app.ctx.get_id_by_idx(idx)
        self.window.app.ctx.remove(id)

        # reset current if current ctx deleted
        if self.window.app.ctx.current == id:
            self.window.app.ctx.current = None
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
        self.window.app.ctx.truncate()
        self.update()

    def rename(self, idx):
        """
        Ctx name rename (shows dialog)

        :param idx: context idx
        """
        id = self.window.app.ctx.get_id_by_idx(idx)
        meta = self.window.app.ctx.get_meta_by_id(id)
        self.window.ui.dialog['rename'].id = 'ctx'
        self.window.ui.dialog['rename'].input.setText(meta.name)
        self.window.ui.dialog['rename'].current = id
        self.window.ui.dialog['rename'].show()
        self.update()

    def update_name(self, id, name):
        """
        Update ctx name

        :param id: context id
        :param name: context name
        """
        if id not in self.window.app.ctx.meta:
            return
        self.window.app.ctx.meta[id].name = name
        self.window.app.ctx.set_initialized()
        self.window.app.ctx.save(id)
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
        self.window.app.ctx.add(ctx)
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
        if not self.window.app.config.get('lock_modes'):
            return True

        if self.window.app.ctx.is_empty():
            return True

        # always allow if no ctx
        id = self.window.app.config.get('ctx')
        if id is None or id == '' or not self.window.app.ctx.has(id):
            return True

        meta = self.window.app.ctx.get_meta_by_id(id)

        # always allow if no last mode
        if meta.last_mode is None:
            return True

        # get last used mode from ctx meta
        prev_mode = meta.last_mode
        if prev_mode not in self.allowed_modes[mode]:
            # exception for assistant (if assistant exists in ctx then allow)
            if mode == 'assistant':
                if meta.assistant is not None:
                    # if the same assistant then allow
                    if meta.assistant == self.window.app.config.get('assistant'):
                        return True
                else:
                    return True  # if no assistant in ctx then allow
            # if other mode, then always disallow
            return False

        # check if the same assistant
        if mode == 'assistant' and check_assistant:
            # allow if no assistant yet in ctx
            if meta.assistant is None:
                return True
            # disallow if different assistant
            if meta.assistant != self.window.app.config.get('assistant'):
                return False
        return True

    def selection_change(self):
        """
        Select ctx on list change
        """
        # TODO: implement this
        # idx = self.window.ui.nodes['ctx.list'].currentIndex().row()
        # self.select(idx)
        self.window.ui.nodes['ctx.list'].lockSelection()

    def context_change_locked(self):
        """
        Check if ctx change is locked

        :return: True if locked
        :rtype: bool
        """
        if self.window.controller.input.generating:
            return True
        return False
