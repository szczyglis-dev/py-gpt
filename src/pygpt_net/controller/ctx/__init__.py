#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.27 19:00:00                  #
# ================================================== #

from PySide6.QtCore import QModelIndex

from pygpt_net.core.dispatcher import Event
from pygpt_net.core.access.events import AppEvent
from pygpt_net.item.ctx import CtxItem

from .common import Common
from .summarizer import Summarizer
from .extra import Extra

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
        self.extra = Extra(window)

        # current edit IDs
        self.edit_meta_id = None
        self.edit_item_id = None

        # current group ID
        self.group_id = None

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

        self.window.ui.nodes['ctx.list'].collapseAll()  # collapse all items at start
        self.restore_expanded_groups()  # restore expanded groups

    def update(self, reload: bool = True, all: bool = True, select: bool = True):
        """
        Update ctx list

        :param reload: reload ctx list items
        :param all: update all
        :param select: select current ctx
        """
        # reload ctx list items
        if reload:
            self.update_list(True)

        # select current ctx on list
        if select:
            self.select_by_current()

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
            self.window.core.dispatcher.dispatch(AppEvent(AppEvent.CTX_SELECTED))  # app event
        else:
            # only update current group if defined
            meta = self.window.core.ctx.get_meta_by_id(id)
            if meta is not None:
                self.set_group(meta.group_id)
        self.common.focus_chat()

    def select_by_idx(self, idx: int):
        """
        Select ctx by index

        :param idx: context index
        """
        self.select_by_id(self.window.core.ctx.get_id_by_idx(idx))

    def select_by_id(self, id: int):
        """
        Select ctx by index

        :param id: context index
        """
        # lock if generating response is in progress
        if self.context_change_locked():
            return

        self.select(id)
        event = Event(Event.CTX_SELECT, {
            'value': id,
        })
        self.window.core.dispatcher.dispatch(event)

    def select_by_current(self, focus: bool = False):
        """
        Select ctx by current

        :param focus: focus chat
        """
        id = self.window.core.ctx.current
        meta = self.window.core.ctx.get_meta()
        if id in meta:
            self.select_index_by_id(id)
        if focus:
            self.update()
            index = self.get_child_index_by_id(id)
            if index.isValid():
                self.window.ui.nodes['ctx.list'].scrollTo(index)

    def unselect(self):
        """Unselect ctx"""
        self.set_group(None)
        self.window.ui.nodes['ctx.list'].clearSelection()

    def set_group(self, group_id: int = None):
        """
        Set current selected group

        :param group_id: group ID
        """
        self.group_id = group_id

    def search_focus_in(self):
        """Search focus handler"""
        pass
        # self.select_by_current()

    def new_ungrouped(self):
        """Create new ungrouped ctx"""
        self.group_id = None
        self.new()

    def new(self, force: bool = False, group_id: int = None):
        """
        Create new ctx

        :param force: force context creation
        :param group_id: group ID
        """
        # lock if generating response is in progress
        if not force and self.context_change_locked():
            return

        # use currently selected group if not defined
        if group_id is None:
            if self.group_id is not None and self.group_id > 0:
                group_id = self.group_id
        else:
            self.group_id = group_id

        # check if group exists
        if group_id is not None and not self.window.core.ctx.has_group(group_id):
            group_id = None
            self.group_id = None

        self.window.core.ctx.new(group_id)
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
            self.window.controller.assistant.files.update()  # always update assistant files

        self.common.update_label(mode, assistant_id)
        self.common.focus_chat()

        # app event
        self.window.core.dispatcher.dispatch(AppEvent(AppEvent.CTX_CREATED))

    def add(self, ctx: CtxItem):
        """
        Add ctx item (CtxItem object)

        :param ctx: CtxItem
        """
        self.window.core.ctx.add(ctx)
        self.update()

    def prev(self):
        """Select previous ctx"""
        id = self.window.core.ctx.get_prev()
        if id is not None:
            self.select(id)

    def next(self):
        """Select next ctx"""
        id = self.window.core.ctx.get_next()
        if id is not None:
            self.select(id)

    def last(self):
        """Select last (newest) ctx"""
        id = self.window.core.ctx.get_last_meta()
        if id is not None:
            self.select(id)

    def update_list(self, reload: bool = False):
        """
        Reload current ctx list

        :param reload: reload ctx list items
        """
        self.window.ui.contexts.ctx_list.update(
            'ctx.list',
            self.window.core.ctx.get_meta(reload),
        )

    def refresh(self, restore_model: bool = True):
        """
        Refresh context

        :param restore_model: restore model
        """
        self.load(
            self.window.core.ctx.current,
            restore_model,
        )

    def refresh_output(self):
        """Refresh output"""
        # append ctx to output
        self.window.controller.chat.render.append_context(
            self.window.core.ctx.items,
            clear=True,
        )

    def load(self, id: int, restore_model: bool = True):
        """
        Load ctx data

        :param id: context ID
        :param restore_model: restore model if defined in ctx
        """
        # select ctx by id
        self.window.core.ctx.thread = None  # reset thread id
        self.window.core.ctx.select(id, restore_model=restore_model)
        meta = self.window.core.ctx.get_meta_by_id(id)
        if meta is not None:
            self.set_group(meta.group_id)  # set current group if defined

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
                self.window.controller.assistant.files.update()  # always update assistant files

            # switch model to ctx model if model is defined in ctx and model is available for this mode
            if model is not None and self.window.core.models.has_model(mode, model):
                self.window.controller.model.set(mode, model)

        # reload ctx list and select current ctx on list, without reloading all
        self.update(reload=False, all=True)

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

    def delete(self, id: int, force: int = False):
        """
        Delete ctx by idx

        :param id: context id
        :param force: force delete
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='ctx.delete',
                id=id,
                msg=trans('ctx.delete.confirm'),
            )
            return

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
        self.group_id = None
        self.unselect()
        self.window.core.ctx.truncate()
        self.window.core.history.truncate()
        self.update()
        self.new()

    def delete_history_groups(self, force: bool = False):
        """
        Delete all ctx / truncate

        :param force: force delete
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='ctx.delete_all_groups',
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
        self.group_id = None
        self.unselect()
        self.window.core.ctx.truncate()
        self.window.core.history.truncate()
        self.window.core.ctx.truncate_groups()
        self.update()
        self.new()

    def new_if_empty(self):
        """Create new context if empty"""
        self.group_id = None
        if self.window.core.ctx.count_meta() == 0:
            self.new()

    def rename(self, id: int):
        """
        Ctx name rename by id (show dialog)

        :param id: context id
        """
        meta = self.window.core.ctx.get_meta_by_id(id)
        self.window.ui.dialog['rename'].id = 'ctx'
        self.window.ui.dialog['rename'].input.setText(meta.name)
        self.window.ui.dialog['rename'].current = id
        self.window.ui.dialog['rename'].show()
        self.update()

    def set_important(self, id: int, value: bool = True):
        """
        Set as important

        :param id: context idx
        :param value: important value
        """
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

    def set_label(self, id: int, label_id: int):
        """
        Set color label for ctx by idx

        :param id: context idx
        :param label_id: label id
        """
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

    def update_name_current(self, name: str):
        """
        Update current ctx name

        :param name: context name
        """
        self.update_name(self.window.core.ctx.current, name)

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
        selected_idx = self.window.ui.nodes['ctx.list'].currentIndex()
        if selected_idx.isValid():
            id = self.window.core.ctx.get_id_by_idx(selected_idx.row())
        self.window.ui.nodes['ctx.list'].lockSelection()

    def search_string_change(self, text: str):
        """
        Search string changed handler

        :param text: search string
        """
        self.window.core.ctx.clear_tmp_meta()
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
        self.window.core.ctx.clear_tmp_meta()
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

    def select_index_by_id(self, id):
        """
        Select item by ID on context list

        :param id: ctx meta ID
        """
        index = self.get_child_index_by_id(id)
        self.window.ui.nodes['ctx.list'].unlocked = True  # tmp allow change if locked (enable)
        self.window.ui.nodes['ctx.list'].setCurrentIndex(index)
        self.window.ui.nodes['ctx.list'].unlocked = False  # tmp allow change if locked (disable)

    def find_index_by_id(self, item, id):
        """
        Return index of item with given ID, searching recursively through the model.

        :param item: QStandardItem
        :param id: int
        :return: QModelIndex
        """
        if hasattr(item, 'id') and item.id == id:
            return item.index()
        for row in range(item.rowCount()):
            found_index = self.find_index_by_id(item.child(row), id)
            if found_index.isValid():
                return found_index
        return QModelIndex()

    def find_parent_index_by_id(self, item, id):
        """
        Return index of item with given ID, searching recursively through the model.

        :param item: QStandardItem
        :param id: int
        :return: QModelIndex
        """
        if hasattr(item, 'id') and hasattr(item, 'isFolder') and item.isFolder and item.id == id:
            return item.index()
        for row in range(item.rowCount()):
            found_index = self.find_parent_index_by_id(item.child(row), id)
            if found_index.isValid():
                return found_index
        return QModelIndex()

    def get_parent_index_by_id(self, id):
        """
        Return QModelIndex of parent item based on its ID.

        :param id: int
        :return: QModelIndex
        """
        model = self.window.ui.models['ctx.list']
        root = model.invisibleRootItem()
        return self.find_parent_index_by_id(root, id)

    def get_children_index_by_id(self, parent_id, child_id):
        """
        Return QModelIndex of child item based on its ID and parent ID.

        :param parent_id: int
        :param child_id: int
        :return: QModelIndex
        """
        model = self.window.ui.models['ctx.list']
        parent_index = self.get_parent_index_by_id(parent_id)
        if not parent_index.isValid():
            # no parent found
            return QModelIndex()

        parent_item = model.itemFromIndex(parent_index)
        return self.find_index_by_id(parent_item, child_id)

    def find_child_index_by_id(self, root_item, child_id):
        """
        Find and return QModelIndex of child based on its ID, recursively searching through the model.

        :param root_item: QStandardItem
        :param child_id: int
        :return: QModelIndex
        """
        for row in range(root_item.rowCount()):
            item = root_item.child(row)
            if hasattr(item, 'id') and hasattr(item, 'isFolder') and not item.isFolder and item.id == child_id:
                return item.index()
            child_index = self.find_child_index_by_id(item, child_id)
            if child_index.isValid():
                return child_index
        return QModelIndex()

    def get_child_index_by_id(self, child_id):
        """
        Return QModelIndex of child item based on its ID.

        :param child_id: int
        :return: QModelIndex
        """
        model = self.window.ui.models['ctx.list']
        root_item = model.invisibleRootItem()
        return self.find_child_index_by_id(root_item, child_id)

    def store_expanded_groups(self):
        """
        Store expanded groups in ctx list
        """
        expanded = []
        for group_id in self.window.ui.nodes['ctx.list'].expanded_items:
            expanded.append(group_id)
        self.window.core.config.set('ctx.list.expanded', expanded)
        self.window.core.config.save()

    def restore_expanded_groups(self):
        """
        Restore expanded groups in ctx list
        """
        expanded = self.window.core.config.get('ctx.list.expanded')
        if expanded is not None:
            for group_id in expanded:
                self.window.ui.nodes['ctx.list'].expand_group(group_id)

    def save_all(self):
        """Save visible ctx list items"""
        self.store_expanded_groups()

    def move_to_group(self, meta_id, group_id, update: bool = True):
        """
        Move ctx to group

        :param meta_id: int
        :param group_id: int
        :param update: update ctx list
        """
        self.window.core.ctx.update_meta_group_id(meta_id, group_id)
        self.group_id = group_id
        if update:
            self.update()

    def remove_from_group(self, meta_id):
        """
        Remove ctx from group

        :param meta_id: int
        """
        self.window.core.ctx.update_meta_group_id(meta_id, None)
        self.group_id = None
        self.update()

    def new_group(self, meta_id = None):
        """
        Open new group dialog

        :param meta_id: int
        """
        self.window.ui.dialog['create'].id = 'ctx.group'
        self.window.ui.dialog['create'].input.setText("")
        self.window.ui.dialog['create'].current = meta_id
        self.window.ui.dialog['create'].show()
        self.window.ui.dialog['create'].input.setFocus()

    def create_group(self, name: str = None, meta_id = None):
        """
        Make directory

        :param name: name of directory
        :param meta_id: int
        """
        if name is None:
            self.window.update_status(
                "[ERROR] Name is empty."
            )
            return
        group = self.window.core.ctx.make_group(name)
        id = self.window.core.ctx.insert_group(group)
        if id is not None:
            if meta_id is not None:
                self.move_to_group(meta_id, id, update=False)
            self.update()
            self.window.update_status(
                "Group '{}' created.".format(name)
            )
            self.window.ui.dialog['create'].close()

            # select new group
            self.select_group(id)
            self.group_id = id

    def rename_group(self, id: int, force: bool = False):
        """
        Rename group

        :param id: group ID
        :param force: force rename
        """
        if not force:
            group = self.window.core.ctx.get_group_by_id(id)
            if group is None:
                return
            self.window.ui.dialog['rename'].id = 'ctx.group'
            self.window.ui.dialog['rename'].input.setText(group.name)
            self.window.ui.dialog['rename'].current = id
            self.window.ui.dialog['rename'].show()

    def update_group_name(self, id: int, name: str, close: bool = True):
        """
        Update group name

        :param id: group ID
        :param name: group name
        :param close: close rename dialog
        """
        group = self.window.core.ctx.get_group_by_id(id)
        if group is not None:
            group.name = name
            self.window.core.ctx.update_group(group)
            if close:
                self.window.ui.dialog['rename'].close()
            self.update(True, False, False)
            self.select_group(id)

    def get_group_name(self, id: int) -> str:
        """
        Get group name by ID

        :param id: group ID
        :return: group name
        """
        group = self.window.core.ctx.get_group_by_id(id)
        if group is not None:
            return group.name
        return ""

    def select_group(self, id: int):
        """
        Select group

        :param id: group ID
        """
        self.group_id = id
        index = self.get_parent_index_by_id(id)
        self.window.ui.nodes['ctx.list'].unlocked = True  # tmp allow change if locked (enable)
        self.window.ui.nodes['ctx.list'].setCurrentIndex(index)
        self.window.ui.nodes['ctx.list'].unlocked = False  # tmp allow change if locked (disable)

    def delete_group(self, id: int, force: bool = False):
        """
        Delete group only

        :param id: group ID
        :param force: force delete
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='ctx.group.delete',
                id=id,
                msg=trans('confirm.ctx.delete')
            )
            return
        group = self.window.core.ctx.get_group_by_id(id)
        if group is not None:
            self.window.core.ctx.remove_group(group, all=False)
            if self.group_id == id:
                self.group_id = None
            self.update()

    def delete_group_all(self, id: int, force: bool = False):
        """
        Delete group with all items

        :param id: group ID
        :param force: force delete
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='ctx.group.delete.all',
                id=id,
                msg=trans('confirm.ctx.delete.all')
            )
            return
        group = self.window.core.ctx.get_group_by_id(id)
        if group is not None:
            self.window.core.ctx.remove_group(group, all=True)
            if self.group_id == id:
                self.group_id = None
            self.update()

    def reload(self):
        """Reload ctx"""
        self.window.core.ctx.reset()
        self.setup()
        self.update()
        self.refresh()

    def reload_after(self):
        """After reload"""
        self.new_if_empty()
