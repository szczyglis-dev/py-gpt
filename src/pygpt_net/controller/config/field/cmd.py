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

from typing import Dict, Any

from pygpt_net.utils import trans


class Cmd:
    def __init__(self, window=None):
        """
        Command field handler - >>> NOT IMPLEMENTED YET <<<<

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
        Apply values to command fields

        :param parent_id: Options parent ID
        :param key: Option key
        :param option: Option data
        """
        v = option.get("value")
        if not isinstance(v, dict):
            v = {"enabled": False, "instruction": "", "params": []}
            option["value"] = v
        else:
            v.setdefault("enabled", False)
            v.setdefault("instruction", "")
            v.setdefault("params", [])

        params = list(v["params"])
        cfg = self.window.ui.config[parent_id][key]
        cfg.params.items = params
        cfg.params.model.updateData(params)
        cfg.enabled.box.setChecked(v["enabled"])
        cfg.instruction.setText(str(v["instruction"]))

    def apply_row(
            self,
            parent_id: str,
            key: str,
            values: Dict[str, Any],
            idx: int
    ):
        """
        Apply data values to command fields

        :param parent_id: Options parent ID
        :param key: Option key
        :param values: dictionary data values
        :param idx: row index
        """
        if key.endswith(".params"):
            key = key[:-7]
        params_cfg = self.window.ui.config[parent_id][key].params
        params_cfg.update_item(idx, values["params"])

    def get_value(
            self,
            parent_id: str,
            key: str,
            option: Dict[str, Any]
    ) -> dict:
        """
        Get command values

        :param parent_id: Options parent ID
        :param key: Option key
        :param option: Option data
        :return: list with dictionary values
        """
        cfg = self.window.ui.config[parent_id][key]
        return {
            "enabled": cfg.enabled.box.isChecked(),
            "instruction": cfg.instruction.toPlainText(),
            "params": cfg.params.model.items,
        }

    def to_options(
            self,
            parent_id: str,
            option: Dict[str, Any]
    ) -> dict:
        """
        Convert dictionary items option to options

        :param parent_id: Parent ID
        :param option: dictionary items option
        :return: options dict
        """
        ty = option.get("type")

        if ty == "dict":
            keys_map = option.get("keys")
            if not keys_map:
                return {}
            opts = {}
            prefix = f"{parent_id}."
            for k, item in keys_map.items():
                if isinstance(item, str):
                    opts[k] = {"label": f"{prefix}{k}", "type": item}
                else:
                    opts[k] = item
                    if "label" not in item:
                        item["label"] = f"{prefix}{k}"
            return opts

        elif ty == "cmd":
            params_map = option.get("params_keys")
            if not params_map:
                return {}
            opts = {}
            prefix = "dictionary.cmd.param."
            for k, item in params_map.items():
                if isinstance(item, str):
                    opts[k] = {"label": f"{prefix}{k}", "type": item}
                else:
                    opts[k] = item
                    if "label" not in item:
                        item["label"] = f"{prefix}{k}"
            return opts