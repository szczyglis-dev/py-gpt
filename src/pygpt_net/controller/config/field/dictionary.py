#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.12.27 21:00:00                  #
# ================================================== #

from typing import Dict, Any, List, Union

from pygpt_net.ui.widget.option.dictionary import OptionDict
from pygpt_net.utils import trans


class Dictionary:
    def __init__(self, window=None):
        """
        Dictionary field handler

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
        Apply values to dictionary

        :param parent_id: Options parent ID
        :param key: Option key
        :param option: Option data
        """
        if option.get("value") is None:
            option["value"] = []
            values = []
        else:
            v = option["value"]
            values = v.copy() if isinstance(v, list) else list(v)
        cfg_item = self.window.ui.config[parent_id][key]
        cfg_item.items = values
        cfg_item.model.updateData(values)

    def apply_row(
            self,
            parent_id: str,
            key: str,
            values: Dict[str, Any],
            idx: int
    ):
        """
        Apply data values to dictionary

        :param parent_id: Options parent ID
        :param key: Option key
        :param values: dictionary data values
        :param idx: row index
        """
        if key.endswith(".params"):
            key = key[:-7]
        self.window.ui.config[parent_id][key].update_item(idx, values)

    def get_value(
            self,
            parent_id: str,
            key: str,
            option: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Get dictionary values

        :param parent_id: Options parent ID
        :param key: Option key
        :param option: Option data
        :return: list with dictionary values
        """
        return self.window.ui.config[parent_id][key].model.items

    def delete_item(
            self,
            parent_object: OptionDict,
            id,  # Union[int, list[int]]
            force: bool = False,
            hooks: bool = True
    ):
        """
        Show delete item (from dict list) confirmation dialog or executes delete

        :param parent_object: parent object
        :param id: item id or list of ids (row indexes)
        :param force: force delete
        :param hooks: run hooks
        """
        if not force:
            # Pass list as-is for batch confirmation
            self.window.ui.dialogs.confirm(
                type="settings.dict.delete",
                id=id,
                msg=trans("settings.dict.delete.confirm"),
                parent_object=parent_object,
            )
            return

        if parent_object is not None:
            # Normalize to unique integer indexes and sort descending to avoid index shift on delete
            ids = id if isinstance(id, list) else [id]
            normalized = []
            for v in ids:
                try:
                    normalized.append(int(v))
                except Exception:
                    continue
            normalized = sorted(set(normalized), reverse=True)

            ui = self.window.ui
            for idx in normalized:
                parent_object.delete_item_execute(idx)
                if hooks:
                    hook_name = f"update.{parent_object}.{idx}"
                    if ui.has_hook(hook_name):
                        hook = ui.get_hook(hook_name)
                        try:
                            hook(idx, {}, "dictionary")
                        except Exception as e:
                            self.window.core.debug.log(e)

    def to_options(
            self,
            parent_id: str,
            option: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Convert dictionary items option to options

        :param parent_id: Parent ID
        :param option: dictionary items option
        :return: options dict
        """
        keys = option.get("keys")
        if not keys:
            return {}
        options: Dict[str, Any] = {}
        prefix = f"{parent_id}."
        for key, item in keys.items():
            if isinstance(item, str):
                item = {
                    "label": f"{prefix}{key}",
                    "type": item,
                }
            else:
                if "label" not in item:
                    item["label"] = f"{prefix}{key}"
            options[key] = item
        return options

    def append_editor(
            self,
            id: str,
            option: Dict[str, Any],
            data: Dict[str, Any]
    ):
        """
        Apply dict item option sub-values to dict editor

        :param id: Owner object ID
        :param option: Option dict
        :param data: Option data
        """
        parent_id = f"dictionary.{id}"
        sub_options = self.to_options(id, option)
        apply_fn = self.window.controller.config.apply
        for key, sub_option in sub_options.items():
            sub_option["value"] = data.get(key, "")
            apply_fn(
                parent_id=parent_id,
                key=key,
                option=sub_option,
            )

    def save_editor(
            self,
            option_key: str,
            parent: str,
            fields: Dict[str, Dict[str, Any]],
            hooks: bool = True
    ):
        """
        Save dict editor (called from dict editor dialog save button)

        :param option_key: Option key
        :param parent: Parent ID
        :param fields: Fields dict
        :param hooks: run hooks
        """
        values: Dict[str, Any] = {}
        dict_id = f"{parent}.{option_key}"
        dialog_id = f"dictionary.{dict_id}"
        dialog_key = f"editor.{dialog_id}"
        ui = self.window.ui
        idx = ui.dialog[dialog_key].idx
        get_value_fn = self.window.controller.config.get_value
        fields_parent_id = f"dictionary.{dict_id}"
        for key, field in fields.items():
            values[key] = get_value_fn(
                parent_id=fields_parent_id,
                key=key,
                option=field,
            )

        self.apply_row(parent, option_key, values, idx)
        ui.dialog[dialog_key].close()

        if hooks:
            hook_name = f"update.{parent}.{option_key}"
            if ui.has_hook(hook_name):
                hook = ui.get_hook(hook_name)
                try:
                    hook(option_key, [values], "dictionary")
                except Exception as e:
                    self.window.core.debug.log(e)