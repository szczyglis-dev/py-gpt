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

import os.path
import time
import speech_recognition as sr
import audioop

from PySide6.QtCore import Slot, Signal

from pygpt_net.utils import trans
from pygpt_net.plugin.base import BaseWorker, BaseSignals


class WorkerSignals(BaseSignals):
    transcribed = Signal(str, str)


class Worker(BaseWorker):
    def __init__(self, *args, **kwargs):
        super(Worker, self).__init__()
        self.signals = WorkerSignals()
        self.args = args
        self.kwargs = kwargs
        self.plugin = None
        self.path = None
        self.advanced = False
        self.transcribe = False

    @Slot()
    def run(self):
        """Run worker."""

        # from file
        if self.transcribe:
            self.handle_file()

        # from microphone
        else:
            if self.advanced:
                self.handle_advanced()
            else:
                self.handle_simple()

    def handle_file(self):
        """Handle file"""
        try:
            # do transcribe
            if os.path.exists(self.path):
                transcript = self.plugin.get_provider().transcribe(self.path)
                if transcript is not None and transcript.strip() != '':
                    self.signals.transcribed.emit(self.path, transcript)
                else:
                    self.status('Error: No transcript.')
        except Exception as e:
            self.plugin.window.ui.nodes['audio.transcribe.status'].setText("Failed. Error: {}".format(e))
            self.error(e)
            self.stopped()
            self.status('Error: {}'.format(e))

    def handle_simple(self):
        """Handle mic simple mode."""
        try:
            # do transcribe
            if os.path.exists(self.path):
                # set status
                self.status(trans('audio.speak.wait'))
                # transcribe audio
                transcript = self.plugin.get_provider().transcribe(self.path)
                self.status('')

                # handle transcript
                if transcript is not None and transcript.strip() != '':
                    self.response(transcript)

        except Exception as e:
            self.error(e)
            self.stopped()
            self.status('Error: {}'.format(e))

    def handle_advanced(self):
        """Handle mic advanced mode."""
        try:
            if not self.plugin.listening:
                return

            # print("Starting audio listener....")

            self.started()
            self.status('')

            with sr.Microphone() as source:
                while self.plugin.listening and not self.plugin.window.is_closing:
                    self.status('')

                    if self.plugin.stop:
                        self.stopped()
                        self.status('Stop.')
                        break

                    if not self.plugin.can_listen():
                        time.sleep(0.5)
                        continue

                    try:
                        recognizer = sr.Recognizer()

                        # set recognizer options
                        recognizer.energy_threshold = self.plugin.get_option_value(
                            'recognition_energy_threshold'
                        )
                        recognizer.dynamic_energy_threshold = \
                            self.plugin.get_option_value(
                                'recognition_dynamic_energy_threshold'
                            )
                        recognizer.dynamic_energy_adjustment_damping = \
                            self.plugin.get_option_value(
                                'recognition_dynamic_energy_adjustment_damping'
                            )
                        recognizer.dynamic_energy_adjustment_ratio = \
                            self.plugin.get_option_value(
                                'recognition_dynamic_energy_adjustment_ratio'
                            )
                        recognizer.pause_threshold = self.plugin.get_option_value(
                            'recognition_pause_threshold'
                        )
                        adjust_duration = self.plugin.get_option_value(
                            'recognition_adjust_for_ambient_noise_duration'
                        )

                        # adjust for ambient noise
                        if self.plugin.get_option_value('adjust_noise'):
                            recognizer.adjust_for_ambient_noise(
                                source,
                                duration=adjust_duration,
                            )
                            self.plugin.is_first_adjust = False

                        timeout = self.plugin.get_option_value('timeout')
                        phrase_length = self.plugin.get_option_value('phrase_length')

                        # check for magic word, if no magic word detected,
                        # then set to magic word timeout and length
                        if self.plugin.get_option_value('magic_word'):
                            if not self.plugin.magic_word_detected:
                                timeout = self.plugin.get_option_value(
                                    'magic_word_timeout'
                                )
                                phrase_length = self.plugin.get_option_value(
                                    'magic_word_phrase_length'
                                )

                        # set begin status
                        if self.plugin.can_listen():
                            if self.plugin.get_option_value('magic_word'):
                                if self.plugin.magic_word_detected:
                                    self.status(trans('audio.speak.now'))
                                else:
                                    self.status(trans('audio.magic_word.please'))
                            else:
                                self.status(trans('audio.speak.now'))

                        min_energy = self.plugin.get_option_value('min_energy')
                        ambient_noise_energy = min_energy * recognizer.energy_threshold

                        if timeout > 0 and phrase_length > 0:
                            audio_data = recognizer.listen(
                                source,
                                timeout,
                                phrase_length,
                            )
                        elif timeout > 0:
                            audio_data = recognizer.listen(
                                source,
                                timeout,
                            )
                        else:
                            audio_data = recognizer.listen(source)

                        if not self.plugin.can_listen():
                            continue

                        # transcript audio
                        raw_data = audio_data.get_wav_data()
                        is_stop_word = False

                        if raw_data:
                            # check RMS / energy
                            rms = audioop.rms(raw_data, 2)
                            if min_energy > 0:
                                self.status("{}: {} / {} (x{})".format(
                                    trans('audio.speak.energy'),
                                    rms,
                                    int(ambient_noise_energy),
                                    min_energy,
                                ))
                            if rms < ambient_noise_energy:
                                continue

                            # save audio file
                            with open(self.path, "wb") as audio_file:
                                audio_file.write(raw_data)

                            # do transcribe
                            if os.path.exists(self.path):

                                # set status
                                self.status(trans('audio.speak.wait'))

                                # transcribe audio
                                transcript = self.plugin.get_provider().transcribe(self.path)

                                # handle transcript
                                if transcript is not None and transcript.strip() != '':
                                    # fix if empty phrase
                                    is_empty_phrase = False
                                    transcript_check = transcript.strip().lower()
                                    for phrase in self.plugin.empty_phrases:
                                        phrase_check = phrase.strip().lower()
                                        if phrase_check in transcript_check:
                                            is_empty_phrase = True
                                            break

                                    if is_empty_phrase:
                                        continue

                                    if self.plugin.can_listen():
                                        self.response(transcript)

                                    # stop listening if not continuous mode or stop word detected
                                    stop_words = self.plugin.get_words('stop_words')
                                    if len(stop_words) > 0:
                                        is_stop_word = transcript.replace('.', '').strip().lower() in stop_words

                        if not self.plugin.get_option_value('continuous_listen') \
                                or is_stop_word:
                            self.stopped()
                            self.status('')  # clear status
                            break

                    except Exception as e:
                        print("Speech recognition error: {}".format(str(e)))

            self.destroyed()

        except Exception as e:
            self.error(e)
            self.destroyed()
            print("Audio input thread error: {}".format(str(e)))


class ControlWorker(BaseWorker):
    def __init__(self, *args, **kwargs):
        super(ControlWorker, self).__init__()
        self.signals = WorkerSignals()
        self.window = None
        self.args = args
        self.kwargs = kwargs
        self.path = None
        self.transcribe = False

    @Slot()
    def run(self):
        """Handle mic simple mode."""
        try:
            # do transcribe
            if os.path.exists(self.path):
                # set status
                self.status(trans('audio.speak.wait'))
                # transcribe audio
                transcript = self.window.core.plugins.get('audio_input').get_provider().transcribe(self.path)
                self.status('')

                # handle transcript
                if transcript is not None and transcript.strip() != '':
                    self.response(transcript)

        except Exception as e:
            self.error(e)
            self.stopped()
            self.status('Error: {}'.format(e))