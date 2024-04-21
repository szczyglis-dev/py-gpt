#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.20 06:00:00                  #
# ================================================== #

class Slider:
    def __init__(self, window=None):
        """
        Slider field handler

        :param window: Window instance
        """
        self.window = window

    def apply(
            self,
            parent_id: str,
            key: str,
            option: dict,
            type: str = None
    ):
        """
        Apply value to slider

        :param parent_id: Options parent ID
        :param key: Option key
        :param option: Option data
        :param type: Update from type (slider, input, None=value)
        """
        value = option["value"]
        is_integer = False
        multiplier = 1

        if "type" in option and option["type"] == "int":
            is_integer = True
        if "multiplier" in option:
            multiplier = option["multiplier"]

        if type != "slider":
            if is_integer:
                try:
                    value = round(int(value), 0)
                except Exception as e:
                    value = 0
            else:
                try:
                    value = float(value)
                except Exception as e:
                    value = 0.0

            if "min" in option and value < option["min"]:
                value = option["min"]
            elif "max" in option and value > option["max"]:
                value = option["max"]

            # update connected input field
            self.window.ui.config[parent_id][key].input.setText(str(value))

        slider_value = round(float(value) * multiplier, 0)

        # from slider
        if type == "slider":
            input_value = value / multiplier
            if is_integer:
                input_value = round(int(input_value), 0)
            txt = "{}".format(input_value)
            self.window.ui.config[parent_id][key].input.setText(txt)

        # from input
        elif type == "input":
            if "min" in option and slider_value < option["min"] * multiplier:
                slider_value = option["min"] * multiplier
            elif "max" in option and slider_value > option["max"] * multiplier:
                slider_value = option["max"] * multiplier
            self.window.ui.config[parent_id][key].slider.setValue(slider_value)

        # from value
        else:
            self.window.ui.config[parent_id][key].input.setText(str(value))
            self.window.ui.config[parent_id][key].slider.setValue(slider_value)

    def on_update(
            self,
            parent_id: str,
            key: str,
            option: dict,
            value: any,
            type: str = None,
            hooks: bool = True
    ):
        """
        Event: on slider update

        :param parent_id: Parent ID
        :param key: Option key
        :param option: Option data
        :param value: New value
        :param type: Update from field type (slider, input, None=value)
        :param hooks: Run hooks
        """
        option['value'] = value
        self.apply(parent_id, key, option, type)

        # on update hooks
        if hooks:
            hook_name = "update.{}.{}".format(parent_id, key)
            if self.window.ui.has_hook(hook_name):
                hook = self.window.ui.get_hook(hook_name)
                try:
                    hook(key, value, type)
                except Exception as e:
                    self.window.core.debug.log(e)

    def get_value(
            self,
            parent_id: str,
            key: str,
            option: dict
    ) -> any:
        """
        Get slider value

        :param parent_id: Parent ID
        :param key: Option key
        :param option: Option data
        :return: Slider value (int or float)
        """
        is_integer = False
        multiplier = 1
        if "type" in option and option["type"] == "int":
            is_integer = True
        if "multiplier" in option:
            multiplier = option["multiplier"]
        value = self.window.ui.config[parent_id][key].slider.value()
        if is_integer:
            return round(int(value), 0)
        else:
            return value / multiplier
