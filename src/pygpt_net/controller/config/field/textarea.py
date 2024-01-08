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

class Textarea:
    def __init__(self, window=None):
        """
        Textarea field handler

        :param window: Window instance
        """
        self.window = window

    def apply(self, parent_id: str, key: str, option: dict):
        """
        Apply value to textarea

        :param parent_id: Options parent ID
        :param key: Option key
        :param option: Option data
        """
        self.window.config_bag.items[parent_id][key].setText('{}'.format(option["value"]))

    def on_update(self, parent_id: str, key: str, option: dict, value: any, hooks: bool = True):
        """
        Event: on update

        :param parent_id: Parent ID
        :param key: Option key
        :param option: Option data
        :param value: Option value
        :param hooks: Run hooks
        """
        option['value'] = value
        self.apply(parent_id, key, option)

        # on update hooks
        hook_name = "update.{}.{}".format(parent_id, key)
        if hook_name in self.window.config_bag.hooks:
            self.window.config_bag.hooks[hook_name](key, value, 'textarea')

    def get_value(self, parent_id: str, key: str, option: dict) -> str:
        """
        Get value of textarea
        :param parent_id: Parent ID
        :param key: Option key
        :param option: Option data
        :return: Textarea option value (plain text)
        """
        return self.window.config_bag.items[parent_id][key].toPlainText()
