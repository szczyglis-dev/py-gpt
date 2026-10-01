#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.24 11:00:00                  #
# ================================================== #

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from pygpt_net.core.events import AppEvent, RealtimeEvent
from pygpt_net.core.tabs.tab import Tab
from pygpt_net.utils import trans


class Simple:

    def __init__(self, plugin=None):
        """
        Simple audio input handler

        :param plugin: plugin instance
        """
        self.plugin = plugin
        self.is_recording = False
        self.timer = None
        self.backend_init_pending = False

    def toggle_realtime(
            self,
            state: bool = None,
            auto: bool = False
    ):
        """
        Toggle recording

        :param state: True to start recording, False to stop recording, None to toggle
        :param auto: True if called automatically (not by user)
        """
        if state is not None:
            if state and not self.is_recording:
                if not auto:
                    self.plugin.window.controller.realtime.prepare_new_turn()
                self.start_recording(realtime=True)
                if self.is_recording:
                    self.plugin.window.dispatch(RealtimeEvent(RealtimeEvent.RT_INPUT_AUDIO_MANUAL_START, {
                        "auto": auto,
                    }))
            elif not state:
                self.force_stop()
            else:
                self.force_stop()
            return
        if self.is_recording:
            self.stop_recording(realtime=True)
            if not auto:
                self.plugin.window.dispatch(RealtimeEvent(RealtimeEvent.RT_INPUT_AUDIO_MANUAL_STOP))
        else:
            if not auto:
                self.plugin.window.controller.realtime.prepare_new_turn()
            self.start_recording(realtime=True)
            if not auto and self.is_recording:
                self.plugin.window.dispatch(RealtimeEvent(RealtimeEvent.RT_INPUT_AUDIO_MANUAL_START))

    def toggle_recording(self, state: bool = None):
        """
        Toggle recording

        :param state: True to start recording, False to stop recording, None to toggle
        """
        if state is not None:
            if state and not self.is_recording:
                self.start_recording()
            elif not state and self.is_recording:
                self.stop_recording()
            return
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def switch_btn_stop(self):
        """Switch button to stop"""
        self.plugin.window.controller.audio.ui.on_input_begin("input")

    def switch_btn_start(self):
        """Switch button to start"""
        self.plugin.window.controller.audio.ui.on_input_end("input")

    def stop_timeout(self):
        """Stop timeout"""
        self.stop_recording(timeout=True)

    def start_recording(
            self,
            force: bool = False,
            realtime: bool = False,
            _backend_status_shown: bool = False
    ):
        """
        Start recording

        :param force: True to force recording
        :param realtime: True if called from realtime callback
        :param _backend_status_shown: internal guard for deferred Windows backend initialization
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
                self.plugin.window.controller.audio.ui.on_input_abort("input")
                return

        # On Windows, show the status before *any* first-use audio/provider work.
        # Local Whisper imports and the lazy Qt Multimedia/WASAPI backend can both
        # make the first microphone click noticeably slower. For regular audio
        # input, return to the event loop once so Qt paints the status before that
        # work starts. Realtime keeps its synchronous start semantics because its
        # caller emits start events immediately after this method returns.
        capture = self.plugin.window.core.audio.capture
        backend_init_status = (
            self.plugin.window.core.platforms.is_windows()
            and not capture.is_initialized()
        )
        if backend_init_status and not _backend_status_shown:
            if self.backend_init_pending:
                return
            self.plugin.window.update_status(trans('audio.backend.initializing'))
            try:
                status = self.plugin.window.ui.nodes.get('status')
                if status is not None:
                    status.msg.repaint()
                    status.timer.repaint()
                self.plugin.window.repaint()
                QApplication.sendPostedEvents()
                QApplication.processEvents()
            except Exception:
                pass
            if not realtime:
                self.backend_init_pending = True
                # Give Windows/Qt one short event-loop turn so the status is
                # actually presented before WASAPI or provider imports block.
                QTimer.singleShot(10, lambda: self._resume_backend_start(force, realtime))
                return

        # Prepare local provider before recording. In particular, do not capture
        # the first utterance while a missing local Whisper model is downloading.
        if not realtime:
            try:
                if not self.plugin.ensure_provider_ready():
                    self._clear_backend_init_status()
                    self.plugin.window.controller.audio.ui.on_input_abort("input")
                    return
            except Exception as e:
                self._clear_backend_init_status()
                self.plugin.error(e)
                self.switch_btn_start()
                self.plugin.window.controller.audio.ui.on_input_abort("input")
                return

        try:
            # enable continuous mode if notepad tab is active
            capture.set_repeat_callback(self.on_stop)
            continuous_enabled = self.plugin.window.core.config.get('audio.input.continuous', False)
            if continuous_enabled and self.plugin.window.controller.tabs.get_current_type() == Tab.TAB_NOTEPAD:
                capture.set_loop(True)  # set loop
            else:
                capture.set_loop(False)

            # stop audio output if playing
            self.plugin.window.controller.audio.stop_output()

            # set audio input mode
            capture.set_mode("input")

            # start timeout timer to prevent infinite recording
            # disable in continuous mode
            timeout = int(self.plugin.window.core.config.get('audio.input.timeout', 120) or 0) # get timeout
            timeout_continuous = self.plugin.window.core.config.get('audio.input.timeout.continuous', False) # enable continuous timeout
            if timeout > 0 and not realtime:
                if self.timer is None and (not continuous_enabled or timeout_continuous):
                    self.timer = QTimer()
                    self.timer.timeout.connect(self.stop_timeout)
                    self.timer.start(timeout * 1000)

            # Open capture once, without opening and closing a test stream first.
            if not capture.start():
                raise Exception("Audio input not working.")
            self.is_recording = True
            self.switch_btn_stop()
            self.plugin.window.update_status(trans('audio.speak.now'))
            self.plugin.window.dispatch(AppEvent(AppEvent.INPUT_VOICE_LISTEN_STARTED))  # app event
        except Exception as e:
            self.backend_init_pending = False
            self.is_recording = False
            if backend_init_status:
                self.plugin.window.update_status("")
            if self.timer is not None:
                self.timer.stop()
                self.timer = None
            self.plugin.window.core.debug.log(e)
            self.plugin.window.ui.dialogs.alert(e)
            if self.plugin.window.core.platforms.is_snap():
                self.plugin.window.ui.dialogs.open(
                    'snap_audio_input',
                    width=400,
                    height=200
                )
            self.switch_btn_start()  # switch button to start
            self.plugin.window.controller.audio.ui.on_input_abort("input")

    def _clear_backend_init_status(self):
        """Clear the Windows initialization message if it is still the active status."""
        try:
            if self.plugin.window.ui.get_status() == trans('audio.backend.initializing'):
                self.plugin.window.update_status("")
        except Exception:
            pass

    def _resume_backend_start(self, force: bool = False, realtime: bool = False):
        """Resume recording after Qt had a chance to paint the Windows init status."""
        self.backend_init_pending = False
        self.start_recording(
            force=force,
            realtime=realtime,
            _backend_status_shown=True,
        )

    def stop_recording(self, timeout: bool = False, realtime: bool = False):
        """
        Stop recording

        :param timeout: True if stopped due to timeout
        :param realtime: True if called from realtime callback
        """
        self.plugin.window.core.audio.capture.reset_audio_level()
        self.is_recording = False
        self.plugin.window.dispatch(AppEvent(AppEvent.INPUT_VOICE_LISTEN_STOPPED))  # app event
        if self.timer:
            self.timer.stop()
            self.timer = None
        self.switch_btn_start()  # switch button to start
        path = self.plugin.get_input_path()
        self.plugin.window.core.audio.capture.set_path(path)

        if self.plugin.window.core.audio.capture.has_source():
            self.plugin.window.core.audio.capture.stop()  # stop recording
            if (realtime
                    and self.plugin.window.controller.realtime.is_enabled()
                    and self.plugin.window.controller.realtime.is_auto_turn()):
                # Only VAD capture sends PCM through the live session. Manual
                # capture must submit the recorded file below, exactly once.
                return
            # abort if timeout
            if timeout:
                self.plugin.window.update_status("Aborted.".format(timeout))
                return

            capture = self.plugin.window.core.audio.capture
            if not capture.has_frames() or (not realtime and not capture.has_min_frames()):
                self.plugin.window.update_status(trans("status.audio.too_short"))
                return
            self.plugin.handle_thread(True)  # handle transcription in simple mode
        else:
            self.plugin.window.update_status("")

    def force_stop(self):
        """Stop recording immediately without submitting/transcribing it."""
        self.is_recording = False
        if self.timer is not None:
            try:
                self.timer.stop()
                self.timer.deleteLater()
            except Exception:
                pass
            self.timer = None
        self.plugin.window.dispatch(AppEvent(AppEvent.INPUT_VOICE_LISTEN_STOPPED))  # app event
        self.switch_btn_start()  # switch button to start
        try:
            self.plugin.window.core.audio.capture.reset_audio_level()
        except Exception:
            pass
        if self.plugin.window.core.audio.capture.has_source():
            self.plugin.window.core.audio.capture.stop()  # stop recording

    def on_stop(self):
        """Handle auto-transcribe"""
        path = self.plugin.get_input_path()
        self.plugin.window.core.audio.capture.set_path(path)
        self.plugin.window.core.audio.capture.stop()
        self.plugin.window.core.audio.capture.start()
        self.plugin.handle_thread(True)
