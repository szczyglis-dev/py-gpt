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
import os
import threading
import time
import webbrowser

from PySide6.QtCore import QObject, Signal, Slot

from ..utils import trans
from ..assistants import Assistants


class Assistant:
    def __init__(self, window=None):
        """
        Assistants controller

        :param window: Window instance
        """
        self.window = window
        self.assistants = Assistants(self.window.config)
        self.thread_run = None
        self.thread_run_started = False
        self.force_stop = False

    def setup(self):
        """Setup assistants"""
        self.assistants.load()
        self.update()

    def update(self, update_list=True):
        """
        Update assistants list

        :param update_list: update list
        """
        if update_list:
            self.update_list()
        self.window.controller.assistant_files.update_uploaded()
        self.select_assistant_by_current()

    def update_list(self):
        """Update assistants list"""
        items = self.assistants.get_all()
        self.window.ui.toolbox.update_list_assistants('assistants', items)

    def assistant_change_locked(self):
        """
        Check if assistant change is locked

        :return: true if locked
        :rtype: bool
        """
        if self.window.controller.input.generating:
            return True
        return False

    def select(self, idx):
        """
        Select assistant on the list

        :param idx: idx on the list
        """
        # check if change is not locked
        if self.assistant_change_locked():
            return

        # mark assistant as selected
        id = self.assistants.get_by_idx(idx)
        self.select_by_id(id)

    def select_by_id(self, id):
        """
        Select assistant on the list

        :param id: assistant ID
        """
        self.window.config.set('assistant', id)

        # update attachments list with list of attachments from assistant
        mode = self.window.config.get('mode')
        assistant = self.assistants.get_by_id(id)
        self.window.controller.attachment.import_from_assistant(mode, assistant)
        self.window.controller.attachment.update()
        self.update(False)

        # update model if exists in assistant
        if assistant is not None:
            model = assistant.model
            if model is not None and model != "":
                if model in self.window.config.models:
                    self.window.config.set('model', model)
                    self.window.config.data['current_model'][mode] = model
                    self.update_assistants()

    def update_field(self, id, value, assistant_id=None, current=False):
        """
        Update assistant field from editor

        :param id: field id
        :param value: field value
        :param assistant_id: assistant ID
        :param current: if true, updates current assistant
        """
        if assistant_id is not None and assistant_id != "":
            if self.assistants.has(assistant_id):
                assistant = self.assistants.get_by_id(assistant_id)
                if id == 'assistant.name':
                    assistant.name = value
                elif id == 'assistant.description':
                    assistant.description = value
                elif id == 'assistant.instructions':
                    assistant.instructions = value
                elif id == 'assistant.model':
                    assistant.model = value

    def edit(self, idx=None):
        """
        Open assistant editor

        :param idx: assistant index (row index)
        """
        id = None
        if idx is not None:
            id = self.assistants.get_by_idx(idx)

        self.init_editor(id)
        self.window.ui.dialogs.open_editor('editor.assistants', idx)

    def init_editor(self, id=None):
        """
        Initialize assistant editor

        :param id: assistant ID
        """
        assistant = self.assistants.create()
        assistant.model = "gpt-4-1106-preview"  # default model

        # if editing existing assistant
        if id is not None and id != "":
            if self.assistants.has(id):
                assistant = self.assistants.get_by_id(id)
        else:
            # default instructions
            assistant.instructions = 'You are a helpful assistant.'

        if assistant.name is None:
            assistant.name = ""
        if assistant.description is None:
            assistant.description = ""
        if assistant.instructions is None:
            assistant.instructions = ""
        if assistant.model is None:
            assistant.model = ""

        self.window.config_option['assistant.id'].setText(id)
        self.config_change('assistant.name', assistant.name, 'assistant.editor')
        self.config_change('assistant.description', assistant.description, 'assistant.editor')
        self.config_change('assistant.instructions', assistant.instructions, 'assistant.editor')
        self.config_change('assistant.model', assistant.model, 'assistant.editor')

        if assistant.has_tool('code_interpreter'):
            self.config_toggle('assistant.tool.code_interpreter', True, 'assistant.editor')
        else:
            self.config_toggle('assistant.tool.code_interpreter', False, 'assistant.editor')

        if assistant.has_tool('retrieval'):
            self.config_toggle('assistant.tool.retrieval', True, 'assistant.editor')
        else:
            self.config_toggle('assistant.tool.retrieval', False, 'assistant.editor')

        # restore functions
        if assistant.has_functions():
            functions = assistant.get_functions()
            values = []
            for function in functions:
                values.append({"name": function['name'], "params": function['params'], "desc": function['desc']})
            self.window.config_option['assistant.tool.function'].items = values
            self.window.config_option['assistant.tool.function'].model.updateData(values)
        else:
            self.window.config_option['assistant.tool.function'].items = []
            self.window.config_option['assistant.tool.function'].model.updateData([])

        # set focus to name field
        self.window.config_option['assistant.name'].setFocus()

    def save(self):
        """
        Save assistant
        """
        created = False
        id = self.window.config_option['assistant.id'].text()
        name = self.window.config_option['assistant.name'].text()
        model = self.window.config_option['assistant.model'].text()

        # check name
        if name is None or name == "" or model is None or model == "":
            self.window.ui.dialogs.alert(trans('assistant.form.empty.fields'))
            return

        if id is None or id == "" or not self.assistants.has(id):
            assistant = self.create()  # id created in API
            if assistant is None:
                print("Assistant not created")
                return
            id = assistant.id
            self.assistants.add(assistant)
            self.window.config_option['assistant.id'].setText(id)
            created = True
        else:
            assistant = self.assistants.get_by_id(id)

        # assign data from fields to assistant
        self.assign_data(assistant)

        # update in API
        if not created:
            self.assistant_update(assistant)

        # save file
        self.assistants.save()
        self.update_assistants()
        self.update()

        self.window.ui.dialogs.close('editor.assistants')
        self.window.set_status(trans('status.assistant.saved'))

    def create(self):
        """
        Create assistant
        """
        assistant = self.assistants.create()
        self.assign_data(assistant)
        try:
            return self.window.gpt.assistant_create(assistant)
        except Exception as e:
            self.window.ui.dialogs.alert(str(e))

    def assistant_update(self, assistant):
        """
        Update assistant
        """
        self.assign_data(assistant)
        try:
            return self.window.gpt.assistant_update(assistant)
        except Exception as e:
            self.window.ui.dialogs.alert(str(e))

    def import_assistants(self, force=False):
        """
        Import all remote assistants from API

        :param force: if true, imports without confirmation
        """
        if not force:
            self.window.ui.dialogs.confirm('assistant_import', '',
                                           trans('confirm.assistant.import'))
            return

        try:
            # import assistants
            items = self.assistants.get_all()
            self.window.gpt.assistant_import(items)
            self.assistants.items = items
            self.assistants.save()

            # import uploaded files
            for id in self.assistants.items:
                assistant = self.assistants.get_by_id(id)
                self.window.controller.assistant_files.import_files(assistant)
            # status
            self.window.set_status("Imported assistants: " + str(len(items)))
        except Exception as e:
            print("Error importing assistants")
            print(e)
            self.window.ui.dialogs.alert(str(e))
        self.update()

    def assign_data(self, assistant):
        """
        Assign data from fields to assistant

        :param assistant: assistant
        """
        assistant.name = self.window.config_option['assistant.name'].text()
        assistant.model = self.window.config_option['assistant.model'].text()
        assistant.description = self.window.config_option['assistant.description'].text()
        assistant.instructions = self.window.config_option['assistant.instructions'].toPlainText()
        assistant.tools = {
            'code_interpreter': self.window.config_option['assistant.tool.code_interpreter'].box.isChecked(),
            'retrieval': self.window.config_option['assistant.tool.retrieval'].box.isChecked(),
            'function': [],  # functions are assigned separately
        }

        # assign assistant's functions tool
        functions = []
        for function in self.window.config_option['assistant.tool.function'].items:
            name = function['name']
            params = function['params']
            desc = function['desc']
            if name is None or name == "":
                continue
            if params is None or params == "":
                params = '{"type": "object", "properties": {}}'
            if desc is None:
                desc = ""
            functions.append({"name": name, "params": params, "desc": desc})
        if len(functions) > 0:
            assistant.tools['function'] = functions
        else:
            assistant.tools['function'] = []

    def clear(self, force=False):
        """
        Clear assistant data

        :param force: force clear data
        """
        id = self.window.config.get('assistant')

        if not force:
            self.window.ui.dialogs.confirm('assistant_clear', '',
                                           trans('confirm.assistant.clear'))
            return

        if id is not None and id != "":
            if self.assistants.has(id):
                assistant = self.assistants.get_by_id(id)
                assistant.reset()

        self.window.set_status(trans('status.assistant.cleared'))
        self.update()

    def delete(self, idx=None, force=False):
        """
        Delete assistant

        :param idx: assistant index (row index)
        :param force: force delete without confirmation
        """
        if idx is not None:
            id = self.assistants.get_by_idx(idx)
            if id is not None and id != "":
                if self.assistants.has(id):
                    # if exists then show confirmation dialog
                    if not force:
                        self.window.ui.dialogs.confirm('assistant_delete', idx,
                                                       trans('confirm.assistant.delete'))
                        return

                    # clear if this is current assistant
                    if id == self.window.config.get('assistant'):
                        self.window.config.set('assistant', None)
                        self.window.config.set('assistant_thread', None)

                    # delete in API
                    try:
                        self.window.gpt.assistant_delete(id)
                    except Exception as e:
                        self.window.ui.dialogs.alert(str(e))

                    self.assistants.delete(id)
                    self.update()
                    self.window.set_status(trans('status.assistant.deleted'))

    def config_toggle(self, id, value, section=None):
        """
        Toggle checkbox

        :param id: checkbox option id
        :param value: checkbox option value
        :param section: settings section
        """
        assistant_id = self.window.config.get('assistant')  # current assistant
        is_current = True
        if section == 'assistant.editor':
            assistant_id = self.window.config_option['assistant.id']  # editing assistant
            is_current = False
        self.update_field(id, value, assistant_id, is_current)

    def config_change(self, id, value, section=None):
        """
        Change input value

        :param id: input option id
        :param value: input option value
        :param section: settings section
        """
        # validate filename
        if id == 'assistant.id':
            self.window.config_option[id].setText(value)

        assistant_id = self.window.config.get('assistant')  # current assistant
        is_current = True
        if section == 'assistant.editor':
            assistant_id = self.window.config_option['assistant.id']  # editing assistant
            is_current = False
        self.update_field(id, value, assistant_id, is_current)
        self.window.config_option[id].setText('{}'.format(value))

    def goto_online(self):
        """Opens Assistants page"""
        webbrowser.open('https://platform.openai.com/assistants')

    def create_thread(self):
        """
        Create assistant thread

        :return: thread_id
        :rtype: str
        """
        thread_id = self.window.gpt.assistant_thread_create()
        self.window.config.set('assistant_thread', thread_id)
        self.window.gpt.context.append_thread(thread_id)
        return thread_id

    def select_assistant_by_current(self):
        """Select assistant by current"""
        assistant_id = self.window.config.get('assistant')
        items = self.window.controller.assistant.assistants.get_all()
        if assistant_id in items:
            idx = list(items.keys()).index(assistant_id)
            current = self.window.models['assistants'].index(idx, 0)
            self.window.data['assistants'].setCurrentIndex(current)

    def select_default_assistant(self):
        """Set default assistant"""
        assistant = self.window.config.get('assistant')
        if assistant is None or assistant == "":
            mode = self.window.config.get('mode')
            if mode == 'assistant':
                self.window.config.set('assistant', self.assistants.get_default_assistant())
                self.update()

    def update_assistants(self):
        """Update assistants"""
        self.select_default_assistant()

    def handle_run_messages(self, ctx):
        """
        Handle run messages

        :param ctx: ContextItem
        """
        data = self.window.gpt.assistant_msg_list(ctx.thread)
        for msg in data:
            if msg.role == "assistant":
                ctx.set_output(msg.content[0].text.value)
                self.window.controller.assistant_files.handle_message_files(msg)
                self.window.controller.input.handle_response(ctx, 'assistant', False)
                self.window.controller.input.handle_commands(ctx)
                break

    def handle_run(self, ctx):
        """
        Handle assistant's run

        :param ctx: ContextItem
        """
        listener = AssistantRunThread(window=self.window, ctx=ctx)
        listener.updated.connect(self.handle_status)
        listener.destroyed.connect(self.handle_destroy)
        listener.started.connect(self.handle_started)

        self.thread_run = threading.Thread(target=listener.run)
        self.thread_run.start()
        self.thread_run_started = True

    @Slot(str, object)
    def handle_status(self, status, ctx):
        """
        Insert text to input and send

        :param status: status
        :param ctx: ContextItem
        """
        print("Run status: {}".format(status))
        if status != "queued" and status != "in_progress":
            self.window.controller.input.unlock_input()  # unlock input
        if status == "completed":
            self.force_stop = False
            self.handle_run_messages(ctx)
            self.window.statusChanged.emit(trans('assistant.run.completed'))
        elif status == "failed":
            self.force_stop = False
            self.window.controller.input.unlock_input()
            self.window.statusChanged.emit(trans('assistant.run.failed'))

    @Slot()
    def handle_destroy(self):
        """
        Insert text to input and send
        """
        self.thread_run_started = False
        self.force_stop = False

    @Slot()
    def handle_started(self):
        """
        Handle listening started
        """
        print("Run: assistant is listening status...")
        self.window.statusChanged.emit(trans('assistant.run.listening'))


class AssistantRunThread(QObject):
    updated = Signal(object, object)
    destroyed = Signal()
    started = Signal()

    def __init__(self, window=None, ctx=None):
        """
        Run assistant run status check thread

        :param window: Window instance
        :param ctx: ContextItem
        """
        super().__init__()
        self.window = window
        self.ctx = ctx
        self.check = True
        self.stop_reasons = [
            "cancelling",
            "cancelled",
            "failed",
            "completed",
            "expired",
            "requires_action",
        ]

    def run(self):
        """Run thread"""
        try:
            self.started.emit()
            while self.check \
                    and not self.window.is_closing \
                    and not self.window.controller.assistant.force_stop:
                status = self.window.gpt.assistant_run_status(self.ctx.thread, self.ctx.run_id)
                self.updated.emit(status, self.ctx)
                # finished or failed
                if status in self.stop_reasons:
                    self.check = False
                    self.destroyed.emit()
                    break
                time.sleep(1)
            self.destroyed.emit()
        except Exception as e:
            print(e)
            self.destroyed.emit()
