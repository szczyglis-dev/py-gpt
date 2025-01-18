#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.01.18 23:00:00                  #
# ================================================== #

import os

from PySide6.QtCore import QTimer

from pygpt_net.core.events import AppEvent
from pygpt_net.core.tabs.tab import Tab
from pygpt_net.utils import trans


class Simple:

    MIN_FRAMES = 25  # minimum frames to start transcription

    def __init__(self, plugin=None):
        """
        Simple audio input handler

        :param plugin: plugin instance
        """
        self.plugin = plugin
        self.is_recording = False
        self.timer = None

    def toggle_recording(self):
        """Toggle recording"""
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def switch_btn_stop(self):
        """Switch button to stop"""
        self.plugin.window.ui.plugin_addon['audio.input.btn'].btn_toggle.setText(trans('audio.speak.btn.stop'))
        self.plugin.window.ui.plugin_addon['audio.input.btn'].btn_toggle.setToolTip(
            trans('audio.speak.btn.stop.tooltip'))

    def switch_btn_start(self):
        """Switch button to start"""
        self.plugin.window.ui.plugin_addon['audio.input.btn'].btn_toggle.setText(trans('audio.speak.btn'))
        self.plugin.window.ui.plugin_addon['audio.input.btn'].btn_toggle.setToolTip(trans('audio.speak.btn.tooltip'))

    def stop_timeout(self):
        """Stop timeout"""
        self.stop_recording(timeout=True)

    def start_recording(self, force: bool = False):
        """
        Start recording

        :param force: True to force recording
        """
        # display snap warning if not displayed yet
        if (not self.plugin.window.core.config.get("audio.input.snap", False)
                or not self.plugin.window.core.config.has("audio.input.snap")):
            if self.plugin.window.core.platforms.is_snap():
                self.plugin.window.ui.dialogs.open(
                    'snap_audio_input',
                    width=400,
                    height=200
                )
                self.plugin.window.core.config.set("audio.input.snap", True)
                self.plugin.window.core.config.save()
                return

        # enable continuous mode if notepad tab is active
        self.plugin.window.core.audio.capture.stop_callback = self.on_stop
        continuous_enabled = self.plugin.window.core.config.get('audio.input.continuous', False)
        if continuous_enabled and self.plugin.window.controller.ui.tabs.get_current_type() == Tab.TAB_NOTEPAD:
            self.plugin.window.core.audio.capture.loop = True  # set loop
        else:
            self.plugin.window.core.audio.capture.loop = False

        try:
            # stop audio output if playing
            self.plugin.window.controller.audio.stop_output()

            # set audio volume bar
            self.plugin.window.core.audio.capture.set_bar(
                self.plugin.window.ui.plugin_addon['audio.input.btn'].bar
            )

            # start timeout timer to prevent infinite recording
            # disable in continuous mode
            timeout = int(self.plugin.window.core.config.get('audio.input.timeout', 120) or 0) # get timeout
            timeout_continuous = self.plugin.window.core.config.get('audio.input.timeout.continuous', False) # enable continuous timeout
            if timeout > 0:
                if self.timer is None and (not continuous_enabled or timeout_continuous):
                    self.timer = QTimer()
                    self.timer.timeout.connect(self.stop_timeout)
                    self.timer.start(timeout * 1000)

            if not force:
                if not self.plugin.window.core.audio.capture.check_audio_input():
                    raise Exception("Audio input not working.")
                    # IMPORTANT!!!!
                    # Stop here if audio input not working!
                    # This prevents the app from freezing when audio input is not working!

            self.is_recording = True
            self.switch_btn_stop()
            self.plugin.window.core.audio.capture.start()  # start recording if audio is OK
            self.plugin.window.update_status(trans('audio.speak.now'))
            self.plugin.window.dispatch(AppEvent(AppEvent.INPUT_VOICE_LISTEN_STARTED))  # app event
        except Exception as e:
            self.is_recording = False
            self.plugin.window.core.debug.log(e)
            self.plugin.window.ui.dialogs.alert(e)
            if self.plugin.window.core.platforms.is_snap():
                self.plugin.window.ui.dialogs.open(
                    'snap_audio_input',
                    width=400,
                    height=200
                )
            self.switch_btn_start()  # switch button to start

    def stop_recording(self, timeout: bool = False):
        """
        Stop recording

        :param timeout: True if stopped due to timeout
        """
        self.plugin.window.core.audio.capture.reset_audio_level()
        self.is_recording = False
        self.plugin.window.dispatch(AppEvent(AppEvent.INPUT_VOICE_LISTEN_STOPPED))  # app event
        if self.timer:
            self.timer.stop()
            self.timer = None
        self.switch_btn_start()  # switch button to start
        path = os.path.join(self.plugin.window.core.config.path, self.plugin.input_file)
        self.plugin.window.core.audio.capture.set_path(path)

        if self.plugin.window.core.audio.capture.has_source():
            self.plugin.window.core.audio.capture.stop()  # stop recording
            # abort if timeout
            if timeout:
                self.plugin.window.update_status("Aborted.".format(timeout))
                return

            if self.plugin.window.core.audio.capture.has_frames():
                frames = self.plugin.window.core.audio.capture.get_frames()
                if len(frames) < self.MIN_FRAMES:
                    self.plugin.window.update_status(trans("status.audio.too_short"))
                    self.plugin.window.dispatch(AppEvent(AppEvent.VOICE_CONTROL_STOPPED))  # app event
                    return

                self.plugin.handle_thread(True)  # handle transcription in simple mode
        else:
            self.plugin.window.update_status("")


    def on_stop(self):
        """Handle auto-transcribe"""
        path = os.path.join(self.plugin.window.core.config.path, self.plugin.input_file)
        self.plugin.window.core.audio.capture.set_path(path)
        self.plugin.window.core.audio.capture.stop()
        self.plugin.window.core.audio.capture.start()
        self.plugin.handle_thread(True)
