#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.06 02:00:00                  #
# ================================================== #

from pygpt_net.controller.ctx.common import Common
from pygpt_net.controller.ctx.summarizer import Summarizer
from pygpt_net.core.dispatcher import Event
from pygpt_net.item.ctx import CtxItem

from pygpt_net.utils import trans


class Ctx:
    def __init__(self, window=None):
        """
        Context controller

        :param window: Window instance
        """
        self.window = window
        self.common = Common(window)
        self.summarizer = Summarizer(window)

    def setup(self):
        """Setup ctx"""
        self.common.restore_display_filter()  # load filters first

        # load ctx list
        self.window.core.ctx.load_meta()

        # if no context yet then create one
        if self.window.core.ctx.count_meta() == 0:
            self.new()
        else:
            # get last ctx from config
            id = self.window.core.config.get('ctx')
            if id is not None and self.window.core.ctx.has(id):
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
                # check if current selected ctx is still valid
                if self.window.core.ctx.current is not None:
                    if not self.window.core.ctx.has(self.window.core.ctx.current):
                        self.search_string_clear()
                        # ^ clear search and reload ctx list to prevent creating new ctx

    def update(self, reload: bool = True, all: bool = True):
        """
        Update ctx list

        :param reload: reload ctx list items
        :param all: update all
        """
        # reload ctx list items
        if reload:
            self.reload(True)
            self.select_by_current()  # select on list

        # update all
        if all:
            self.window.controller.ui.update()

        # append ctx and thread id (assistants API) to config
        id = self.window.core.ctx.current
        if id is not None:
            self.window.core.config.set('ctx', id)
            self.window.core.config.set('assistant_thread', self.window.core.ctx.thread)
            self.window.core.config.save()

        # update calendar ctx list
        self.window.controller.calendar.update(all=False)

    def select(self, id: int):
        """
        Select ctx by id

        :param id: context id
        """
        prev_id = self.window.core.ctx.current
        self.window.core.ctx.current = id

        if prev_id != id:
            self.load(id)
        self.common.focus_chat()

    def select_by_idx(self, idx: int):
        """
        Select ctx by index

        :param idx: context index
        """
        # lock if generating response is in progress
        if self.context_change_locked():
            return

        id = self.window.core.ctx.get_id_by_idx(idx)
        self.select(id)

        event = Event(Event.CTX_SELECT, {
            'value': id,
        })
        self.window.core.dispatcher.dispatch(event)

    def select_by_current(self):
        """Select ctx by current"""
        id = self.window.core.ctx.current
        meta = self.window.core.ctx.get_meta()
        if id in meta:
            idx = self.window.core.ctx.get_idx_by_id(id)
            current = self.window.ui.models['ctx.list'].index(idx, 0)
            self.window.ui.nodes['ctx.list'].unlocked = True  # tmp allow change if locked (enable)
            self.window.ui.nodes['ctx.list'].setCurrentIndex(current)
            self.window.ui.nodes['ctx.list'].unlocked = False  # tmp allow change if locked (disable)

    def new(self, force: bool = False):
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

        # reset appended data
        self.window.controller.chat.render.reset()
        self.window.controller.chat.render.clear_output()

        if not force:  # only if real click on new context button
            self.window.controller.chat.common.unlock_input()
            self.window.ui.nodes['input'].setFocus()  # set focus to input

        # update context label
        mode = self.window.core.ctx.mode
        assistant_id = None
        if mode == 'assistant':
            assistant_id = self.window.core.config.get('assistant')
        self.common.update_label(mode, assistant_id)
        self.common.focus_chat()

    def add(self, ctx: CtxItem):
        """
        Add ctx item (CtxItem object)

        :param ctx: CtxItem
        """
        self.window.core.ctx.add(ctx)
        self.update()

    def reload(self, reload: bool = False):
        """
        Reload current ctx list

        :param reload: reload ctx list items
        """
        self.window.ui.contexts.ctx_list.update(
            'ctx.list',
            self.window.core.ctx.get_meta(reload),
        )

    def refresh(self):
        """Refresh context"""
        self.load(self.window.core.ctx.current)

    def refresh_output(self):
        """Refresh output"""
        # append ctx to output
        self.window.controller.chat.render.append_context(
            self.window.core.ctx.items,
            clear=True,
        )

    def load(self, id: int):
        """
        Load ctx data

        :param id: context ID
        """
        # select ctx by id
        self.window.core.ctx.select(id)

        # reset appended data
        self.window.controller.chat.render.reset()

        # get current settings stored in ctx
        thread = self.window.core.ctx.thread
        mode = self.window.core.ctx.mode
        model = self.window.core.ctx.model
        assistant_id = self.window.core.ctx.assistant
        preset = self.window.core.ctx.preset

        # restore thread from ctx
        self.window.core.config.set('assistant_thread', thread)

        # clear before output and append ctx to output
        self.refresh_output()

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

            # switch model to ctx model if model is defined in ctx and model is available for this mode
            if model is not None and self.window.core.models.has_model(mode, model):
                self.window.controller.model.set(mode, model)

        # reload ctx list and select current ctx on list
        self.update()

        # update current ctx label in UI
        self.common.update_label(mode, assistant_id)

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
        self.common.update_label(mode, id)

    def delete(self, idx: int, force: int = False):
        """
        Delete ctx by idx

        :param idx: context idx
        :param force: force delete
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='ctx.delete',
                id=idx,
                msg=trans('ctx.delete.confirm'),
            )
            return

        id = self.window.core.ctx.get_id_by_idx(idx)

        # delete data from indexes if exists
        try:
            self.delete_meta_from_idx(id)
        except Exception as e:
            self.window.core.debug.log(e)
            print("Error deleting ctx data from indexes", e)

        # delete ctx items from db
        items = self.window.core.ctx.all()
        self.window.core.history.remove_items(items)  # remove txt history items
        self.window.core.ctx.remove(id)  # remove ctx from db

        # reset current if current ctx deleted
        if self.window.core.ctx.current == id:
            self.window.core.ctx.current = None
            self.window.controller.chat.render.clear_output()
        self.update()

    def delete_meta_from_idx(self, id: int):
        """
        Delete meta from indexes

        :param id: ctx meta id
        """
        meta = self.window.core.ctx.get_meta_by_id(id)
        if meta is None:
            return

        # check if ctx is indexed
        if meta.indexed is not None and meta.indexed > 0:
            for store_id in list(meta.indexes):
                for idx in list(meta.indexes[store_id]):
                    self.window.core.ctx.idx.remove_meta_from_indexed(store_id, id, idx)

    def delete_item(self, id: int, force: bool = False):
        """
        Delete ctx item by id

        :param id: ctx item id
        :param force: force delete
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='ctx.delete_item',
                id=id,
                msg=trans('ctx.delete.item.confirm'),
            )
            return
        self.window.core.ctx.remove_item(id)
        self.refresh()
        self.update()

    def delete_history(self, force: bool = False):
        """
        Delete all ctx / truncate

        :param force: force delete
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='ctx.delete_all',
                id='',
                msg=trans('ctx.delete.all.confirm'),
            )
            return

        # truncate index db if exists
        try:
            self.window.core.idx.ctx.truncate()
        except Exception as e:
            self.window.core.debug.log(e)
            print("Error truncating ctx index db", e)

        # truncate ctx and history
        self.window.core.ctx.truncate()
        self.window.core.history.truncate()
        self.update()
        self.new()

    def rename(self, idx: int):
        """
        Ctx name rename (show dialog)

        :param idx: context idx
        """
        id = self.window.core.ctx.get_id_by_idx(idx)
        meta = self.window.core.ctx.get_meta_by_id(id)
        self.window.ui.dialog['rename'].id = 'ctx'
        self.window.ui.dialog['rename'].input.setText(meta.name)
        self.window.ui.dialog['rename'].current = id
        self.window.ui.dialog['rename'].show()
        self.update()

    def set_important(self, idx: int, value: bool = True):
        """
        Set as important

        :param idx: context idx
        :param value: important value
        """
        id = self.window.core.ctx.get_id_by_idx(idx)
        meta = self.window.core.ctx.get_meta_by_id(id)
        if meta is not None:
            meta.important = value
            self.window.core.ctx.save(id)
            self.update()

    def is_important(self, idx: int) -> bool:
        """
        Check if ctx is important

        :param idx: context idx
        :return: True if important
        """
        id = self.window.core.ctx.get_id_by_idx(idx)
        meta = self.window.core.ctx.get_meta_by_id(id)
        if meta is not None:
            return meta.important
        return False

    def set_label(self, idx: int, label_id: int):
        """
        Set color label for ctx by idx

        :param idx: context idx
        :param label_id: label id
        """
        id = self.window.core.ctx.get_id_by_idx(idx)
        meta = self.window.core.ctx.get_meta_by_id(id)
        if meta is not None:
            meta.label = label_id
            self.window.core.ctx.save(id)
            self.update()

    def update_name(
            self,
            id: int,
            name: str,
            close: bool = True,
            refresh: bool = True
    ):
        """
        Update ctx name

        :param id: context id
        :param name: context name
        :param close: close rename dialog
        :param refresh: refresh ctx list
        """
        if id not in self.window.core.ctx.get_meta():
            return
        self.window.core.ctx.meta[id].name = name
        self.window.core.ctx.set_initialized()
        self.window.core.ctx.save(id)
        if close:
            self.window.ui.dialog['rename'].close()

        if refresh:
            self.update()
        else:
            self.update(True, False)

    def handle_allowed(self, mode: str) -> bool:
        """
        Check if append to current ctx is allowed for this mode, if not then switch to new context

        :param mode: mode name
        :return: True if allowed
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

    def search_string_change(self, text: str):
        """
        Search string changed handler

        :param text: search string
        """
        self.window.core.ctx.search_string = text
        self.window.core.config.set('ctx.search.string', text)
        self.update(reload=True, all=False)

    def search_string_clear(self):
        """Search string clear"""
        self.window.ui.nodes['ctx.search'].clear()
        self.search_string_change("")  # clear search

    def append_search_string(self, text: str):
        """
        Append search string to input and make search

        :param text: search string
        """
        self.window.ui.nodes['ctx.search'].setText(text)
        self.search_string_change(text)  # make search

    def label_filters_changed(self, labels: list):
        """
        Filters labels change

        :param labels: list of labels
        """
        self.window.core.ctx.filters_labels = labels
        self.window.core.config.set('ctx.records.filter.labels', labels)
        self.update(reload=True, all=False)


    def prepare_name(self, ctx: CtxItem):
        """
        Handle context name (summarize first input and output)

        :param ctx: CtxItem
        """
        # if ctx is not initialized yet then summarize
        if not self.window.core.ctx.is_initialized():
            self.summarizer.summarize(
                self.window.core.ctx.current,
                ctx,
            )

    def context_change_locked(self) -> bool:
        """
        Check if ctx change is locked

        :return: True if locked
        """
        return self.window.controller.chat.input.generating
