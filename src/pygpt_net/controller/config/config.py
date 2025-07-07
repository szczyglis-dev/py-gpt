#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.06.30 02:00:00                  #
# ================================================== #

from typing import Any, Dict, List

from .field.checkbox import Checkbox
from .field.checkbox_list import CheckboxList
from .field.combo import Combo
from .field.cmd import Cmd
from .field.dictionary import Dictionary
from .field.input import Input
from .field.slider import Slider
from .field.textarea import Textarea
from .placeholder import Placeholder


class Config:
    def __init__(self, window=None):
        """
        Configuration controller

        :param window: Window instance
        """
        self.window = window
        self.checkbox = Checkbox(window)
        self.checkbox_list = CheckboxList(window)
        self.combo = Combo(window)
        self.cmd = Cmd(window)
        self.dictionary = Dictionary(window)
        self.input = Input(window)
        self.placeholder = Placeholder(window)
        self.slider = Slider(window)
        self.textarea = Textarea(window)

    def load_options(
            self,
            parent_id: str,
            options: Dict[str, Dict[str, Any]]
    ):
        """
        Load options

        :param parent_id: Parent ID
        :param options: Options dict
        """
        for key in options:
            option = options[key]
            self.apply(parent_id, key, option)

    def apply(
            self,
            parent_id: str,
            key: str,
            option: Dict[str, Any]
    ):
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
        elif option['type'] == 'bool_list':
            self.checkbox_list.apply(parent_id, key, option)
        elif option['type'] == 'dict':
            self.dictionary.apply(parent_id, key, option)
        elif option['type'] == 'combo':
            self.combo.apply(parent_id, key, option)
        elif option['type'] == 'cmd':
            self.cmd.apply(parent_id, key, option)

    def apply_value(
            self,
            parent_id: str,
            key: str,
            option: Dict[str, Any],
            value: Any
    ):
        """
        Apply value to option

        :param parent_id: Parent ID
        :param key: Option key
        :param option: Option dict
        :param value: Option value
        """
        option['value'] = value
        self.apply(parent_id, key, option)

    def get_value(
            self,
            parent_id: str,
            key: str,
            option: Dict[str, Any],
            idx: bool = False
    ) -> Any:
        """
        Get value from field handler based on type

        :param parent_id: Parent ID
        :param key: Option key
        :param option: Option dict
        :param idx: return selected idx, not the value
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
        elif option['type'] == 'bool_list':
            return self.checkbox_list.get_value(parent_id, key, option)
        elif option['type'] == 'dict':
            return self.dictionary.get_value(parent_id, key, option)
        elif option['type'] == 'combo':
            return self.combo.get_value(parent_id, key, option, idx)
        elif option['type'] == 'cmd':
            return self.cmd.get_value(parent_id, key, option)

    def update_list(
            self,
            option: Dict[str, Any],
            parent_id: str,
            key: str,
            items: List[Dict]
    ):
        """
        Update list items

        :param option: Option dict
        :param parent_id: Parent ID
        :param key: Option key
        :param items: Items dict
        """
        if "type" not in option:
            return
        if option['type'] == 'combo':
            as_dict = {}
            for item in items:
                for k, v in item.items():
                    as_dict[k] = v
            self.update_combo(parent_id, key, as_dict)
        elif option['type'] == 'bool_list':
            self.update_bool_list(parent_id, key, items)

    def update_combo(
            self,
            parent_id: str,
            key: str,
            items: Dict[str, str]
    ):
        """
        Update combo items

        :param parent_id: Parent ID
        :param key: Option key
        :param items: Items dict
        """
        self.combo.update_list(parent_id, key, items)

    def update_bool_list(
            self,
            parent_id: str,
            key: str,
            items: List[Dict]
    ):
        """
        Update combo items

        :param parent_id: Parent ID
        :param key: Option key
        :param items: Items dict
        """
        self.checkbox_list.update_list(parent_id, key, items)
