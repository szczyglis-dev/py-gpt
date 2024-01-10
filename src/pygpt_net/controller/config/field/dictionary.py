#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.10 17:00:00                  #
# ================================================== #

from pygpt_net.utils import trans


class Dictionary:
    def __init__(self, window=None):
        """
        Dictionary field handler

        :param window: Window instance
        """
        self.window = window

    def apply(self, parent_id: str, key: str, option: dict):
        """
        Apply values to dictionary

        :param parent_id: Options parent ID
        :param key: Option key
        :param option: Option data
        """
        values = list(option["value"])
        self.window.ui.config[parent_id][key].items = values  # replace model data list
        self.window.ui.config[parent_id][key].model.updateData(values)  # update model data

    def apply_row(self, parent_id: str, key: str, values: dict, idx: int):
        """
        Apply data values to dictionary

        :param parent_id: Options parent ID
        :param key: Option key
        :param values: dictionary data values
        :param idx: row index
        """
        self.window.ui.config[parent_id][key].update_item(idx, values)

    def get_value(self, parent_id: str, key: str, option: dict) -> list:
        """
        Get dictionary values

        :param parent_id: Options parent ID
        :param key: Option key
        :param option: Option data
        :return: list with dictionary values
        """
        return self.window.ui.config[parent_id][key].model.items

    def delete_item(self, parent_object, id: str, force: bool = False):
        """
        Show delete item (from dict list) confirmation dialog or executes delete

        :param parent_object: parent object
        :param id: item id
        :param force: force delete
        """
        if not force:
            self.window.ui.dialogs.confirm('settings.dict.delete', id, trans('settings.dict.delete.confirm'),
                                           parent_object)
            return

        # delete item
        if parent_object is not None:
            parent_object.delete_item_execute(id)
