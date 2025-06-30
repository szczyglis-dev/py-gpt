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


class CheckboxList:
    def __init__(self, window=None):
        """
        CheckboxList field handler

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
        Apply values to checkboxes

        :param parent_id: Options parent ID
        :param key: Option key
        :param option: Option data
        """
        if "value" not in option:
            return
        value = option["value"]
        exploded_list = value.split(",") if isinstance(value, str) else []
        if key not in self.window.ui.config[parent_id]:
            self.window.ui.config[parent_id][key] = {}
        for item in self.window.ui.config[parent_id][key].boxes:
            if self.window.ui.config[parent_id][key].boxes[item] is not None:
                self.window.ui.config[parent_id][key].boxes[item].setChecked(False)
        for item in exploded_list:
            item = item.strip()
            if item not in self.window.ui.config[parent_id][key].boxes:
                continue
            if self.window.ui.config[parent_id][key].boxes[item] is None:
                continue
            self.window.ui.config[parent_id][key].boxes[item].setChecked(True)

    def on_update(
            self,
            parent_id: str,
            key: str,
            option: dict,
            value: Any,
            subkey: str = None,
            hooks: bool = True
    ):
        """
        Event: on update checkbox value

        :param parent_id: Options parent ID
        :param key: Option key
        :param option: Option data
        :param value: Option value
        :param subkey: Subkey for specific checkbox
        :param hooks: Run hooks
        """
        # on update hooks
        if hooks:
            hook_name = "update.{}.{}".format(parent_id, key)
            if self.window.ui.has_hook(hook_name):
                hook = self.window.ui.get_hook(hook_name)
                try:
                    hook(key, value, 'bool_list')
                except Exception as e:
                    self.window.core.debug.log(e)

    def get_value(
            self,
            parent_id: str,
            key: str,
            option: Dict[str, Any]
    ) -> str:
        """
        Get checkbox values as comma-separated string

        :param parent_id: Parent ID
        :param key: Option key
        :param option: Option data dict
        :return: Option value
        """
        if key not in self.window.ui.config[parent_id]:
            return ""
        imploded_list = []
        for item in self.window.ui.config[parent_id][key].boxes:
            if self.window.ui.config[parent_id][key].boxes[item] is None:
                continue
            if self.window.ui.config[parent_id][key].boxes[item].isChecked():
                imploded_list.append(item)
        return ",".join(imploded_list)


    def update_list(
            self,
            parent_id: str,
            key: str,
            items: List[Dict]
    ):
        """
        Update combobox items

        :param parent_id: Options parent ID
        :param key: Option key
        :param items: Items dict
        """
        self.window.ui.config[parent_id][key].update_boxes_list(items)
