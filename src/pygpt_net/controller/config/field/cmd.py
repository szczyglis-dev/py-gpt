#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.12 06:00:00                  #
# ================================================== #

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
            option: dict
    ):
        """
        Apply values to command fields

        :param parent_id: Options parent ID
        :param key: Option key
        :param option: Option data
        """
        if option["value"] is None:
            option["value"] = {
                "enabled": False,
                "instruction": "",
                "params": [],
            }
        if "params" not in option["value"]:
            option["value"]["params"] = []
        if "enabled" not in option["value"]:
            option["value"]["enabled"] = False
        if "instruction" not in option["value"]:
            option["value"]["instruction"] = ""

        params = list(option["value"]["params"])
        self.window.ui.config[parent_id][key].params.items = params  # replace model data list
        self.window.ui.config[parent_id][key].params.model.updateData(params)  # update model data
        self.window.ui.config[parent_id][key].enabled.box.setChecked(option["value"]["enabled"])
        self.window.ui.config[parent_id][key].instruction.setText(str(option["value"]["instruction"]))

    def apply_row(
            self,
            parent_id: str,
            key: str,
            values: dict,
            idx: int
    ):
        """
        Apply data values to command fields

        :param parent_id: Options parent ID
        :param key: Option key
        :param values: dictionary data values
        :param idx: row index
        """
        # remove .params suffix
        if key.endswith(".params"):
            key = key.replace(".params", "")
        self.window.ui.config[parent_id][key].params.update_item(idx, values["params"])

    def get_value(
            self,
            parent_id: str,
            key: str,
            option: dict
    ) -> dict:
        """
        Get command values

        :param parent_id: Options parent ID
        :param key: Option key
        :param option: Option data
        :return: list with dictionary values
        """
        data = {
            "enabled": self.window.ui.config[parent_id][key].enabled.box.isChecked(),
            "instruction": self.window.ui.config[parent_id][key].instruction.toPlainText(),
            "params": self.window.ui.config[parent_id][key].params.model.items,
        }
        return data

    def to_options(
            self,
            parent_id: str,
            option: dict
    ) -> dict:
        """
        Convert dictionary items option to options

        :param parent_id: Parent ID
        :param option: dictionary items option
        :return: options dict
        """
        # option type: dict
        if option["type"] == "dict":
            if "keys" not in option:
                return {}
            options = {}
            for key in option["keys"]:
                item = option["keys"][key]
                if isinstance(item, str):
                    item = {
                        "label": parent_id + '.' + key,
                        "type": item,  # field type is provided as value in this case
                    }
                options[key] = item
                if "label" not in options[key]:
                    options[key]["label"] = key
                    options[key]["label"] = parent_id + "." + options[key]["label"]
            return options

        # option type: cmd
        elif option["type"] == "cmd":
            if "params_keys" not in option:  # keys are stored in "params_keys" in cmd type
                return {}
            options = {}
            for key in option["params_keys"]:
                item = option["params_keys"][key]
                if isinstance(item, str):
                    item = {
                        "label": 'dictionary.cmd.param.' + key,
                        "type": item,  # field type is provided as value in this case
                    }
                options[key] = item
                if "label" not in options[key]:
                    options[key]["label"] = 'dictionary.cmd.param.' + key
            return options
