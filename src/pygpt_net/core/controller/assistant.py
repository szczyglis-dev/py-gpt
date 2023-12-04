#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.04 20:00:00                  #
# ================================================== #

from ..utils import trans


class Assistant:
    def __init__(self, window=None):
        """
        Presets controller

        :param window: main window object
        """
        self.window = window

    def update_field(self, id, value, assistant_id=None, current=False):
        """
        Updates assistant field from editor

        :param id: field id
        :param value: field value
        :param assistant: assistant ID
        :param current: if True, updates current assistant
        """
        if assistant_id is not None and assistant_id != "":
            if assistant_id in self.window.config.assistants:
                if id == 'assistant.name':
                    self.window.config.assistants[assistant_id]['name'] = value
                elif id == 'assistant.description':
                    self.window.config.assistants[assistant_id]['description'] = value
                elif id == 'assistant.instructions':
                    self.window.config.assistants[assistant_id]['instructions'] = value
                elif id == 'assistant.model':
                    self.window.config.assistants[assistant_id]['model'] = value

        self.window.controller.ui.update()

    def edit(self, idx=None):
        """
        Opens assistant editor

        :param idx: assistant index (row index)
        """
        id = None
        if idx is not None:
            id = self.window.config.get_assistant_by_idx(idx)

        self.init_editor(id)
        self.window.ui.dialogs.open_editor('editor.assistants', idx)

    def init_editor(self, id=None):
        """
        Initializes assistant editor

        :param id: assistant ID
        """
        data = {}
        data['name'] = ""
        data['description'] = ""
        data['instructions'] = ""
        data['model'] = "gpt-4-1106-preview"
        data['tool.code_interpreter'] = False
        data['tool.retrieval'] = False
        data['tool.function'] = False

        if id is not None and id != "":
            if id in self.window.config.assistants:
                data = self.window.config.assistants[id]
                data['id'] = id
        if data['name'] is None:
            data['name'] = ""
        if data['description'] is None:
            data['description'] = ""
        if data['model'] is None:
            data['model'] = ""
        if data['instructions'] is None:
            data['instructions'] = ""

        self.window.config_option['assistant.id'].setText(id)

        self.config_change('assistant.name', data['name'], 'assistant.editor')
        self.config_change('assistant.description', data['description'], 'assistant.editor')
        self.config_change('assistant.instructions', data['instructions'], 'assistant.editor')
        self.config_change('assistant.model', data['model'], 'assistant.editor')

        if 'tool.code_interpreter' in data:
            self.config_toggle('assistant.tool.code_interpreter', data['tool.code_interpreter'], 'assistant.editor')
        if 'tool.retrieval' in data:
            self.config_toggle('assistant.tool.retrieval', data['tool.retrieval'], 'assistant.editor')
        if 'tool.function' in data:
            self.config_toggle('assistant.tool.function', data['tool.function'], 'assistant.editor')

    def save(self, force=False):
        """
        Saves assistant

        :param force: force overwrite file
        """
        create = False
        id = self.window.config_option['assistant.id'].text()
        if id is None or id == "" or id not in self.window.config.assistants:
            id = self.create()
            if id is None:
                print("Assistant not created")
                return
            self.window.config.assistants[id] = {}
            self.window.config_option['assistant.id'].setText(id)
            create = True

        # assign data from fields to preset
        self.assign_data(id)

        # update in API
        if not create:
            self.assistent_update(id)

        # save file
        self.window.config.save_assistants()
        self.window.controller.model.update()
        self.update()

        self.window.ui.dialogs.close('editor.assistants')
        self.window.set_status(trans('status.assistant.saved'))

    def create(self):
        """
        Creates assistant
        """
        name = self.window.config_option['assistant.name'].text()
        model = self.window.config_option['assistant.model'].text()
        description = self.window.config_option['assistant.description'].text()
        instructions = self.window.config_option['assistant.instructions'].toPlainText()
        tool_code_interpreter = self.window.config_option['assistant.tool.code_interpreter'].box.isChecked()
        tool_retrieval = self.window.config_option['assistant.tool.retrieval'].box.isChecked()
        tool_function = self.window.config_option['assistant.tool.function'].box.isChecked()

        tools = []
        if tool_code_interpreter:
            tools.append({"type": "code_interpreter"})
        if tool_retrieval:
            tools.append({"type": "retrieval"})
        if tool_function:
            tools.append({"type": "function"})

        try:
            return self.window.gpt.assistant_create(name, model, description, instructions, tools)
        except Exception as e:
            self.window.ui.dialogs.alert(str(e))

    def assistent_update(self, id):
        """
        Updated assistant
        """
        name = self.window.config_option['assistant.name'].text()
        model = self.window.config_option['assistant.model'].text()
        description = self.window.config_option['assistant.description'].text()
        instructions = self.window.config_option['assistant.instructions'].toPlainText()
        tool_code_interpreter = self.window.config_option['assistant.tool.code_interpreter'].box.isChecked()
        tool_retrieval = self.window.config_option['assistant.tool.retrieval'].box.isChecked()
        tool_function = self.window.config_option['assistant.tool.function'].box.isChecked()

        tools = []
        if tool_code_interpreter:
            tools.append({"type": "code_interpreter"})
        if tool_retrieval:
            tools.append({"type": "retrieval"})
        if tool_function:
            tools.append({"type": "function"})

        try:
            return self.window.gpt.assistant_update(id, name, model, description, instructions, tools)
        except Exception as e:
            self.window.ui.dialogs.alert(str(e))

    def import_all(self):
        """
        Imports all assistants
        """
        try:
            self.window.gpt.assistant_import()
        except Exception as e:
            print(e)
            self.window.ui.dialogs.alert(str(e))
        self.update()

    def assign_data(self, id):
        """
        Assigns data from fields to assistant

        :param id: assistant ID
        """
        self.window.config.assistants[id]['id'] = id
        self.window.config.assistants[id]['name'] = self.window.config_option['assistant.name'].text()
        self.window.config.assistants[id]['model'] = self.window.config_option['assistant.model'].text()
        self.window.config.assistants[id]['description'] = self.window.config_option['assistant.description'].text()
        self.window.config.assistants[id]['instructions'] = self.window.config_option['assistant.instructions'].toPlainText()
        self.window.config.assistants[id]['files'] = {}
        self.window.config.assistants[id]['tools'] = {
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
            if id in self.window.config.assistants:
                self.window.config.assistants[id]['name'] = ""
                self.window.config.assistants[id]['model'] = ""
                self.window.config.assistants[id]['description'] = ""
                self.window.config.assistants[id]['instructions'] = ""
                self.window.controller.model.update()

        self.window.set_status(trans('status.assistant.cleared'))
        self.update()

    def delete(self, idx=None, force=False):
        """
        Deletes assistant

        :param idx: assistant index (row index)
        :param force: force delete without confirmation
        """
        if idx is not None:
            id = self.window.config.get_assistant_by_idx(idx)
            if id is not None and id != "":
                if id in self.window.config.assistants:
                    # if exists then show confirmation dialog
                    if not force:
                        self.window.ui.dialogs.confirm('assistant_delete', idx, trans('confirm.assistant.delete'))
                        return

                    if id == self.window.config.data['assistant']:
                        self.window.config.data['assistant'] = None
                        self.window.config.data['assistant_thread'] = None

                    # delete in API
                    try:
                        return self.window.gpt.assistant_delete(id)
                    except Exception as e:
                        self.window.ui.dialogs.alert(str(e))

                    self.window.config.delete_assistant(id)
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

    def select(self, idx):
        """
        Selects assistant

        :param idx: IDx on the list
        """
        # mark assistant as selected
        id = self.window.config.get_assistant_by_idx(idx)
        self.window.config.data['assistant'] = id

        # update attachments list with list of attachments from assistant
        self.window.controller.attachment.attachments.from_assistant(id)
        self.window.controller.attachment.update()

    def update_list_assistants(self):
        """Updates assistants list"""
        # update model
        items = self.window.config.get_assistants()
        self.window.ui.toolbox.update_list('assistants', items)

    def update(self):
        self.update_list_assistants()

    def setup(self):
        self.update()
