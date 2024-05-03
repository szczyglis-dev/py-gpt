#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.05.03 15:00:00                  #
# ================================================== #

import pyaudio
import wave
import os

from PySide6.QtCore import QTimer, Slot
from PySide6.QtWidgets import QApplication

from pygpt_net.item.ctx import CtxItem
from pygpt_net.plugin.audio_input.worker import ControlWorker
from pygpt_net.core.access.events import ControlEvent, AppEvent
from pygpt_net.utils import trans


class Voice:

    TIMEOUT_SECONDS = 120  # 2 minutes, max recording time before timeout

    def __init__(self, window=None):
        """
        Accessibility voice controller

        :param window: Window instance
        """
        self.window = window
        self.is_recording = False
        self.frames = []
        self.p = None
        self.stream = None
        self.timer = None
        self.input_file = "voice_control.wav"
        self.thread_started = False
        self.audio_disabled_events = [
            AppEvent.INPUT_CALL,
            AppEvent.VOICE_CONTROL_TOGGLE,
            AppEvent.CTX_END,
        ]
        self.confirm_events = [
            ControlEvent.NOTEPAD_CLEAR,
            ControlEvent.CALENDAR_CLEAR,
        ]
        self.pending_text = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.play_audio)
        self.delay_msec = 500

    def setup(self):
        """Setup voice control"""
        self.update()

    def delayed_play(self, text: str):
        """
        Delayed play audio

        :param text: text to play
        """
        self.pending_text = text
        self.timer.start(self.delay_msec)

    def play_audio(self):
        """Play current audio"""
        self.timer.stop()
        if self.pending_text is not None:
            self.window.controller.audio.read_text(self.pending_text)
            self.pending_text = None

    def play(self, event: AppEvent):
        """
        Play audio event

        :param event: AppEvent
        """
        mic_events = [
            AppEvent.VOICE_CONTROL_STARTED,
            AppEvent.VOICE_CONTROL_STOPPED,
            AppEvent.VOICE_CONTROL_SENT,
            AppEvent.INPUT_VOICE_LISTEN_STARTED,
            AppEvent.INPUT_VOICE_LISTEN_STOPPED,
        ]
        always_play = [
            AppEvent.VOICE_CONTROL_UNRECOGNIZED,
        ]
        if event.name in mic_events and self.window.core.config.get("access.microphone.notify"):
            if event.name in [AppEvent.VOICE_CONTROL_STARTED, AppEvent.INPUT_VOICE_LISTEN_STARTED]:
                if self.window.core.config.get("access.audio.notify.execute"):
                    self.window.controller.audio.play_sound("click_on.mp3")
            elif event.name in [
                AppEvent.VOICE_CONTROL_STOPPED,
                AppEvent.VOICE_CONTROL_SENT,
                AppEvent.INPUT_VOICE_LISTEN_STOPPED
            ]:
                if self.window.core.config.get("access.audio.notify.execute"):
                    self.window.controller.audio.play_sound("click_off.mp3")
            return

        if not self.window.core.config.get("access.audio.event.speech") and event.name not in always_play:
            return

        if event.name not in self.audio_disabled_events:
            trans_key = "event.audio." + event.name

            if event.name == AppEvent.CTX_SELECTED:
                self.delayed_play(
                    self.window.core.access.voice.get_selected_ctx()  # with info about ctx
                )
            elif event.name == AppEvent.MODE_SELECTED:
                self.delayed_play(
                    self.window.core.access.voice.get_selected_mode()  # with info about mode
                )
            elif event.name == AppEvent.MODEL_SELECTED:
                self.delayed_play(
                    self.window.core.access.voice.get_selected_model()  # with info about model
                )
            elif event.name == AppEvent.PRESET_SELECTED:
                self.delayed_play(
                    self.window.core.access.voice.get_selected_preset()  # with info about preset
                )
            elif event.name == AppEvent.TAB_SELECTED:
                self.delayed_play(
                    self.window.core.access.voice.get_selected_tab()  # with info about tab
                )
            elif event.name == AppEvent.CTX_END:
                if not self.window.controller.plugins.is_type_enabled("audio.output"):
                    self.delayed_play(trans(trans_key))  # only if audio output is disabled
            else:
                # handle rest of events
                self.delayed_play(trans(trans_key))
            self.window.core.debug.info("AUDIO EVENT PLAY: " + event.name)

    def update(self):
        """Update voice control"""
        if self.window.core.config.get("access.voice_control"):
            self.window.ui.nodes['voice.control.btn'].setVisible(True)
        else:
            self.window.ui.nodes['voice.control.btn'].setVisible(False)

    def toggle_recording(self):
        """Toggle recording"""
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def switch_btn_stop(self):
        """Switch button to stop"""
        self.window.ui.nodes['voice.control.btn'].btn_toggle.setText(trans('audio.speak.btn.stop'))
        self.window.ui.nodes['voice.control.btn'].btn_toggle.setToolTip(
            trans('audio.speak.btn.stop.tooltip'))

    def switch_btn_start(self):
        """Switch button to start"""
        self.window.ui.nodes['voice.control.btn'].btn_toggle.setText(trans('audio.control.btn'))
        self.window.ui.nodes['voice.control.btn'].btn_toggle.setToolTip(trans('audio.speak.btn.tooltip'))

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

            self.window.ui.status(trans('audio.speak.now'))
            self.window.core.dispatcher.dispatch(AppEvent(AppEvent.VOICE_CONTROL_STARTED))  # app event
            self.stream.start_stream()
        except Exception as e:
            self.is_recording = False
            self.window.core.debug.log(e)
            self.window.ui.dialogs.alert(e)
            if self.window.core.platforms.is_snap():
                self.window.ui.dialogs.open(
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
        if self.timer:
            self.timer.stop()
            self.timer = None
        self.switch_btn_start()  # switch button to start
        path = os.path.join(self.window.core.config.path, self.input_file)

        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
            self.p.terminate()

            # abort if timeout
            if timeout:
                self.window.core.dispatcher.dispatch(AppEvent(AppEvent.VOICE_CONTROL_STOPPED))  # app event
                self.window.ui.status("Aborted.".format(self.TIMEOUT_SECONDS))
                return

            if self.frames:
                wf = wave.open(path, 'wb')
                wf.setnchannels(1)
                wf.setsampwidth(self.p.get_sample_size(pyaudio.paInt16))
                wf.setframerate(44100)
                wf.writeframes(b''.join(self.frames))
                wf.close()
                self.window.core.dispatcher.dispatch(AppEvent(AppEvent.VOICE_CONTROL_SENT))  # app event
                self.handle_thread(True)  # handle transcription in simple mode
        else:
            self.window.core.dispatcher.dispatch(AppEvent(AppEvent.VOICE_CONTROL_STOPPED))  # app event

    def handle_thread(self, force: bool = False):
        """
        Handle listener thread

        :param force: force start
        """
        if self.thread_started and not force:
            return

        try:
            # worker
            worker = ControlWorker()
            worker.window = self.window
            worker.path = os.path.join(
                self.window.core.config.path,
                self.input_file,
            )
            # signals
            worker.signals.transcribed.connect(self.handle_transcribed)
            worker.signals.finished.connect(self.handle_input)
            worker.signals.destroyed.connect(self.handle_destroy)
            worker.signals.started.connect(self.handle_started)
            worker.signals.stopped.connect(self.handle_stop)
            worker.signals.status.connect(self.handle_status)
            worker.signals.error.connect(self.handle_error)

            # start
            self.window.threadpool.start(worker)

        except Exception as e:
            self.window.core.debug.log(e)

    @Slot(str, str)
    def handle_transcribed(self, path: str, text: str):
        """
        Handle transcribed text

        :param path: audio file path
        :param text: transcribed text
        """
        self.window.tools.get("transcriber").on_transcribe(path, text)

    @Slot(object, object)
    def handle_input(self, text: str, ctx: CtxItem = None):
        """
        Insert text to input and send

        :param text: text
        :param ctx: CtxItem
        """
        if text is None or text.strip() == '':
            return
        self.window.core.debug.info("VOICE CONTROL INPUT: " + text)
        commands = self.window.core.access.voice.recognize_commands(text)
        if len(commands) > 0:
            for command in commands:
                cmd = command["cmd"]
                params = command.get("params", "")
                self.window.ui.status("Voice command: " + cmd)
                event = ControlEvent(cmd)
                event.data = {
                    "params": params,
                }
                self.window.core.dispatcher.dispatch(event)
                self.window.core.debug.info("VOICE CONTROL COMMAND: " + cmd, params)
                trans_key = "event.control." + cmd

                if cmd in self.confirm_events:
                    self.window.ui.status(trans("event.audio.confirm"))
                else:
                    event_name = trans(trans_key)
                    if event_name == trans_key:
                        event_name = cmd
                    self.window.ui.status("Voice command: " + event_name)
                    QApplication.processEvents()

            # play OK sound
            if self.window.core.config.get("access.audio.notify.execute"):
                self.window.controller.audio.play_sound("ok.mp3")

        else:
            self.window.ui.status("Voice command not recognized.")
            QApplication.processEvents()
            self.window.core.dispatcher.dispatch(AppEvent(AppEvent.VOICE_CONTROL_UNRECOGNIZED))

    @Slot(object)
    def handle_error(self, data: str):
        """
        Handle thread error signal

        :param data: message
        """
        self.window.ui.status(str(data))

    @Slot(object)
    def handle_status(self, data: str):
        """
        Handle thread status msg signal

        :param data: message
        """
        self.window.ui.status(str(data))

    @Slot()
    def handle_destroy(self):
        """Handle listener destroyed"""
        self.thread_started = False

    @Slot()
    def handle_started(self):
        """Handle listening started"""
        self.thread_started = True

    @Slot()
    def handle_stop(self):
        """Handle stop listening"""
        self.thread_started = False
