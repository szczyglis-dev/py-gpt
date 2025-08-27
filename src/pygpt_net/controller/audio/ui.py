#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.27 07:00:00                  #
# ================================================== #

from pygpt_net.utils import trans


class UI:
    def __init__(self, window=None):
        """
        Audio/voice UI controller

        :param window: Window instance
        """
        self.window = window
        self.recording = False

        self._input_bar = None
        self._input_btn = None
        self._input_control_bar = None
        self._input_control_btn = None
        self._output_bar = None
        self._output_btn = None

    def get_input_bar(self):
        """
        Get input bar widget

        :return: input bar widget
        """
        if self._input_bar is not None:
            return self._input_bar
        if "audio.input.btn" not in self.window.ui.plugin_addon:
            return None
        self._input_bar = self.window.ui.plugin_addon['audio.input.btn'].bar
        return self._input_bar

    def get_input_control_bar(self):
        """
        Get input control bar widget

        :return: input control bar widget
        """
        if self._input_control_bar is not None:
            return self._input_control_bar
        if 'voice.control.btn' not in self.window.ui.nodes:
            return None
        self._input_control_bar = self.window.ui.nodes['voice.control.btn'].bar
        return self._input_control_bar

    def get_output_bar(self):
        """
        Get output bar widget

        :return: output bar widget
        """
        if self._output_bar is not None:
            return self._output_bar
        if "audio.output.bar" not in self.window.ui.plugin_addon:
            return None
        self._output_bar = self.window.ui.plugin_addon['audio.output.bar']
        return self._output_bar

    def get_input_btn(self):
        """
        Get input bar widget

        :return: input btn widget
        """
        if self._input_btn is not None:
            return self._input_btn
        if "audio.input.btn" not in self.window.ui.plugin_addon:
            return None
        self._input_btn = self.window.ui.plugin_addon['audio.input.btn']
        return self._input_btn

    def get_input_control_btn(self):
        """
        Get input control btn widget

        :return: input control btn widget
        """
        if self._input_control_btn is not None:
            return self._input_control_btn
        if 'voice.control.btn' not in self.window.ui.nodes:
            return None
        self._input_control_btn = self.window.ui.nodes['voice.control.btn']
        return self._input_control_btn

    def get_output_btn(self):
        """
        Get output btn widget

        :return: output btn widget
        """
        if self._output_btn is not None:
            return self._output_btn
        if "audio.output" not in self.window.ui.plugin_addon:
            return None
        self._output_btn = self.window.ui.plugin_addon['audio.output']
        return self._output_btn

    # --- Input events ---

    def on_input_volume_change(self, value: int, mode: str = 'input'):
        """
        Input volume slider change event

        :param value: slider value
        :param mode: 'input' or 'control' mode
        """
        bar = self.get_output_bar()
        if bar:
            bar.setLevel(value)

    def on_input_device_change(self, index: int):
        """
        Input device combo change event

        :param index: combo index
        """
        pass

    def on_input_enable(self, mode: str = 'input'):
        """
        Input enable checkbox change event

        :param mode: 'input' or 'control' mode
        """
        self.window.ui.nodes['input'].set_icon_visible("mic", True)
        if mode == "input":
            return
        btn = self.get_input_btn() if mode == 'input' else self.get_input_control_btn()
        if btn:
            btn.setVisible(True)

    def on_input_disable(self, mode: str = 'input'):
        """
        Input disabled button click event

        :param mode: 'input' or 'control' mode
        """
        self.window.ui.nodes['input'].set_icon_visible("mic", False)
        if mode == "input":
            return
        btn = self.get_input_btn() if mode == 'input' else self.get_input_control_btn()
        if btn:
            btn.setVisible(False)

    def on_input_continuous_enable(self, checked: bool, mode: str = 'input'):
        """
        Input enable checkbox change event

        :param checked: checkbox state
        :param mode: 'input' or 'control' mode
        """
        btn = self.get_input_btn() if mode == 'input' else self.get_input_control_btn()
        if btn:
            btn.notepad_footer.setVisible(True)

    def on_input_continuous_disable(self, mode: str = 'input'):
        """
        Input disabled button click event

        :param mode: 'input' or 'control' mode
        """
        btn = self.get_input_btn() if mode == 'input' else self.get_input_control_btn()
        if btn:
            btn.notepad_footer.setVisible(False)

    def on_input_begin(self, mode: str = 'input'):
        """
        Input begin button click event

        :param mode: 'input' or 'control' mode
        """
        self.recording = True
        self.window.ui.nodes['input'].set_icon_state("mic", True)
        if mode == "input":
            self.window.controller.chat.common.lock_input()
            return
        btn = self.get_input_btn() if mode == 'input' else self.get_input_control_btn()
        btn.btn_toggle.setText(trans('audio.speak.btn.stop'))
        btn.btn_toggle.setToolTip(trans('audio.speak.btn.stop.tooltip'))

    def on_input_end(self, mode: str = 'input'):
        """
        Input end button click event

        :param mode: 'input' or 'control' mode
        """
        self.recording = False
        self.window.ui.nodes['input'].set_icon_state("mic", False)
        if mode == "input":
            self.window.controller.chat.common.unlock_input()
            return
        btn = self.get_input_btn() if mode == 'input' else self.get_input_control_btn()
        btn.btn_toggle.setText(trans('audio.speak.btn'))
        btn.btn_toggle.setToolTip(trans('audio.speak.btn.tooltip'))

    def on_input_cancel(self):
        """
        Input cancel button click event
        """
        pass

    # --- Output events ---

    def on_output_volume_change(self, value: int):
        """
        Output volume slider change event
        :param value: slider value
        """
        if self.recording:
            return
        bar = self.get_output_bar()
        if bar:
            bar.setLevel(value)

    def on_output_device_change(self, index: int):
        """
        Output device combo change event

        :param index: combo index
        """
        pass

    def on_output_enable(self):
        """
        Output enable checkbox change event
        """
        pass

    def on_output_disable(self):
        """
        Output disabled button click event
        """
        pass

    def on_output_begin(self):
        """
        Output begin button click event
        """
        self.window.controller.audio.start_speaking()

    def on_output_end(self):
        """
        Output end button click event
        """
        pass

    def on_output_cancel(self):
        """
        Output cancel button click event
        """
        pass