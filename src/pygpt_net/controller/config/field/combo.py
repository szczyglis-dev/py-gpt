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
        combo = self.window.ui.config[parent_id][key].combo
        if "idx" in option:
            combo.setCurrentIndex(option["idx"])
        else:
            index = combo.findData(value)
            if index != -1:
                combo.setCurrentIndex(index)

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
        if hooks:
            ui = self.window.ui
            hook_name = f"update.{parent_id}.{key}"
            if ui.has_hook(hook_name):
                hook = ui.get_hook(hook_name)
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
        combo = self.window.ui.config[parent_id][key].combo
        if idx:
            return combo.currentIndex()
        else:
            return combo.currentData()

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
        combo = self.window.ui.config[parent_id][key].combo
        combo.setUpdatesEnabled(False)
        try:
            need_rebuild = True
            if combo.count() == len(items):
                i = 0
                need_rebuild = False
                for k, v in items.items():
                    if combo.itemData(i) != k or combo.itemText(i) != v:
                        need_rebuild = True
                        break
                    i += 1
            if need_rebuild:
                combo.clear()
                for k, v in items.items():
                    combo.addItem(v, k)
            combo.setCurrentIndex(-1)
        finally:
            combo.setUpdatesEnabled(True)