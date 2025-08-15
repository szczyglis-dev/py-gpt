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
        selection = {s.strip() for s in value.split(",")} if isinstance(value, str) else set()
        selection.discard("")

        ui = self.window.ui
        cfg_parent = ui.config.get(parent_id)
        if not cfg_parent:
            return
        entry = cfg_parent.get(key)
        if entry is None or not hasattr(entry, "boxes"):
            return
        boxes = entry.boxes

        for name, cb in boxes.items():
            if cb is None:
                continue
            desired = name in selection
            if cb.isChecked() != desired:
                cb.setChecked(desired)

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
        if hooks:
            ui = self.window.ui
            hook_name = f"update.{parent_id}.{key}"
            if ui.has_hook(hook_name):
                hook = ui.get_hook(hook_name)
                if hook:
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
        ui = self.window.ui
        cfg_parent = ui.config.get(parent_id)
        if not cfg_parent:
            return ""
        entry = cfg_parent.get(key)
        if entry is None or not hasattr(entry, "boxes"):
            return ""
        boxes = entry.boxes
        return ",".join(name for name, cb in boxes.items() if cb is not None and cb.isChecked())

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