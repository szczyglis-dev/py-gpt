#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.20 00:00:00                  #
# ================================================== #

import copy

from PySide6.QtWidgets import QApplication

from pygpt_net.item.assistant import AssistantItem
from pygpt_net.utils import trans


class Editor:
    def __init__(self, window=None):
        """
        Assistants editor controller

        :param window: Window instance
        """
        self.window = window
        self.options = {
            "id": {
                "type": "text",
                "label": "assistant.id",
                "read_only": True,
            },
            "name": {
                "type": "text",
                "label": "assistant.name",
            },
            "description": {
                "type": "text",
                "label": "assistant.description",
            },
            "model": {
                "type": "combo",
                "use": "models",
                "keys": [],
                "label": "assistant.model",
            },
            "instructions": {
                "type": "textarea",
                "label": "assistant.instructions",
            },
            "vector_store": {
                "type": "combo",
                "label": "assistant.vector_store",
            },
            "tool.code_interpreter": {
                "type": "bool",
                "label": "assistant.tool.code_interpreter",
                "value": True,
            },
            "tool.file_search": {
                "type": "bool",
                "label": "assistant.tool.file_search",
                "value": False,
            },
            "tool.function": {
                "type": "dict",
                "label": "assistant.tool.function",
                "keys": {
                    'name': 'text',
                    'params': 'textarea',
                    'desc': 'textarea',
                },
            },
        }
        self.id = "assistant"
        self.current = None

    def get_options(self) -> dict:
        """
        Get options list

        :return: options dict
        """
        return self.options

    def get_option(self, key: str) -> dict:
        """
        Get option by key

        :param key: option key
        :return: option dict
        """
        if key in self.options:
            return self.options[key]

    def setup(self):
        """Setup editor"""
        parent = "assistant"
        key = "tool.function"
        self.window.ui.dialogs.register_dictionary(
            key,
            parent,
            self.get_option(key),
        )
        self.update_store_list()  # vector store list

    def update_store_list(self):
        """Update vector store list"""
        items = {}
        items["--"] = "--"  # none
        current_idx = 0
        current_id = self.get_selected_store_id()
        if current_id is not None:
            current_idx = self.get_choice_idx_by_id(current_id)
        stores = self.window.core.assistants.store.get_all()
        for id in list(stores.keys()):
            if self.window.core.assistants.store.is_hidden(id):
                continue
            if stores[id].name is None or stores[id].name == "":
                items[id] = id
            else:
                items[id] = stores[id].name
        self.window.controller.config.update_combo(self.id, "vector_store", items)
        if current_id is not None:
            current_idx = self.get_choice_idx_by_id(current_id)
        option = copy.deepcopy(self.options["vector_store"])
        option["idx"] = current_idx
        self.window.controller.config.apply_value(
            parent_id=self.id,
            key="vector_store",
            option=option,
            value="",
        )

    def get_selected_store_id(self) -> str or None:
        """
        Return current selected vector store ID

        :return: vector store ID or None
        """
        idx = self.window.controller.config.get_value(
            parent_id=self.id,
            key='vector_store',
            option=self.options['vector_store'],
            idx=True,  # return idx, not the text value
        )  # empty or not
        if idx > 0:
            return self.window.ui.config[self.id]['vector_store'].combo.itemData(idx)
        return None

    def get_choice_idx_by_id(self, store_id) -> int:
        """
        Return combo choice index by vector store ID

        :param store_id: store ID
        :return: combo idx
        """
        stores = self.window.core.assistants.store.get_all()
        i = 1
        for id in list(stores.keys()):
            if self.window.core.assistants.store.is_hidden(id):
                continue  # ignore empty names
            if id == store_id:
                return i
            i += 1
        return 0  # none

    def edit(self, idx: int = None):
        """
        Open assistant editor

        :param idx: assistant index (row index)
        """
        id = None
        if idx is not None:
            id = self.window.core.assistants.get_by_idx(idx)

        self.init(id)
        self.window.ui.dialogs.open_editor('editor.assistants', idx, width=900)

    def close(self):
        """Close assistant editor"""
        self.window.ui.dialogs.close('editor.assistants')

    def init(self, id: str = None):
        """
        Initialize assistant editor

        :param id: assistant ID (in API)
        """
        assistant = self.window.core.assistants.create()
        assistant.model = "gpt-4-1106-preview"  # default model

        # if editing existing assistant
        if id is not None and id != "":
            if self.window.core.assistants.has(id):
                assistant = self.window.core.assistants.get_by_id(id)
        else:
            # defaults
            assistant.instructions = 'You are a helpful assistant.'
            assistant.tools['code_interpreter'] = True
            assistant.tools['file_search'] = True

        self.update_store_list()

        self.current = assistant

        if assistant.name is None:
            assistant.name = ""
        if assistant.description is None:
            assistant.description = ""
        if assistant.instructions is None:
            assistant.instructions = ""
        if assistant.model is None:
            assistant.model = ""

        options = {}
        data_dict = assistant.to_dict()
        for key in self.options:
            options[key] = copy.deepcopy(self.options[key])
            options[key]['value'] = data_dict[key]
            if options[key]['value'] is None:
                options[key]['value'] = ""

            # if vector store, set by idx, not by value
            if key == "vector_store":
                idx = self.get_choice_idx_by_id(data_dict[key])
                options[key]['idx'] = idx  # set by idx

        self.window.controller.config.load_options(self.id, options)  # set combo by idx

        # restore functions
        if assistant.has_functions():
            functions = assistant.get_functions()
            values = []
            for function in functions:
                values.append(
                    {
                        "name": function['name'],
                        "params": function['params'],
                        "desc": function['desc'],
                    }
                )
            self.window.ui.config[self.id]['tool.function'].items = values
            self.window.ui.config[self.id]['tool.function'].model.updateData(values)
        else:
            self.window.ui.config[self.id]['tool.function'].items = []
            self.window.ui.config[self.id]['tool.function'].model.updateData([])

        # set focus to name field
        self.window.ui.config[self.id]['name'].setFocus()

    def import_functions(self, force: bool = False):
        """
        Import functions from plugins

        :param force: force import
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='assistant.functions.import',
                id='',
                msg=trans('confirm.assistant.functions.import'),
            )
            return
        func_plugin = self.window.core.command.as_native_functions(True)
        values = self.window.ui.config[self.id]['tool.function'].items

        # import to editor
        for func in func_plugin:
            if func['name'] in [f['name'] for f in values]:
                # replace if exists
                for i in range(len(values)):
                    if values[i]['name'] == func['name']:
                        values[i] = {
                            "name": func['name'],
                            "params": func['params'],
                            "desc": func['desc'],
                        }
            else:
                # add new
                values.append(
                    {
                        "name": func['name'],
                        "params": func['params'],
                        "desc": func['desc'],
                    }
                )
        self.window.ui.config[self.id]['tool.function'].items = values
        self.window.ui.config[self.id]['tool.function'].model.updateData(values)

    def clear_functions(self, force: bool = False):
        """
        Clear functions list

        :param force: force clear
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='assistant.functions.clear',
                id='',
                msg=trans('confirm.assistant.functions.clear'),
            )
            return
        values = []
        self.window.ui.config[self.id]['tool.function'].items = values
        self.window.ui.config[self.id]['tool.function'].model.updateData(values)

    def save(self):
        """Save assistant"""
        created = False

        # get data from fields
        id = self.window.controller.config.get_value(
            parent_id=self.id, 
            key='id', 
            option=self.options['id'],
        )  # empty or not
        name = self.window.controller.config.get_value(
            parent_id=self.id, 
            key='name', 
            option=self.options['name'],
        )
        model = self.window.controller.config.get_value(
            parent_id=self.id, 
            key='model', 
            option=self.options['model'],
        )

        # check name
        if name is None or name == "" or model is None or model == "":
            self.window.ui.dialogs.alert(
                trans('assistant.form.empty.fields')
            )
            return

        if id is None or id == "" or not self.window.core.assistants.has(id):
            self.window.ui.status(trans('status.sending'))
            QApplication.processEvents()
            assistant = self.window.controller.assistant.create()  # id is created in API here
            if assistant is None:
                self.window.ui.status("status.error")
                print("ERROR: Assistant not created!")
                return
            id = assistant.id  # set to ID created in API
            self.window.core.assistants.add(assistant)
            self.window.controller.config.apply_value(
                parent_id=self.id,
                key="id",
                option=self.options["id"],
                value=id,
            )
            created = True
        else:
            assistant = self.window.core.assistants.get_by_id(id)

        # assign data from fields to assistant object
        self.assign_data(assistant)

        # update data in API if only updating data here (not creating)
        if not created:
            self.window.ui.status(trans('status.sending'))
            QApplication.processEvents()
            self.window.controller.assistant.update_data(assistant)

        # save
        self.window.core.assistants.save()
        self.window.controller.assistant.refresh()
        self.window.controller.assistant.update()

        self.window.ui.dialogs.close('editor.assistants')
        self.window.ui.status(trans('status.assistant.saved'))

        # switch to edited assistant
        self.window.controller.assistant.select_by_id(id)

    def assign_data(self, assistant: AssistantItem):
        """
        Assign data from fields to assistant

        :param assistant: assistant
        """
        model = self.window.controller.config.get_value(
            parent_id=self.id,
            key='model',
            option=self.options['model'],
        )
        if model == '_':
            model = None

        assistant.name = self.window.controller.config.get_value(
            parent_id=self.id,
            key='name',
            option=self.options['name'],
        )
        assistant.model = model
        assistant.description = self.window.controller.config.get_value(
            parent_id=self.id,
            key='description',
            option=self.options['description'],
        )
        assistant.instructions = self.window.controller.config.get_value(
            parent_id=self.id,
            key='instructions',
            option=self.options['instructions'],
        )
        assistant.tools = {
            'code_interpreter': self.window.controller.config.get_value(
                parent_id=self.id,
                key='tool.code_interpreter',
                option=self.options['tool.code_interpreter'],
            ),
            'file_search': self.window.controller.config.get_value(
                parent_id=self.id,
                key='tool.file_search',
                option=self.options['tool.file_search'],
            ),
            'function': [],  # functions are assigned separately (below)
        }

        # assign assistant's functions tool
        values = self.window.controller.config.get_value(
                parent_id=self.id,
                key='tool.function',
                option=self.options['tool.function'],
        )
        functions = []
        for function in values:
            name = function['name']
            params = function['params']
            desc = function['desc']
            if name is None or name == "":
                continue
            if params is None or params == "":
                params = '{"type": "object", "properties": {}}'  # default empty JSON params
            if desc is None:
                desc = ""
            functions.append(
                {
                    "name": name,
                    "params": params,
                    "desc": desc,
                }
            )

        if len(functions) > 0:
            assistant.tools['function'] = functions
        else:
            assistant.tools['function'] = []

        # vector store
        store_id = self.get_selected_store_id()
        assistant.vector_store = store_id
