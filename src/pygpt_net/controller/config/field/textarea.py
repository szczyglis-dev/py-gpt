#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.12.26 13:00:00                  #
# ================================================== #

from typing import Any, Dict


class Textarea:
    def __init__(self, window=None):
        """
        Textarea field handler

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
        Apply value to textarea

        :param parent_id: Options parent ID
        :param key: Option key
        :param option: Option data
        """
        parent = self.window.ui.config[parent_id]
        field = parent.get(key)
        if field is None:
            return
        new_text = str(option["value"]) if "value" in option else ""
        if hasattr(field, "toPlainText"):
            current = field.toPlainText()
        elif hasattr(field, "text"):
            current = field.text()
        else:
            current = None
        if current == new_text:
            return
        if hasattr(field, "setText"):
            field.setText(new_text)
        elif hasattr(field, "setPlainText"):
            field.setPlainText(new_text)

    def on_update(
            self,
            parent_id: str,
            key: str,
            option: Dict[str, Any],
            value: Any,
            hooks: bool = True
    ):
        """
        Event: on update

        :param parent_id: Parent ID
        :param key: Option key
        :param option: Option data
        :param value: Option value
        :param hooks: Run hooks
        """
        option["value"] = value
        self.apply(parent_id, key, option)

        if hooks:
            hook_name = f"update.{parent_id}.{key}"
            if self.window.ui.has_hook(hook_name):
                hook = self.window.ui.get_hook(hook_name)
                try:
                    hook(key, value, "textarea")
                except Exception as e:
                    self.window.core.debug.log(e)

    def get_value(
            self,
            parent_id: str,
            key: str,
            option: Dict[str, Any]
    ) -> str:
        """
        Get value of textarea

        :param parent_id: Parent ID
        :param key: Option key
        :param option: Option data
        :return: Textarea option value (plain text)
        """
        return self.window.ui.config[parent_id][key].toPlainText()