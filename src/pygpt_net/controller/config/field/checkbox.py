#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.08 17:00:00                  #
# ================================================== #

class Checkbox:
    def __init__(self, window=None):
        """
        Checkbox field handler

        :param window: Window instance
        """
        self.window = window

    def apply(self, parent_id: str, key: str, option: dict):
        """
        Apply value to checkbox

        :param parent_id: Options parent ID
        :param key: Option key
        :param option: Option data
        """
        value = option["value"]
        self.window.config_bag.items[parent_id][key].box.setChecked(value)

    def on_update(self, parent_id: str, key: str, option: dict, value: any, hooks: bool = True):
        """
        Update value of checkbox

        :param parent_id: Options parent ID
        :param key: Option key
        :param option: Option data
        :param value: Option value
        :param hooks: Run hooks
        """
        # on update hooks
        if hooks:
            hook_name = "update.{}.{}".format(parent_id, key)
            if hook_name in self.window.config_bag.hooks:
                self.window.config_bag.hooks[hook_name](key, value, 'checkbox')

    def get_value(self, parent_id: str, key: str, option: dict):
        return self.window.config_bag.items[parent_id][key].box.isChecked()
