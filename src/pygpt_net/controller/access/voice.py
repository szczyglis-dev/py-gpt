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

from typing import Optional, List, Dict, Any

import os

from PySide6.QtCore import QTimer, Slot
from PySide6.QtWidgets import QApplication

from pygpt_net.item.ctx import CtxItem
from pygpt_net.plugin.audio_input.worker import ControlWorker
from pygpt_net.core.events import ControlEvent, AppEvent
from pygpt_net.utils import trans


class Voice:

    MIN_FRAMES = 25  # minimum frames to start transcription
    PLAY_DELAY = 500  # ms, delay before playing audio event

    def __init__(self, window=None):
        """
        Accessibility voice controller

        :param window: Window instance
        """
        self.window = window
        self.is_recording = False
        self.timer = None
        self.input_file = "voice_control.wav"
        self.thread_started = False
        self.audio_disabled_events = [
            AppEvent.INPUT_CALL,
            AppEvent.VOICE_CONTROL_TOGGLE,
        ]
        self.confirm_events = [
            ControlEvent.NOTEPAD_CLEAR,
            ControlEvent.CALENDAR_CLEAR,
        ]
        self.pending_text = None
        self.pending_event = None
        self.play_timer = QTimer(self.window)
        self.play_timer.timeout.connect(self.play_audio)

    def setup(self):
        """Setup voice control"""
        self.update()

    def delayed_play(self, text: str, event: AppEvent):
        """
        Delayed play audio

        :param text: text to play
        :param event: AppEvent
        """
        self.pending_text = text
        self.pending_event = event
        self.play_timer.start(self.PLAY_DELAY)

    def play_audio(self):
        """Play current pending audio"""
        self.play_timer.stop()
        if self.pending_text is not None and self.pending_event is not None:
            self.window.controller.audio.play_event(
                self.pending_text,
                self.pending_event,
            )  # use cached audio if available
            self.pending_text = None
            self.pending_event = None

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
                AppEvent.INPUT_VOICE_LISTEN_STOPPED,
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
                    self.window.core.access.helpers.get_selected_ctx(),  # with info about ctx
                    event,
                )
            elif event.name == AppEvent.MODE_SELECTED:
                self.delayed_play(
                    self.window.core.access.helpers.get_selected_mode(),  # with info about mode
                    event,
                )
            elif event.name == AppEvent.MODEL_SELECTED:
                self.delayed_play(
                    self.window.core.access.helpers.get_selected_model(),  # with info about model
                    event,
                )
            elif event.name == AppEvent.PRESET_SELECTED:
                self.delayed_play(
                    self.window.core.access.helpers.get_selected_preset(),  # with info about preset
                    event,
                )
            elif event.name == AppEvent.TAB_SELECTED:
                self.delayed_play(
                    self.window.core.access.helpers.get_selected_tab(),  # with info about tab
                    event,
                )
            elif event.name == AppEvent.CTX_END:
                if (not self.window.controller.plugins.is_type_enabled("audio.output") and
                        not self.window.controller.plugins.is_type_enabled("audio.control")):
                    self.delayed_play(
                        trans(trans_key),
                        event,
                    )  # only if audio output is disabled
            else:
                # handle rest of events
                self.delayed_play(
                    trans(trans_key),
                    event,
                )
            self.window.core.debug.info("AUDIO EVENT PLAY: " + event.name)

    def update(self):
        """Update voice control"""
        if self.window.core.config.get("access.voice_control"):
            self.window.ui.nodes['voice.control.btn'].setVisible(True)
        else:
            self.window.ui.nodes['voice.control.btn'].setVisible(False)

        self.window.controller.audio.update()  # update audio menu, etc.

    def enable_voice_control(self):
        """Enable voice control"""
        self.window.core.config.set("access.voice_control", True)
        self.window.core.config.save()
        self.update()

    def disable_voice_control(self):
        """Disable voice control"""
        self.window.core.config.set("access.voice_control", False)
        self.window.core.config.save()
        self.update()

    def toggle_voice_control(self):
        """Toggle voice control"""
        if self.is_voice_control_enabled():
            self.disable_voice_control()
        else:
            self.enable_voice_control()

    def is_voice_control_enabled(self) -> bool:
        """
        Check if voice control is enabled

        :return: True if enabled
        """
        return self.window.core.config.get("access.voice_control")

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
        # display snap warning if not displayed yet
        if (not self.window.core.config.get("audio.input.snap", False)
                or not self.window.core.config.has("audio.input.snap")):
            if self.window.core.platforms.is_snap():
                self.window.ui.dialogs.open(
                    'snap_audio_input',
                    width=400,
                    height=200
                )
                self.window.core.config.set("audio.input.snap", True)
                self.window.core.config.save()
                return
        try:
            self.is_recording = True
            self.switch_btn_stop()

            # stop audio output if playing
            if self.window.controller.audio.is_playing():
                self.window.controller.audio.stop_output()

            # set audio volume bar
            self.window.core.audio.capture.set_bar(
                self.window.ui.nodes['voice.control.btn'].bar
            )

            # start timeout timer to prevent infinite recording
            timeout = int(self.window.core.config.get('audio.input.timeout', 120) or 0)  # get timeout
            if timeout > 0:
                if self.timer is None:
                    self.timer = QTimer()
                    self.timer.timeout.connect(self.stop_timeout)
                    self.timer.start(timeout * 1000)

            if not self.window.core.audio.capture.check_audio_input():
                raise Exception("Audio input not working.")
                # IMPORTANT!!!!
                # Stop here if audio input not working!
                # This prevents the app from freezing when audio input is not working!

            self.window.core.audio.capture.start()  # start recording if audio is OK
            self.window.update_status(trans('audio.speak.now'))
            self.window.dispatch(AppEvent(AppEvent.VOICE_CONTROL_STARTED))  # app event
        except Exception as e:
            self.is_recording = False
            self.window.core.debug.log(e)
            self.window.ui.dialogs.alert(e)
            if self.window.core.platforms.is_snap():
                self.window.ui.dialogs.open(
                    'snap_audio_input',
                    width=400,
                    height=200,
                )
            self.switch_btn_start()  # switch button to start

    def stop_recording(self, timeout: bool = False):
        """
        Stop recording

        :param timeout: True if stopped due to timeout
        """
        self.window.core.audio.capture.reset_audio_level()
        self.is_recording = False
        if self.timer:
            self.timer.stop()
            self.timer = None
        self.switch_btn_start()  # switch button to start
        path = os.path.join(self.window.core.config.path, self.input_file)
        self.window.core.audio.capture.set_path(path)

        if self.window.core.audio.capture.has_source():
            self.window.core.audio.capture.stop()  # stop recording
            # abort if timeout
            if timeout:
                self.window.dispatch(AppEvent(AppEvent.VOICE_CONTROL_STOPPED))  # app event
                self.window.update_status("Aborted.".format(timeout))
                return

            if self.window.core.audio.capture.has_frames():
                frames = self.window.core.audio.capture.get_frames()
                if len(frames) < self.MIN_FRAMES:
                    self.window.update_status(trans("status.audio.too_short"))
                    self.window.dispatch(AppEvent(AppEvent.VOICE_CONTROL_STOPPED))  # app event
                    return
                self.window.dispatch(AppEvent(AppEvent.VOICE_CONTROL_SENT))  # app event
                self.handle_thread(True)  # handle transcription in simple mode
        else:
            self.window.update_status("")
            self.window.dispatch(AppEvent(AppEvent.VOICE_CONTROL_STOPPED))  # app event

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
    def handle_input(self, text: str, ctx: Optional[CtxItem] = None):
        """
        Insert text to input and send

        :param text: text
        :param ctx: CtxItem
        """
        if text is None or text.strip() == '':
            self.window.update_status("")
            return
        self.window.core.debug.info("VOICE CONTROL INPUT: " + text)
        commands = self.window.core.access.voice.recognize_commands(text)
        self.handle_commands(commands)

    def handle_commands(self, commands: List[Dict[str, Any]]):
        """
        Handle commands

        :param commands: commands list
        """
        unrecognized = False
        if len(commands) > 0:
            for command in commands:
                cmd = command["cmd"]
                params = command.get("params", "")
                self.window.update_status(trans("event.audio.cmd").format(cmd=cmd))
                event = ControlEvent(cmd)
                event.data = {
                    "params": params,
                }
                if event.name == "unrecognized":
                    unrecognized = True
                self.window.dispatch(event)
                self.window.core.debug.info("VOICE CONTROL COMMAND: " + cmd, params)
                trans_key = "event.control." + cmd

                if cmd in self.confirm_events:
                    self.window.update_status(trans("event.audio.confirm"))
                else:
                    event_name = trans(trans_key)
                    if event_name == trans_key:  # if no translation
                        event_name = cmd
                    self.window.update_status(trans("event.audio.cmd").format(cmd=event_name))
                    QApplication.processEvents()

            # play OK sound
            if not unrecognized:
                if self.window.core.config.get("access.audio.notify.execute"):
                    self.window.controller.audio.play_sound("ok.mp3")

    @Slot(object)
    def handle_error(self, data: str):
        """
        Handle thread error signal

        :param data: message
        """
        self.window.update_status(str(data))

    @Slot(object)
    def handle_status(self, data: str):
        """
        Handle thread status msg signal

        :param data: message
        """
        self.window.update_status(str(data))

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
