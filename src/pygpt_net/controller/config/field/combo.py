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

class Combo:
    def __init__(self, window=None):
        """
        Combobox field handler

        :param window: Window instance
        """
        self.window = window

    def apply(self, parent_id: str, key: str, option: dict):
        """
        Apply value to combobox

        :param parent_id: Options parent ID
        :param key: Option key
        :param option: Option data
        """
        value = option["value"]
        index = self.window.ui.config[parent_id][key].combo.findData(value)
        if index != -1:
            self.window.ui.config[parent_id][key].combo.setCurrentIndex(index)

    def on_update(self, parent_id: str, key: str, option: dict, value: any, hooks: bool = True):
        """
        Event: on change combobox value

        :param parent_id: Options parent ID
        :param key: Option key
        :param option: Option data
        :param value: Option value
        :param hooks: Run hooks
        """
        # on update hooks
        if hooks:
            hook_name = "update.{}.{}".format(parent_id, key)
            if self.window.ui.has_hook(hook_name):
                hook = self.window.ui.get_hook(hook_name)
                try:
                    hook(key, value, 'combo')
                except Exception as e:
                    self.window.core.debug.log(e)

    def get_value(self, parent_id: str, key: str, option: dict) -> str:
        """
        Get checkbox value

        :param parent_id: Parent ID
        :param key: Option key
        :param option: Option data dict
        :return: Option value
        """
        return self.window.ui.config[parent_id][key].combo.currentData()
