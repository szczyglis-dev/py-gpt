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

from typing import Any, Dict, Optional, Union


class Input:
    def __init__(self, window=None):
        """
        Text input field handler

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
        Apply value to input

        :param parent_id: Options parent ID
        :param key: Option key
        :param option: Option data
        """
        if "value" not in option:
            return
        value = option["value"]

        # type
        if "type" in option and option["type"] == "int":
            try:
                value = round(int(value), 0)
            except Exception:
                value = 0
        elif "type" in option and option["type"] == "float":
            try:
                value = float(value)
            except Exception:
                value = 0.0

        # min/max
        if "type" in option and (option["type"] == "int" or option["type"] == "float"):
            if value is not None:
                if "min" in option and (option["min"] is not None and value < option["min"]):
                    value = option["min"]
                elif "max" in option and (option["max"] is not None and value > option["max"]):
                    value = option["max"]

        if parent_id in self.window.ui.config and key in self.window.ui.config[parent_id]:
            self.window.ui.config[parent_id][key].setText("{}".format(value))

    def on_update(
            self,
            parent_id: str,
            key: str,
            option: Dict[str, Any],
            value: Any,
            hooks: bool = True,
            only_hook = False,
    ):
        """
        On update event handler

        :param parent_id: Parent ID
        :param key: Option key
        :param option: Option data
        :param value: Option value
        :param hooks: Run hooks
        :param only_hook: Only run hook, do not apply value
        """
        option['value'] = value
        if not only_hook:
            self.apply(parent_id, key, option)

        # on update hooks
        if hooks:
            hook_name = "update.{}.{}".format(parent_id, key)
            if self.window.ui.has_hook(hook_name):
                hook = self.window.ui.get_hook(hook_name)
                try:
                    hook(key, value, "input")
                except Exception as e:
                    self.window.core.debug.log(e)

    def get_value(
            self,
            parent_id: str,
            key: str,
            option: Dict[str, Any]
    ) -> Optional[Union[int, float, str]]:
        """
        Get value from input

        :param parent_id: Parent ID
        :param key: Option key
        :param option: Option data
        :return: Value
        """
        value = None
        if option["type"] == "int":
            try:
                value = int(self.window.ui.config[parent_id][key].text())
            except Exception:
                value = 0
        elif option["type"] == "float":
            try:
                value = float(self.window.ui.config[parent_id][key].text())
            except Exception:
                value = 0.0
        elif option["type"] == "text":
            value = self.window.ui.config[parent_id][key].text()
        return value
