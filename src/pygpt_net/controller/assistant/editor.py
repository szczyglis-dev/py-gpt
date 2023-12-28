#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.26 21:00:00                  #
# ================================================== #

from pygpt_net.utils import trans


class Editor:
    def __init__(self, window=None):
        """
        Assistants editor controller

        :param window: Window instance
        """
        self.window = window

    def edit(self, idx=None):
        """
        Open assistant editor

        :param idx: assistant index (row index)
        """
        id = None
        if idx is not None:
            id = self.window.core.assistants.get_by_idx(idx)

        self.init(id)
        self.window.ui.dialogs.open_editor('editor.assistants', idx)

    def init(self, id=None):
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

    def save(self):
        """Save assistant"""
        created = False
        id = self.window.ui.config_option['assistant.id'].text()
        name = self.window.ui.config_option['assistant.name'].text()
        model = self.window.ui.config_option['assistant.model'].text()

        # check name
        if name is None or name == "" or model is None or model == "":
            self.window.ui.dialogs.alert(trans('assistant.form.empty.fields'))
            return

        if id is None or id == "" or not self.window.core.assistants.has(id):
            assistant = self.window.controller.assistant.create()  # id created in API
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
            self.window.controller.assistant.update_data(assistant)

        # save file
        self.window.core.assistants.save()
        self.window.controller.assistant.refresh()
        self.window.controller.assistant.update()

        self.window.ui.dialogs.close('editor.assistants')
        self.window.set_status(trans('status.assistant.saved'))

        # switch to new assistant
        self.window.controller.assistant.select_by_id(id)

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
