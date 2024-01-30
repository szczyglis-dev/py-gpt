#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.30 20:00:00                  #
# ================================================== #

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
            option: dict
    ):
        """
        Apply value to checkbox

        :param parent_id: Options parent ID
        :param key: Option key
        :param option: Option data
        """
        value = option["value"]
        if value is None:
            value = False
        if key in self.window.ui.config[parent_id]:
            self.window.ui.config[parent_id][key].box.setChecked(bool(value))

    def on_update(
            self,
            parent_id: str,
            key: str,
            option: dict,
            value: any,
            hooks: bool = True
    ):
        """
        Event: on update checkbox value

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
                    hook(key, value, 'checkbox')
                except Exception as e:
                    self.window.core.debug.log(e)

    def get_value(
            self,
            parent_id: str,
            key: str,
            option: dict
    ) -> bool:
        """
        Get checkbox value

        :param parent_id: Parent ID
        :param key: Option key
        :param option: Option data dict
        :return: Option value
        """
        if key not in self.window.ui.config[parent_id]:
            return False
        return self.window.ui.config[parent_id][key].box.isChecked()
