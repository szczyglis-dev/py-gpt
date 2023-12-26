#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.25 21:00:00                  #
# ================================================== #

import webbrowser

from pygpt_net.utils import trans


class Assistant:
    def __init__(self, window=None):
        """
        Assistants controller

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup assistants"""
        self.window.core.assistants.load()
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
        items = self.window.core.assistants.get_all()
        self.window.ui.toolbox.assistants.update(items)

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
        id = self.window.core.assistants.get_by_idx(idx)
        self.select_by_id(id)

    def select_by_id(self, id):
        """
        Select assistant on the list

        :param id: assistant ID
        """
        self.window.core.config.set('assistant', id)

        # update attachments list with list of attachments from assistant
        mode = self.window.core.config.get('mode')
        assistant = self.window.core.assistants.get_by_id(id)
        self.window.controller.attachment.import_from_assistant(mode, assistant)
        self.window.controller.attachment.update()
        self.update(False)

        # update model if exists in assistant
        if assistant is not None:
            model = assistant.model
            if model is not None and model != "":
                if model in self.window.core.models.items:
                    self.window.core.config.set('model', model)
                    self.window.core.config.data['current_model'][mode] = model
                    self.update_assistants()

        self.window.controller.ctx.update_ctx()  # update current ctx info

    def select_assistant_by_current(self):
        """Select assistant by current"""
        assistant_id = self.window.core.config.get('assistant')
        items = self.window.core.assistants.get_all()
        if assistant_id in items:
            idx = list(items.keys()).index(assistant_id)
            current = self.window.ui.models['assistants'].index(idx, 0)
            self.window.ui.nodes['assistants'].setCurrentIndex(current)

    def select_default_assistant(self):
        """Set default assistant"""
        assistant = self.window.core.config.get('assistant')
        if assistant is None or assistant == "":
            mode = self.window.core.config.get('mode')
            if mode == 'assistant':
                self.window.core.config.set('assistant', self.window.core.assistants.get_default_assistant())
                self.update()

    def update_assistants(self):
        """Update assistants"""
        self.select_default_assistant()

    def update_field(self, id, value, assistant_id=None, current=False):
        """
        Update assistant field from editor

        :param id: field id
        :param value: field value
        :param assistant_id: assistant ID
        :param current: if true, updates current assistant
        """
        if assistant_id is not None and assistant_id != "":
            if self.window.core.assistants.has(assistant_id):
                assistant = self.window.core.assistants.get_by_id(assistant_id)
                if id == 'assistant.name':
                    assistant.name = value
                elif id == 'assistant.description':
                    assistant.description = value
                elif id == 'assistant.instructions':
                    assistant.instructions = value
                elif id == 'assistant.model':
                    assistant.model = value

    def init_editor(self, id=None):
        """
        Initialize assistant editor

        :param id: assistant ID
        """
        assistant = self.window.core.assistants.create()
        assistant.model = "gpt-4-1106-preview"  # default model

        # if editing existing assistant
        if id is not None and id != "":
            if self.window.core.assistants.has(id):
                assistant = self.window.core.assistants.get_by_id(id)
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

        self.window.ui.config_option['assistant.id'].setText(id)
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
            self.window.ui.config_option['assistant.tool.function'].items = values
            self.window.ui.config_option['assistant.tool.function'].model.updateData(values)
        else:
            self.window.ui.config_option['assistant.tool.function'].items = []
            self.window.ui.config_option['assistant.tool.function'].model.updateData([])

        # set focus to name field
        self.window.ui.config_option['assistant.name'].setFocus()

    def edit(self, idx=None):
        """
        Open assistant editor

        :param idx: assistant index (row index)
        """
        id = None
        if idx is not None:
            id = self.window.core.assistants.get_by_idx(idx)

        self.init_editor(id)
        self.window.ui.dialogs.open_editor('editor.assistants', idx)

    def save(self):
        """
        Save assistant
        """
        created = False
        id = self.window.ui.config_option['assistant.id'].text()
        name = self.window.ui.config_option['assistant.name'].text()
        model = self.window.ui.config_option['assistant.model'].text()

        # check name
        if name is None or name == "" or model is None or model == "":
            self.window.ui.dialogs.alert(trans('assistant.form.empty.fields'))
            return

        if id is None or id == "" or not self.window.core.assistants.has(id):
            assistant = self.create()  # id created in API
            if assistant is None:
                print("Assistant not created")
                return
            id = assistant.id
            self.window.core.assistants.add(assistant)
            self.window.ui.config_option['assistant.id'].setText(id)
            created = True
        else:
            assistant = self.window.core.assistants.get_by_id(id)

        # assign data from fields to assistant
        self.assign_data(assistant)

        # update in API
        if not created:
            self.assistant_update(assistant)

        # save file
        self.window.core.assistants.save()
        self.update_assistants()
        self.update()

        self.window.ui.dialogs.close('editor.assistants')
        self.window.set_status(trans('status.assistant.saved'))

        # switch to new assistant
        self.select_by_id(id)

    def create(self):
        """
        Create assistant
        """
        assistant = self.window.core.assistants.create()
        self.assign_data(assistant)
        try:
            return self.window.core.gpt.assistants.create(assistant)
        except Exception as e:
            self.window.core.debug.log(e)
            self.window.ui.dialogs.alert(str(e))

    def assistant_update(self, assistant):
        """
        Update assistant
        """
        self.assign_data(assistant)
        try:
            return self.window.core.gpt.assistants.update(assistant)
        except Exception as e:
            self.window.core.debug.log(e)
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
            items = self.window.core.assistants.get_all()
            self.window.core.gpt.assistants.import_assistants(items)
            self.window.core.assistants.items = items
            self.window.core.assistants.save()

            # import uploaded files
            for id in self.window.core.assistants.items:
                assistant = self.window.core.assistants.get_by_id(id)
                self.window.controller.assistant_files.import_files(assistant)
            # status
            self.window.set_status("Imported assistants: " + str(len(items)))
        except Exception as e:
            self.window.core.debug.log(e)
            print("Error importing assistants")
            self.window.ui.dialogs.alert(str(e))
        self.update()

    def assign_data(self, assistant):
        """
        Assign data from fields to assistant

        :param assistant: assistant
        """
        assistant.name = self.window.ui.config_option['assistant.name'].text()
        assistant.model = self.window.ui.config_option['assistant.model'].text()
        assistant.description = self.window.ui.config_option['assistant.description'].text()
        assistant.instructions = self.window.ui.config_option['assistant.instructions'].toPlainText()
        assistant.tools = {
            'code_interpreter': self.window.ui.config_option['assistant.tool.code_interpreter'].box.isChecked(),
            'retrieval': self.window.ui.config_option['assistant.tool.retrieval'].box.isChecked(),
            'function': [],  # functions are assigned separately
        }

        # assign assistant's functions tool
        functions = []
        for function in self.window.ui.config_option['assistant.tool.function'].items:
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
        id = self.window.core.config.get('assistant')

        if not force:
            self.window.ui.dialogs.confirm('assistant_clear', '',
                                           trans('confirm.assistant.clear'))
            return

        if id is not None and id != "":
            if self.window.core.assistants.has(id):
                assistant = self.window.core.assistants.get_by_id(id)
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
            id = self.window.core.assistants.get_by_idx(idx)
            if id is not None and id != "":
                if self.window.core.assistants.has(id):
                    # if exists then show confirmation dialog
                    if not force:
                        self.window.ui.dialogs.confirm('assistant_delete', idx,
                                                       trans('confirm.assistant.delete'))
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
                    self.window.set_status(trans('status.assistant.deleted'))

    def config_toggle(self, id, value, section=None):
        """
        Toggle checkbox

        :param id: checkbox option id
        :param value: checkbox option value
        :param section: settings section
        """
        assistant_id = self.window.core.config.get('assistant')  # current assistant
        is_current = True
        if section == 'assistant.editor':
            assistant_id = self.window.ui.config_option['assistant.id']  # editing assistant
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
            self.window.ui.config_option[id].setText(value)

        assistant_id = self.window.core.config.get('assistant')  # current assistant
        is_current = True
        if section == 'assistant.editor':
            assistant_id = self.window.ui.config_option['assistant.id']  # editing assistant
            is_current = False
        self.update_field(id, value, assistant_id, is_current)
        self.window.ui.config_option[id].setText('{}'.format(value))

    def goto_online(self):
        """Opens Assistants page"""
        webbrowser.open('https://platform.openai.com/assistants')
