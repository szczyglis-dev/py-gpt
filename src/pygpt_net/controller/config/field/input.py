#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.15 23:00:00                  #
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

        ui = self.window.ui
        parent = ui.config.get(parent_id)
        if not parent:
            return
        widget = parent.get(key)
        if widget is None:
            return

        value = option["value"]
        typ = option.get("type")

        if typ == "int":
            try:
                value = round(int(value), 0)
            except (ValueError, TypeError):
                value = 0
        elif typ == "float":
            try:
                value = float(value)
            except (ValueError, TypeError):
                value = 0.0

        if typ in ("int", "float") and value is not None:
            minv = option.get("min")
            maxv = option.get("max")
            if minv is not None and value < minv:
                value = minv
            elif maxv is not None and value > maxv:
                value = maxv

        new_text = str(value)
        curr_val = None
        if hasattr(widget, 'text'):
            curr_val = widget.text()
        elif hasattr(widget, 'toPlainText'):
            curr_val = widget.toPlainText()
        if curr_val != new_text:
            widget.setText(new_text)

    def on_update(
            self,
            parent_id: str,
            key: str,
            option: Dict[str, Any],
            value: Any,
            hooks: bool = True,
            only_hook: bool = False,
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

        if hooks:
            ui = self.window.ui
            hook_name = f"update.{parent_id}.{key}"
            if ui.has_hook(hook_name):
                hook = ui.get_hook(hook_name)
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
        typ = option["type"]
        widget = self.window.ui.config[parent_id][key]
        text = widget.text()

        if typ == "int":
            try:
                return int(text)
            except (ValueError, TypeError):
                return 0
        elif typ == "float":
            try:
                return float(text)
            except (ValueError, TypeError):
                return 0.0
        elif typ == "text":
            return text
        return None