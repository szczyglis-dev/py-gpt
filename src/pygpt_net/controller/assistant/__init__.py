#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.18 18:00:00                  #
# ================================================== #

import webbrowser

from pygpt_net.controller.assistant.editor import Editor
from pygpt_net.controller.assistant.files import Files
from pygpt_net.controller.assistant.threads import Threads
from pygpt_net.item.assistant import AssistantItem

from pygpt_net.utils import trans


class Assistant:
    def __init__(self, window=None):
        """
        Assistant controller

        :param window: Window instance
        """
        self.window = window
        self.editor = Editor(window)
        self.files = Files(window)
        self.threads = Threads(window)

    def setup(self):
        """Setup assistants"""
        self.window.core.assistants.load()
        self.editor.setup()
        self.update()

    def update(self, update_list: bool = True):
        """
        Update assistants list

        :param update_list: update list
        """
        if update_list:
            self.update_list()
        self.window.controller.assistant.files.update_list()
        self.select_current()

    def update_list(self):
        """Update assistants list"""
        items = self.window.core.assistants.get_all()
        self.window.ui.toolbox.assistants.update(items)

    def run_stop(self):
        """Stop assistant run"""
        ctx = self.window.core.ctx.last_item
        if ctx is not None:
            if ctx.run_id is not None and ctx.thread is not None:
                print("Stopping Run: ", ctx.run_id)
                status = self.window.core.gpt.assistants.run_stop(ctx)
                if status == "cancelling":
                    print("Run has been canceled.")

    def prepare(self):
        """Prepare assistants"""
        # create or get current thread, it is required before conversation start
        if self.window.core.config.get('assistant_thread') is None:
            try:
                self.window.ui.status(trans('status.starting'))
                self.window.core.config.set('assistant_thread', self.threads.create_thread())
            except Exception as e:
                self.window.core.debug.log(e)
                self.window.ui.dialogs.alert(str(e))

    def refresh(self):
        """Update assistants"""
        self.select_default()

    def select(self, idx: int):
        """
        Select assistant on the list

        :param idx: idx on the list
        """
        # check if change is not locked
        if self.change_locked():
            return

        # mark assistant as selected
        id = self.window.core.assistants.get_by_idx(idx)
        self.select_by_id(id)

    def select_by_id(self, id: str):
        """
        Select assistant on the list

        :param id: assistant ID
        """
        self.window.core.config.set('assistant', id)

        # update attachments list with list of attachments from assistant
        mode = self.window.core.config.get('mode')
        assistant = self.window.core.assistants.get_by_id(id)
        self.window.controller.attachment.import_from_assistant(
            mode,
            assistant,
        )
        self.window.controller.attachment.update()
        self.update(False)

        # update model if exists in assistant
        if assistant is not None:
            model = assistant.model
            if model is not None and model != "":
                if model in self.window.core.models.items:
                    self.window.core.config.set('model', model)
                    self.window.core.config.data['current_model'][mode] = model
                    self.window.controller.model.set(mode, model)
                    self.window.controller.model.update_list()
                    self.window.controller.model.select_current()
            self.window.ui.nodes['preset.prompt'].setPlainText(assistant.instructions)
            self.refresh()

        self.window.controller.ctx.update_ctx()  # update current ctx info

    def from_global(self):
        """Update current preset from global prompt"""
        id = self.window.core.config.get('assistant')
        if id is not None and id != "":
            if self.window.core.assistants.has(id):
                assistant = self.window.core.assistants.get_by_id(id)
                assistant.instructions = self.window.core.config.get('prompt')

    def select_current(self):
        """Select assistant by current"""
        assistant_id = self.window.core.config.get('assistant')
        items = self.window.core.assistants.get_all()
        if assistant_id in items:
            idx = list(items.keys()).index(assistant_id)
            current = self.window.ui.models['assistants'].index(idx, 0)
            self.window.ui.nodes['assistants'].setCurrentIndex(current)
            self.window.core.config.set('prompt', items[assistant_id].instructions)
            self.window.ui.nodes['preset.prompt'].setPlainText(items[assistant_id].instructions)

    def select_default(self):
        """Set default assistant"""
        assistant = self.window.core.config.get('assistant')
        if assistant is None or assistant == "":
            mode = self.window.core.config.get('mode')
            if mode == 'assistant':
                self.window.core.config.set(
                    'assistant',
                    self.window.core.assistants.get_default_assistant(),
                )
                self.update()

    def create(self) -> AssistantItem:
        """
        Create assistant in API

        :return: AssistantItem
        """
        assistant = self.window.core.assistants.create()
        self.editor.assign_data(assistant)
        try:
            return self.window.core.gpt.assistants.create(assistant)
        except Exception as e:
            self.window.core.debug.log(e)
            self.window.ui.dialogs.alert(str(e))

    def update_data(self, assistant: AssistantItem):
        """Update assistant"""
        self.editor.assign_data(assistant)
        try:
            return self.window.core.gpt.assistants.update(assistant)
        except Exception as e:
            self.window.core.debug.log(e)
            self.window.ui.dialogs.alert(str(e))

    def import_api(self, force: bool = False):
        """
        Import all remote assistants from API

        :param force: if true, imports without confirmation
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='assistant_import',
                id='',
                msg=trans('confirm.assistant.import'),
            )
            return

        # run asynchronous
        self.window.ui.status("Importing assistants...please wait...")
        self.window.core.assistants.importer.import_assistants()

    def handle_imported_assistants(self, num: int):
        """
        Handle imported assistants

        :param num: number of imported assistants
        """
        self.window.ui.status("OK. Imported assistants: " + str(num) + ".")
        self.update()

    def handle_imported_assistants_failed(self, error: any):
        """
        Handle error on importing assistants

        :param error: error message
        """
        self.window.core.debug.log(error)
        print("Error importing assistants")
        self.window.ui.dialogs.alert(str(error))
        self.update()

    def clear(self, force: bool = False):
        """
        Clear assistant data

        :param force: force clear data
        """
        id = self.window.core.config.get('assistant')

        if not force:
            self.window.ui.dialogs.confirm(
                type='assistant_clear',
                id='',
                msg=trans('confirm.assistant.clear'),
            )
            return

        if id is not None and id != "":
            if self.window.core.assistants.has(id):
                assistant = self.window.core.assistants.get_by_id(id)
                assistant.reset()

        self.window.ui.status(trans('status.assistant.cleared'))
        self.update()

    def delete(self, idx: int = None, force: bool = False):
        """
        Delete assistant

        :param idx: assistant index (row index)
        :param force: force delete without confirmation
        """
        if idx is not None:
            id = self.window.core.assistants.get_by_idx(idx)
            if id is not None and id != "":
                if self.window.core.assistants.has(id):
                    # if exists then show confirmation dialog
                    if not force:
                        self.window.ui.dialogs.confirm(
                            type='assistant_delete',
                            id=idx,
                            msg=trans('confirm.assistant.delete'),
                        )
                        return

                    # clear if this is current assistant
                    if id == self.window.core.config.get('assistant'):
                        self.window.core.config.set('assistant', None)
                        self.window.core.config.set('assistant_thread', None)

                    # delete in API
                    try:
                        self.window.core.gpt.assistants.delete(id)
                    except Exception as e:
                        self.window.ui.dialogs.alert(str(e))

                    self.window.core.assistants.delete(id)
                    self.update()
                    self.window.ui.status(trans('status.assistant.deleted'))

    def goto_online(self):
        """Open Assistants page"""
        webbrowser.open('https://platform.openai.com/assistants')

    def change_locked(self) -> bool:
        """
        Check if assistant change is locked

        :return: True if locked
        """
        return self.window.controller.chat.input.generating
