#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.05.02 19:00:00                  #
# ================================================== #

import pyaudio
import wave
import os

from PySide6.QtCore import QTimer

from pygpt_net.core.access.events import AppEvent
from pygpt_net.utils import trans


class Simple:

    TIMEOUT_SECONDS = 120  # 2 minutes, max recording time before timeout
    MIN_FRAMES = 25  # minimum frames to start transcription

    def __init__(self, plugin=None):
        """
        Simple audio input handler

        :param plugin: plugin instance
        """
        self.plugin = plugin
        self.is_recording = False
        self.frames = []
        self.p = None
        self.stream = None
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

    def start_recording(self):
        """Start recording"""
        self.frames = []  # clear audio frames

        def callback(in_data, frame_count, time_info, status):
            self.frames.append(in_data)
            if self.is_recording:
                return (in_data, pyaudio.paContinue)
            else:
                return (in_data, pyaudio.paComplete)

        try:
            self.is_recording = True
            self.switch_btn_stop()

            # stop audio output if playing
            if self.plugin.window.controller.audio.is_playing():
                self.plugin.window.controller.audio.stop_output()

            # start timeout timer to prevent infinite recording
            if self.timer is None:
                self.timer = QTimer()
                self.timer.timeout.connect(self.stop_timeout)
                self.timer.start(self.TIMEOUT_SECONDS * 1000)

            self.p = pyaudio.PyAudio()
            self.stream = self.p.open(format=pyaudio.paInt16,
                                      channels=1,
                                      rate=44100,
                                      input=True,
                                      frames_per_buffer=1024,
                                      stream_callback=callback)

            self.plugin.window.ui.status(trans('audio.speak.now'))
            self.plugin.window.core.dispatcher.dispatch(AppEvent(AppEvent.INPUT_VOICE_LISTEN_STARTED))  # app event
            self.stream.start_stream()
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
        self.is_recording = False
        self.plugin.window.core.dispatcher.dispatch(AppEvent(AppEvent.INPUT_VOICE_LISTEN_STOPPED))  # app event
        if self.timer:
            self.timer.stop()
            self.timer = None
        self.switch_btn_start()  # switch button to start
        path = os.path.join(self.plugin.window.core.config.path, self.plugin.input_file)

        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
            self.p.terminate()

            # abort if timeout
            if timeout:
                self.plugin.window.ui.status("Aborted.".format(self.TIMEOUT_SECONDS))
                return

            if self.frames:
                if len(self.frames) < self.MIN_FRAMES:
                    self.plugin.window.ui.status(trans("status.audio.too_short"))
                    self.plugin.window.core.dispatcher.dispatch(AppEvent(AppEvent.VOICE_CONTROL_STOPPED))  # app event
                    return
                wf = wave.open(path, 'wb')
                wf.setnchannels(1)
                wf.setsampwidth(self.p.get_sample_size(pyaudio.paInt16))
                wf.setframerate(44100)
                wf.writeframes(b''.join(self.frames))
                wf.close()
                self.plugin.handle_thread(True)  # handle transcription in simple mode
        else:
            self.plugin.window.ui.status("")
