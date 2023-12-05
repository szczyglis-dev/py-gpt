#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.05 10:00:00                  #
# ================================================== #
import os

from ..utils import trans
from ..assistants import Assistants


class Assistant:
    def __init__(self, window=None):
        """
        Presets controller

        :param window: main window object
        """
        self.window = window
        self.assistants = Assistants(self.window.config)

    def setup(self):
        self.assistants.load()
        self.update()

    def update_list(self):
        """Updates assistants list"""
        items = self.assistants.get_all()
        self.window.ui.toolbox.update_list_assistants('assistants', items)

    def update(self):
        self.update_list()

    def select(self, idx):
        """
        Selects assistant on the list

        :param idx: IDx on the list
        """
        # mark assistant as selected
        id = self.assistants.get_by_idx(idx)
        self.window.config.data['assistant'] = id

        # update attachments list with list of attachments from assistant
        mode = self.window.config.data['mode']
        assistant = self.assistants.get_by_id(id)
        self.window.controller.attachment.import_from_assistant(mode, assistant)
        self.window.controller.attachment.update()

    def update_field(self, id, value, assistant_id=None, current=False):
        """
        Updates assistant field from editor

        :param id: field id
        :param value: field value
        :param assistant_id: assistant ID
        :param current: if True, updates current assistant
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

        self.window.controller.ui.update()

    def edit(self, idx=None):
        """
        Opens assistant editor

        :param idx: assistant index (row index)
        """
        id = None
        if idx is not None:
            id = self.assistants.get_by_idx(idx)

        self.init_editor(id)
        self.window.ui.dialogs.open_editor('editor.assistants', idx)

    def init_editor(self, id=None):
        """
        Initializes assistant editor

        :param id: assistant ID
        """

        assistant = self.assistants.create()
        assistant.model = "gpt-4-1106-preview"  # default model

        if id is not None and id != "":
            if self.assistants.has(id):
                assistant = self.assistants.get_by_id(id)

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

        if assistant.has_tool('function'):
            self.config_toggle('assistant.tool.function', True, 'assistant.editor')
        else:
            self.config_toggle('assistant.tool.function', False, 'assistant.editor')

    def save(self):
        """
        Saves assistant
        """
        created = False
        id = self.window.config_option['assistant.id'].text()
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
        self.window.controller.model.update()
        self.update()

        self.window.ui.dialogs.close('editor.assistants')
        self.window.set_status(trans('status.assistant.saved'))

    def create(self):
        """
        Creates assistant
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

    def import_from_api(self):
        """
        Imports all remote assistants from API
        """
        try:
            items = self.assistants.get_all()
            self.window.gpt.assistant_import(items)
            self.assistants.items = items
            self.assistants.save()
        except Exception as e:
            print(e)
            self.window.ui.dialogs.alert(str(e))
        self.update()

    def assign_data(self, assistant):
        """
        Assigns data from fields to assistant

        :param assistant: assistant
        """
        assistant.name = self.window.config_option['assistant.name'].text()
        assistant.model = self.window.config_option['assistant.model'].text()
        assistant.description = self.window.config_option['assistant.description'].text()
        assistant.instructions = self.window.config_option['assistant.instructions'].toPlainText()
        assistant.tools = {
            'code_interpreter': self.window.config_option['assistant.tool.code_interpreter'].box.isChecked(),
            'retrieval': self.window.config_option['assistant.tool.retrieval'].box.isChecked(),
            'function': self.window.config_option['assistant.tool.function'].box.isChecked(),
        }

    def clear(self, force=False):
        """
        Clears assistant data

        :param force: force clear data
        """
        id = self.window.config.data['assistant']

        if not force:
            self.window.ui.dialogs.confirm('assistant_clear', '', trans('confirm.assistant.clear'))
            return

        if id is not None and id != "":
            if self.assistants.has(id):
                assistant = self.assistants.get_by_id(id)
                assistant.reset()

        self.window.set_status(trans('status.assistant.cleared'))
        self.update()

    def delete_file(self, assistant_id, file_id):
        """
        Deletes file

        :param assistant_id: assistant id
        :param file_id: file id
        """
        # delete in API
        try:
            self.window.gpt.assistant_file_delete(assistant_id, file_id)
        except Exception as e:
            self.window.ui.dialogs.alert(str(e))
            return

        # delete locally
        if assistant_id is not None and assistant_id != "":
            if self.assistants.has(assistant_id):
                assistant = self.assistants.get_by_id(assistant_id)
                if assistant.has_file(file_id):
                    assistant.delete_file(file_id)
                    self.assistants.save()
                    self.update()

    def clear_files(self, assistant_id):
        """
        Deletes all files

        :param assistant_id: assistant id
        """
        # delete all files
        if assistant_id is not None and assistant_id != "":
            if self.assistants.has(assistant_id):
                assistant = self.assistants.get_by_id(assistant_id)
                for file_id in assistant.files.keys():
                    try:
                        self.window.gpt.assistant_file_delete(assistant_id, file_id)
                        assistant.delete_file(file_id)
                    except Exception as e:
                        self.window.ui.dialogs.alert(str(e))
                self.assistants.save()
                self.update()

    def delete(self, idx=None, force=False):
        """
        Deletes assistant

        :param idx: assistant index (row index)
        :param force: force delete without confirmation
        """
        if idx is not None:
            id = self.assistants.get_by_idx(idx)
            if id is not None and id != "":
                if self.assistants.has(id):
                    # if exists then show confirmation dialog
                    if not force:
                        self.window.ui.dialogs.confirm('assistant_delete', idx, trans('confirm.assistant.delete'))
                        return

                    # clear if this is current assistant
                    if id == self.window.config.data['assistant']:
                        self.window.config.data['assistant'] = None
                        self.window.config.data['assistant_thread'] = None

                    # delete in API
                    try:
                        return self.window.gpt.assistant_delete(id)
                    except Exception as e:
                        self.window.ui.dialogs.alert(str(e))

                    self.assistants.delete(id)
                    self.update()
                    self.window.set_status(trans('status.assistant.deleted'))

    def config_toggle(self, id, value, section=None):
        """
        Toggles checkbox

        :param id: checkbox option id
        :param value: checkbox option value
        :param section: settings section
        """
        assistant_id = self.window.config.data['assistant']  # current assistant
        is_current = True
        if section == 'assistant.editor':
            assistant_id = self.window.config_option['assistant.id']  # editing assistant
            is_current = False
        self.update_field(id, value, assistant_id, is_current)
        self.window.config_option[id].box.setChecked(value)

    def config_change(self, id, value, section=None):
        """
        Changes input value

        :param id: input option id
        :param value: input option value
        :param section: settings section
        """
        # validate filename
        if id == 'assistant.id':
            self.window.config_option[id].setText(value)

        assistant_id = self.window.config.data['assistant']  # current assistant
        is_current = True
        if section == 'assistant.editor':
            assistant_id = self.window.config_option['assistant.id']  # editing assistant
            is_current = False
        self.update_field(id, value, assistant_id, is_current)
        self.window.config_option[id].setText('{}'.format(value))

    def rename_file(self, assistant_id, file_id, name):
        """
        Renames uploaded remote file name

        :param assistant_id: assistant_id
        :param file_id: file_id
        :param name: new name
        """
        self.assistants.rename_file(assistant_id, file_id, name)

    def upload_attachments(self, mode, attachments):
        """
        Uploads attachments to assistant
        """
        # get current chosen assistant
        assistant_id = self.window.config.data['assistant']
        if assistant_id is None:
            return
        assistant = self.assistants.get_by_id(assistant_id)

        # loop on attachments
        for uuid in attachments:
            attachment = attachments[uuid]
            tmp_id = attachment.uuid  # tmp id

            # check if not already uploaded (ignore already uploaded files)
            if not attachment.send:
                # check if file exists
                if not os.path.exists(attachment.path):
                    continue

                # upload file and get new ID
                file_id = self.window.gpt.assistant_file_upload(assistant_id, attachment.path)
                if file_id is not None:
                    # mark as uploaded
                    attachment.send = True
                    attachment.uuid = file_id
                    attachment.remote = file_id

                    # replace old ID with new one
                    self.window.controller.attachment.attachments.replace_id(mode, tmp_id, attachment)

                    # update assistant files list
                    assistant.files[file_id] = {
                        'id': file_id,
                        'name': attachment.name,
                        'path': attachment.path,
                    }
        # update assistants
        self.assistants.save()
        self.window.controller.attachment.update()  # update attachments UI
