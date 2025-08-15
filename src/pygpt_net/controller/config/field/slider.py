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

from typing import Any, Optional, Dict, Union


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
            option: Dict[str, Any],
            type: Optional[str] = None
    ):
        """
        Apply value to slider

        :param parent_id: Options parent ID
        :param key: Option key
        :param option: Option data
        :param type: Update from type (slider, input, None=value)
        """
        if "value" not in option:
            return

        ui = self.window.ui
        cfg_parent = ui.config.get(parent_id)
        field = cfg_parent.get(key) if cfg_parent else None

        is_integer = option.get("type") == "int"
        multiplier = option.get("multiplier", 1)

        value = option["value"]

        if type != "slider":
            if is_integer:
                try:
                    value = round(int(float(value)), 0)
                except Exception:
                    value = 0
            else:
                try:
                    value = float(value)
                except Exception:
                    value = 0.0

            min_v = option.get("min")
            max_v = option.get("max")
            if min_v is not None and value < min_v:
                value = min_v
            elif max_v is not None and value > max_v:
                value = max_v

            if field:
                field.input.setText(str(value))

        slider_value = round(float(value) * multiplier, 0)

        if type == "slider":
            input_value = value / multiplier
            if is_integer:
                try:
                    input_value = round(int(float(input_value)), 0)
                except Exception:
                    input_value = 0
            if field:
                field.input.setText(str(input_value))
        elif type == "input":
            min_v = option.get("min")
            max_v = option.get("max")
            if min_v is not None and slider_value < min_v * multiplier:
                slider_value = min_v * multiplier
            elif max_v is not None and slider_value > max_v * multiplier:
                slider_value = max_v * multiplier
            if field:
                field.slider.setValue(slider_value)
        else:
            if field:
                field.slider.setValue(slider_value)

    def on_update(
            self,
            parent_id: str,
            key: str,
            option: Dict[str, Any],
            value: Any,
            type: Optional[str] = None,
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

        if hooks:
            hook_name = f"update.{parent_id}.{key}"
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
            option: Dict[str, Any]
    ) -> Union[int, float]:
        """
        Get slider value

        :param parent_id: Parent ID
        :param key: Option key
        :param option: Option data
        :return: Slider value (int or float)
        """
        is_integer = option.get("type") == "int"
        multiplier = option.get("multiplier", 1)
        value = self.window.ui.config[parent_id][key].slider.value()
        if is_integer:
            return round(int(value), 0)
        else:
            return value / multiplier