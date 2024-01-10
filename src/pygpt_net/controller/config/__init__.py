#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.10 17:00:00                  #
# ================================================== #

from .field.checkbox import Checkbox
from .field.combo import Combo
from .field.dictionary import Dictionary
from .field.input import Input
from .field.slider import Slider
from .field.textarea import Textarea


class Config:
    def __init__(self, window=None):
        """
        Configuration options controller

        :param window: Window instance
        """
        self.window = window
        self.checkbox = Checkbox(window)
        self.combo = Combo(window)
        self.dictionary = Dictionary(window)
        self.input = Input(window)
        self.slider = Slider(window)
        self.textarea = Textarea(window)

    def load_options(self, parent_id: str, options: dict):
        """
        Load options

        :param parent_id: Parent ID
        :param options: Options dict
        """
        for key in options:
            option = options[key]
            self.apply(parent_id, key, option)

    def apply(self, parent_id: str, key: str, option: dict):
        """
        Apply option to field handler based on type

        :param parent_id: Parent ID
        :param key: Option key
        :param option: Option dict
        """
        if option['type'] == 'int' or option['type'] == 'float':
            if 'slider' in option and option['slider']:
                self.slider.apply(parent_id, key, option)
            else:
                self.input.apply(parent_id, key, option)
        elif option['type'] == 'text':
            self.input.apply(parent_id, key, option)
        elif option['type'] == 'textarea':
            self.textarea.apply(parent_id, key, option)
        elif option['type'] == 'bool':
            self.checkbox.apply(parent_id, key, option)
        elif option['type'] == 'dict':
            self.dictionary.apply(parent_id, key, option)
        elif option['type'] == 'combo':
            self.combo.apply(parent_id, key, option)

    def apply_value(self, parent_id: str, key: str, option: dict, value):
        """
        Apply value to option

        :param parent_id: Parent ID
        :param key: Option key
        :param option: Option dict
        :param value: Option value
        """
        option['value'] = value
        self.apply(parent_id, key, option)

    def apply_to_dict_editor(self, id, option, data):
        """
        Apply dict item option sub-values to dict editor

        :param id: Owner object ID
        :param option: Option dict
        :param data: Option data
        """
        parent_id = "dictionary." + id
        sub_options = self.dict_option_to_options(id, option)
        for key in sub_options:
            sub_option = sub_options[key]
            self.apply_value(parent_id, key, sub_option, data[key])

    def get_value(self, parent_id: str, key: str, option: dict) -> any:
        """
        Get value from field handler based on type

        :param parent_id: Parent ID
        :param key: Option key
        :param option: Option dict
        :return: Option value
        """
        if option['type'] == 'int' or option['type'] == 'float':
            if 'slider' in option and option['slider']:
                return self.slider.get_value(parent_id, key, option)
            else:
                return self.input.get_value(parent_id, key, option)
        elif option['type'] == 'text':
            return self.input.get_value(parent_id, key, option)
        elif option['type'] == 'textarea':
            return self.textarea.get_value(parent_id, key, option)
        elif option['type'] == 'bool':
            return self.checkbox.get_value(parent_id, key, option)
        elif option['type'] == 'dict':
            return self.dictionary.get_value(parent_id, key, option)
        elif option['type'] == 'combo':
            return self.combo.get_value(parent_id, key, option)

    def dict_option_to_options(self, parent_id: str, option: dict) -> dict:
        """
        Convert dictionary items option to options

        :param parent_id: Parent ID
        :param option: dictionary items option
        :return: options dict
        """
        if "keys" not in option:
            return {}
        options = {}
        for key in option["keys"]:
            item = option["keys"][key]
            if isinstance(item, str):
                item = {
                    'label': parent_id + '.' + key,
                    'type': 'text',
                }
            options[key] = item
            if options[key]["type"] == "text":
                options[key]["type"] = "textarea"  # convert text fields to textarea fields
            if 'label' not in options[key]:
                options[key]['label'] = key
                options[key]['label'] = parent_id + '.' + options[key]['label']
        return options

    def save_dict_editor(self, option_key: str, parent: str, fields: dict):
        """
        Save dict editor (called from dict editor dialog save button)

        :param option_key: Option key
        :param parent: Parent ID
        :param fields: Fields dict
        """
        values = {}
        dict_id = parent + "." + option_key
        dialog_id = "dictionary." + parent + "." + option_key  # dictionary parent ID
        idx = self.window.ui.dialog['editor.' + dialog_id].idx  # editing record idx is stored in dialog idx
        for key in fields:
            value = self.get_value("dictionary." + dict_id, key, fields[key])
            values[key] = value

        # update values in dictionary item on list in parent
        self.dictionary.apply_row(parent, option_key, values, idx)

        # close dialog
        self.window.ui.dialog['editor.' + dialog_id].close()

    def apply_placeholders(self, option: dict):
        """
        Apply placeholders to option

        :param option: Option dict
        """
        if option['type'] == 'dict' and 'keys' in option:
            for key in option['keys']:
                item = option['keys'][key]
                if type(item) is dict:
                    if "type" in item:
                        if item["type"] == "combo":
                            if "use" in item:
                                if item["use"] == "presets":
                                    item["keys"] = self.get_placeholder_presets()
                                elif item["use"] == "models":
                                    item["keys"] = self.get_placeholder_models()
        elif option['type'] == 'combo':
            if "use" in option:
                if option["use"] == "presets":
                    option["keys"] = self.get_placeholder_presets()
                elif option["use"] == "models":
                    option["keys"] = self.get_placeholder_models()

    def get_placeholder_presets(self) -> list:
        """
        Get presets placeholders list

        :return: Presets placeholders list
        """
        presets = self.window.core.presets.get_all()
        data = []
        data.append({'_': '---'})
        for id in presets:
            if id.startswith("current."):
                continue
            data.append({id: id})  # TODO: name
        return data

    def get_placeholder_models(self) -> list:
        """
        Get models placeholders list

        :return: Models placeholders list
        """
        models = self.window.core.models.get_all()
        data = []
        data.append({'_': '---'})
        for id in models:
            data.append({id: id})  # TODO: name
        return data
