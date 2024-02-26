#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.26 20:00:00                  #
# ================================================== #

import pyaudio
import wave
import os

from pygpt_net.utils import trans


class Simple:
    def __init__(self, plugin=None):
        """
        Simple audio input handler

        :param plugin: plugin instance
        """
        self.plugin = plugin
        self.is_recording = False
        self.frames = []
        self.stream = None

    def toggle_recording(self):
        """Toggle recording"""
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        """Start recording"""
        self.is_recording = True
        self.plugin.window.ui.plugin_addon['audio.input.btn'].btn_toggle.setText(trans('audio.speak.btn.stop'))
        self.plugin.window.ui.plugin_addon['audio.input.btn'].btn_toggle.setToolTip(trans('audio.speak.btn.stop.tooltip'))
        self.p = pyaudio.PyAudio()

        def callback(in_data, frame_count, time_info, status):
            self.frames.append(in_data)
            if self.is_recording:
                return (in_data, pyaudio.paContinue)
            else:
                return (in_data, pyaudio.paComplete)

        self.stream = self.p.open(format=pyaudio.paInt16,
                                  channels=1,
                                  rate=44100,
                                  input=True,
                                  frames_per_buffer=1024,
                                  stream_callback=callback)

        self.plugin.window.ui.status(trans('audio.speak.now'))
        self.stream.start_stream()

    def stop_recording(self):
        """Stop recording"""
        self.is_recording = False
        self.plugin.window.ui.plugin_addon['audio.input.btn'].btn_toggle.setText(trans('audio.speak.btn'))
        self.plugin.window.ui.plugin_addon['audio.input.btn'].btn_toggle.setToolTip(trans('audio.speak.btn.tooltip'))
        path = os.path.join(self.plugin.window.core.config.path, self.plugin.input_file)

        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
            self.p.terminate()

            wf = wave.open(path, 'wb')
            wf.setnchannels(1)
            wf.setsampwidth(self.p.get_sample_size(pyaudio.paInt16))
            wf.setframerate(44100)
            wf.writeframes(b''.join(self.frames))
            wf.close()
            self.plugin.handle_thread(True)  # handle transcription in simple mode
