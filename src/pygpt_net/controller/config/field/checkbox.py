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

from typing import Any, Dict


class Checkbox:
    def __init__(self, window=None):
        """
        Checkbox field handler

        :param window: Window instance
        """
        self.window = window

    def apply(
            self,
            parent_id: str,
            key: str,
            option: Dict[str, Any]
    ) -> None:
        """
        Apply value to checkbox

        :param parent_id: Options parent ID
        :param key: Option key
        :param option: Option data
        """
        if "value" not in option:
            return
        value = option["value"]
        if value is None:
            value = False
        cfg_parent = self.window.ui.config[parent_id]
        row = cfg_parent.get(key)
        if row is not None:
            row.box.setChecked(bool(value))

    def on_update(
            self,
            parent_id: str,
            key: str,
            option: Dict[str, Any],
            value: Any,
            hooks: bool = True
    ) -> None:
        """
        Event: on update checkbox value

        :param parent_id: Options parent ID
        :param key: Option key
        :param option: Option data
        :param value: Option value
        :param hooks: Run hooks
        """
        if hooks:
            ui = self.window.ui
            hook_name = f"update.{parent_id}.{key}"
            if ui.has_hook(hook_name):
                hook = ui.get_hook(hook_name)
                try:
                    hook(key, value, 'checkbox')
                except Exception as e:
                    self.window.core.debug.log(e)

    def get_value(
            self,
            parent_id: str,
            key: str,
            option: Dict[str, Any]
    ) -> bool:
        """
        Get checkbox value

        :param parent_id: Parent ID
        :param key: Option key
        :param option: Option data dict
        :return: Option value
        """
        cfg_parent = self.window.ui.config[parent_id]
        row = cfg_parent.get(key)
        if row is None:
            return False
        return row.box.isChecked()