#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.06.29 18:00:00                  #
# ================================================== #

from typing import Any, Dict


class Combo:
    def __init__(self, window=None):
        """
        Combobox field handler

        :param window: Window instance
        """
        self.window = window

    def apply(
            self,
            parent_id: str,
            key: str,
            option: Dict[str, Any]
    ):
        """
        Apply value to combobox

        :param parent_id: Options parent ID
        :param key: Option key
        :param option: Option data
        :param idx: by idx, not the value
        """
        if "value" not in option:
            return
        value = option["value"]
        if "idx" in option:  # by idx
            self.window.ui.config[parent_id][key].combo.setCurrentIndex(option["idx"])
        else: # by value
            index = self.window.ui.config[parent_id][key].combo.findData(value)
            if index != -1:
                self.window.ui.config[parent_id][key].combo.setCurrentIndex(index)

    def on_update(
            self,
            parent_id: str,
            key: str,
            option: Dict[str, Any],
            value: Any,
            hooks: bool = True
    ):
        """
        Event: on change combobox value

        :param parent_id: Options parent ID
        :param key: Option key
        :param option: Option data
        :param value: Option value
        :param hooks: Run hooks
        """
        # on update hooks
        if hooks:
            hook_name = "update.{}.{}".format(parent_id, key)
            if self.window.ui.has_hook(hook_name):
                hook = self.window.ui.get_hook(hook_name)
                try:
                    hook(key, value, "combo")
                except Exception as e:
                    self.window.core.debug.log(e)

    def get_value(
            self,
            parent_id: str,
            key: str,
            option: Dict[str, Any],
            idx: bool = False
    ) -> str or int:
        """
        Get checkbox value

        :param parent_id: Parent ID
        :param key: Option key
        :param option: Option data dict
        :param idx: return selected idx, not the value
        :return: Option text value or selected idx
        """
        if idx:
            return self.window.ui.config[parent_id][key].combo.currentIndex()
        else:
            return self.window.ui.config[parent_id][key].combo.currentData()

    def update_list(
            self,
            parent_id: str,
            key: str,
            items: Dict[str, str]
    ):
        """
        Update combobox items

        :param parent_id: Options parent ID
        :param key: Option key
        :param items: Items dict
        """
        self.window.ui.config[parent_id][key].combo.clear()
        for item in items:
            self.window.ui.config[parent_id][key].combo.addItem(items[item], item)
        self.window.ui.config[parent_id][key].combo.setCurrentIndex(-1)
