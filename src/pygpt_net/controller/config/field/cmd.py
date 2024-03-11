#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.11 01:00:00                  #
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
        values = list(option["value"]["params"])
        self.window.ui.config[parent_id][key].params.items = values  # replace model data list
        self.window.ui.config[parent_id][key].params.model.updateData(values)  # update model data

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
            "params": self.window.ui.config[parent_id][key].params.model.items,
        }
        return data
