#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.18 14:10:00
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
        self._input_record_bar = None
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

    def get_input_record_bar(self):
        """
        Get dedicated input recording status bar widget.

        :return: input recording widget
        """
        if self._input_record_bar is not None:
            return self._input_record_bar
        if "audio.input.bar" not in self.window.ui.plugin_addon:
            return None
        self._input_record_bar = self.window.ui.plugin_addon['audio.input.bar']
        return self._input_record_bar

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


    def _notepad_widgets(self):
        """Return live Notepad widgets that expose the dedicated mic control."""
        widgets = getattr(self.window.ui, 'notepad', {}) or {}
        return [widget for widget in widgets.values() if widget is not None]

    def _set_notepad_mic_visible(self, visible: bool):
        for widget in self._notepad_widgets():
            if hasattr(widget, 'set_mic_visible'):
                widget.set_mic_visible(visible)
            if not visible and hasattr(widget, 'reset_recording_ui'):
                widget.reset_recording_ui()

    def _set_notepad_mic_state(self, active: bool):
        for widget in self._notepad_widgets():
            if hasattr(widget, 'set_mic_state'):
                widget.set_mic_state(active)

    def _set_notepad_record_pending(self):
        for widget in self._notepad_widgets():
            if hasattr(widget, 'set_record_pending'):
                widget.set_record_pending()

    def _set_notepad_recording_active(self):
        for widget in self._notepad_widgets():
            if hasattr(widget, 'set_recording_active'):
                widget.set_recording_active()

    def _set_notepad_record_level(self, value: int):
        for widget in self._notepad_widgets():
            if hasattr(widget, 'set_record_level'):
                widget.set_record_level(value)

    def _reset_notepad_recording_ui(self):
        for widget in self._notepad_widgets():
            if hasattr(widget, 'reset_recording_ui'):
                widget.reset_recording_ui()

    # --- Input events ---

    def on_input_volume_change(self, value: int, mode: str = 'input'):
        """
        Input volume slider change event

        :param value: slider value
        :param mode: 'input' or 'control' mode
        """
        if mode == 'control':
            bar = self.get_input_control_bar()
            if bar:
                bar.setLevel(value)
            return

        bar = self.get_input_bar()
        if bar:
            bar.setLevel(value)

        status = self.get_input_record_bar()
        if status:
            status.setLevel(value)

        self._set_notepad_record_level(value)

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
            self._set_notepad_mic_visible(True)
            status = self.get_input_record_bar()
            if status:
                status.reset()
            self._reset_notepad_recording_ui()
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
            self._set_notepad_mic_visible(False)
            status = self.get_input_record_bar()
            if status:
                status.reset()
            self._reset_notepad_recording_ui()
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
            self._set_notepad_mic_state(True)
            self._set_notepad_recording_active()
            status = self.get_input_record_bar()
            if status:
                status.show_recording()
        if mode in ["input", "realtime"]:
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
            self._set_notepad_mic_state(False)
            self._reset_notepad_recording_ui()
            status = self.get_input_record_bar()
            if status:
                status.reset()
        if mode in ["input", "realtime"]:
            self.window.controller.chat.common.unlock_input()
            return
        btn = self.get_input_btn() if mode == 'input' else self.get_input_control_btn()
        btn.btn_toggle.setText(trans('audio.speak.btn'))
        btn.btn_toggle.setToolTip(trans('audio.speak.btn.tooltip'))

    def on_input_cancel(self):
        """
        Input cancel button click event
        """
        status = self.get_input_record_bar()
        if status:
            status.abort()
        self._reset_notepad_recording_ui()

    def on_input_toggle_requested(self, mode: str = 'input'):
        """Show the compact pending indicator immediately after the mic click."""
        if mode != 'input':
            return
        status = self.get_input_record_bar()
        if status:
            status.show_pending()
        self._set_notepad_record_pending()

    def on_input_abort(self, mode: str = 'input'):
        """Hide the compact pending/recording indicator after a failed start."""
        if mode != 'input':
            return
        status = self.get_input_record_bar()
        if status:
            status.abort()
        self._reset_notepad_recording_ui()

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