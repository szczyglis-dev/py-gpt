#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.15 19:00:00                  #
# ================================================== #
import os
import threading
import time

from PySide6.QtCore import QObject, Signal, Qt, Slot
import speech_recognition as sr
from openai import OpenAI
import audioop

from ..base_plugin import BasePlugin
from ...utils import trans


class Plugin(BasePlugin):
    def __init__(self):
        super(Plugin, self).__init__()
        self.id = "audio_openai_whisper"
        self.name = "Audio Input (OpenAI Whisper)"
        self.type = ['audio.input']
        self.description = "Enables speech recognition using OpenAI Whisper API"
        self.input_text = None
        self.window = None
        self.speech_enabled = False
        self.thread_started = False
        self.thread = None
        self.listening = False
        self.waiting = False
        self.magic_word_detected = False
        self.is_first_adjust = True
        self.empty_phrases = ['Thank you for watching']  # phrases to ignore (fix for empty phrases)
        self.order = 1
        self.init_options()

    def init_options(self):
        """
        Initializes options
        """
        self.add_option("model", "text", "whisper-1",
                        "Model",
                        "Specify model, default: whisper-1")
        self.add_option("timeout", "int", 1,
                        "Timeout",
                        "Speech recognition timeout", min=0, max=30, slider=True, tooltip="Timeout, default: 1")
        self.add_option("phrase_length", "int", 5,
                        "Phrase max length",
                        "Speech recognition phrase length", min=0, max=30, slider=True, tooltip="Phrase max length, "
                                                                                                "default: 5")
        self.add_option("min_energy", "int", 2000,
                        "Min. energy",
                        "Minimum energy (loudness) to start recording, 0 = disabled", min=0, max=30000, slider=True,
                        tooltip="Min. energy, default: 4000, 0 = disabled, adjust for your microphone")
        self.add_option("adjust_noise", "bool", True,
                        "Adjust ambient noise",
                        "Adjust for ambient noise")
        self.add_option("continuous_listen", "bool", True,
                        "Continuous listening",
                        "Continuous listening (do not stop after single input)")
        self.add_option("auto_send", "bool", True,
                        "Auto send",
                        "Automatically send input when received voice")
        self.add_option("wait_response", "bool", True,
                        "Wait for response",
                        "Wait for response before listening next input")
        self.add_option("magic_word", "bool", False,
                        "Magic word",
                        "Enable listening only after magic word, like 'Hey GPT' or 'OK GPT'")
        self.add_option("magic_word_reset", "bool", True,
                        "Reset Magic word",
                        "Reset Magic word after received (must be provided next time)")
        self.add_option("magic_words", "text", "OK, Okay, Hey GPT, OK GPT",
                        "Magic words",
                        "Specify magic words for 'Magic word' option: if received this word then start listening, "
                        "put words separated by coma, "
                        "Magic word option must be enabled, examples: Hey GPT, OK GPT")
        self.add_option("magic_word_timeout", "int", 1,
                        "Magic word timeout",
                        "Magic word recognition timeout", min=0, max=30, slider=True, tooltip="Timeout, default: 1")
        self.add_option("magic_word_phrase_length", "int", 2,
                        "Magic word phrase max length",
                        "Magic word phrase length", min=0, max=30, slider=True, tooltip="Phrase length, default: 2")
        self.add_option("prefix_words", "text", "",
                        "Prefix words",
                        "Specify prefix words: if defined then only phrases starting with this words will be sent "
                        "and rest will be ignored, put separated words by coma, eg. 'OK, Okay, GPT'. Leave empty to disable")
        self.add_option("stop_words", "text", "stop, exit, quit, end, finish, close, terminate, kill, halt, abort",
                        "Stop words",
                        "Specify stop words: if received this word then stop listening, put words separated by coma, "
                        "leave empty to disable, default: stop, exit, quit, end, finish, close, terminate, kill, "
                        "halt, abort")

    def setup(self):
        """
        Returns available config options

        :return: config options
        """
        return self.options

    def setup_ui(self):
        """
        Setup UI
        """
        # show/hide widget
        if self.enabled:
            pass
        else:
            pass

    def on_dispatch(self, event, data=None):
        """
        Receives events from dispatcher

        :param event: Event name
        :param data: Event data
        """
        if event == 'audio.input.toggle':
            self.toggle_speech(data)

    def get_stop_words(self):
        """
        Returns stop words

        :return: stop words
        """
        words_str = self.get_option_value('stop_words')
        words = []
        if words_str is not None and len(words_str) > 0 and words_str.strip() != ' ':
            words = words_str.split(',')
            # remove white-spaces
            words = [x.strip() for x in words]
        return words

    def get_magic_words(self):
        """
        Returns magic words

        :return: stop words
        """
        words_str = self.get_option_value('magic_words')
        words = []
        if words_str is not None and len(words_str) > 0 and words_str.strip() != ' ':
            words = words_str.split(',')
            # remove white-spaces
            words = [x.strip() for x in words]
        return words

    def get_prefix_words(self):
        """
        Returns prefix words

        :return: prefix words
        """
        words_str = self.get_option_value('prefix_words')
        words = []
        if words_str is not None and len(words_str) > 0 and words_str.strip() != ' ':
            words = words_str.split(',')
            # remove white-spaces
            words = [x.strip() for x in words]
        return words

    def toggle_speech(self, state):
        """
        Toggle speech

        :param state: State
        """
        self.speech_enabled = state
        self.window.plugin_addon['audio.input'].btn_toggle.setChecked(state)

        # Start thread if not started
        if state:
            self.listening = True
            self.handle_thread()
        else:
            self.listening = False
            self.set_status('')

    def attach(self, window):
        """
        Attaches window

        :param window: Window
        """
        self.window = window

    def on_user_send(self, text):
        """
        Event: On user send text

        :param text: Text
        :return: text
        """
        return text

    def on_ctx_begin(self, ctx):
        """
        Event: On new context begin

        :param ctx: Context
        :return: ctx
        """
        self.waiting = True
        return ctx

    def on_ctx_end(self, ctx):
        """
        Event: On context end

        :param ctx: Context
        :return: ctx
        """
        self.waiting = False
        return ctx

    def on_system_prompt(self, prompt):
        """
        Event: On prepare system prompt

        :param prompt: Prompt
        :return: prompt
        """
        return prompt

    def on_ai_name(self, name):
        """
        Event: On set AI name

        :param name: Name
        :return: name
        """
        return name

    def on_user_name(self, name):
        """
        Event: On set user name

        :param name: Name
        :return: name
        """
        return name

    def on_enable(self):
        """Event: On plugin enable"""
        self.speech_enabled = True
        self.handle_thread()

    def on_disable(self):
        """Event: On plugin disable"""
        self.speech_enabled = True

    def on_input_before(self, text):
        """
        Event: Before input

        :param text: Text
        :return: text
        """
        self.input_text = text
        return text

    def on_ctx_before(self, ctx):
        """
        Event: Before ctx

        :param ctx: Context
        :return: Context
        """
        return ctx

    def on_ctx_after(self, ctx):
        """
        Event: After ctx

        :param ctx: Context
        :return: Context
        """
        return ctx

    def destroy(self):
        """
        Destroy thread
        """
        self.waiting = True
        self.listening = False
        self.thread_started = False

    def handle_thread(self):
        """
        Handle listener thread
        """
        if self.thread_started:
            return

        listener = AudioInputThread(plugin=self)
        listener.finished.connect(self.handle_input)
        listener.destroyed.connect(self.handle_destroy)
        listener.started.connect(self.handle_started)
        listener.stopped.connect(self.handle_stop)

        self.thread = threading.Thread(target=listener.run)
        self.thread.start()
        self.thread_started = True

    def can_listen(self):
        """
        Check if can listen

        :return: True if can listen
        """
        state = True
        if self.get_option_value('wait_response') and self.window.controller.input.generating:
            state = False
        if self.window.controller.input.locked:
            state = False
        return state

    def set_status(self, status):
        """
        Set status

        :param status: Status
        """
        self.window.plugin_addon['audio.input'].set_status(status)

    @Slot(str)
    def handle_input(self, text):
        """
        Insert text to input and send

        :param text: Text
        """
        if text is None or text.strip() == '':
            return

        # check prefix words
        prefix_words = self.get_prefix_words()
        if len(prefix_words) > 0:
            for word in prefix_words:
                check_text = text.lower().strip()
                check_word = word.lower().strip()
                if not check_text.startswith(check_word):
                    # self.window.data['input'].setText(text)
                    self.window.statusChanged.emit(trans('audio.speak.ignoring'))
                    self.set_status(trans('audio.speak.ignoring'))
                    return

        # previous magic word detected state
        magic_prev_detected = self.magic_word_detected  # save magic word detected state before checking for magic word

        # check for magic word
        is_magic_word = False
        if self.get_option_value('magic_word'):
            for word in self.get_magic_words():
                # prepare magic word
                check_word = word.lower().replace('.', '')
                check_text = text.lower()
                if check_text.startswith(check_word):
                    is_magic_word = True
                    self.set_status(trans('audio.magic_word.detected'))
                    self.window.statusChanged.emit(trans('audio.magic_word.detected'))
                    break

        # if magic word enabled
        if self.get_option_value('magic_word'):
            if not is_magic_word:
                if self.get_option_value('magic_word_reset'):
                    self.magic_word_detected = False
            else:
                self.magic_word_detected = True

            # if not previously detected, then abort now
            if not magic_prev_detected:
                if not is_magic_word:
                    self.window.statusChanged.emit(trans('audio.magic_word.invalid'))
                self.window.data['input'].setText(text)
                return
            else:
                self.window.statusChanged.emit("")

        # update input text
        self.window.data['input'].setText(text)

        # send text
        if self.get_option_value('auto_send'):
            self.set_status('...')
            self.window.statusChanged.emit(trans('audio.speak.sending'))
            self.window.controller.input.send(text)

    @Slot()
    def handle_destroy(self):
        """
        Insert text to input and send
        """
        self.thread_started = False

    @Slot()
    def handle_started(self):
        """
        Handle listening started
        """
        print("Whisper is listening...")

    @Slot()
    def handle_stop(self):
        """
        Stop listening
        """
        self.thread_started = False
        self.listening = False
        self.window.statusChanged.emit("")
        print("Whisper stopped listening...")
        self.toggle_speech(False)


class AudioInputThread(QObject):
    finished = Signal(object)
    destroyed = Signal()
    started = Signal()
    stopped = Signal()

    def __init__(self, plugin=None):
        """
        Audio input listener thread
        """
        super().__init__()
        self.plugin = plugin

    def run(self):
        try:
            client = OpenAI(
                api_key=self.plugin.window.config.get('api_key'),
                organization=self.plugin.window.config.get('organization_key'),
            )
            print("Starting audio listener....")
            path = os.path.join(self.plugin.window.config.path, 'input.wav')

            self.started.emit()
            recognizer = sr.Recognizer()
            with sr.Microphone() as source:
                while self.plugin.listening and not self.plugin.window.is_closing:
                    self.plugin.set_status('')
                    try:
                        # abort if disallowed
                        if not self.plugin.can_listen():
                            time.sleep(0.25)
                            continue

                        # adjust for ambient noise
                        if self.plugin.get_option_value('adjust_noise') and self.plugin.is_first_adjust:
                            time.sleep(1)
                            recognizer.adjust_for_ambient_noise(source, duration=1)
                            self.plugin.is_first_adjust = False

                        timeout = self.plugin.get_option_value('timeout')
                        phrase_length = self.plugin.get_option_value('phrase_length')

                        # check for magic word, if no magic word detected, then set to magic word timeout and length
                        if self.plugin.get_option_value('magic_word'):
                            if not self.plugin.magic_word_detected:
                                timeout = self.plugin.get_option_value('magic_word_timeout')
                                phrase_length = self.plugin.get_option_value('magic_word_phrase_length')

                        # set begin status
                        if self.plugin.get_option_value('magic_word'):
                            if self.plugin.magic_word_detected:
                                self.plugin.set_status(trans('audio.speak.now'))
                            else:
                                self.plugin.set_status(trans('audio.magic_word.please'))
                        else:
                            self.plugin.set_status(trans('audio.speak.now'))

                        audio_data = recognizer.listen(source, timeout, phrase_length)
                        self.plugin.set_status('')

                        # transcript audio
                        if audio_data.get_wav_data():
                            # check RMS / energy
                            rms = audioop.rms(audio_data.get_wav_data(), 2)
                            min_energy = self.plugin.get_option_value('min_energy')
                            if min_energy > 0:
                                self.plugin.window.statusChanged.emit("{}: {} / {}".format(trans('audio.speak.energy'),
                                                                                           rms, min_energy))
                            if min_energy > 0 and rms < min_energy:
                                continue

                            # save audio file
                            with open(path, "wb") as audio_file:
                                audio_file.write(audio_data.get_wav_data())

                            # transcribe
                            with open(path, "rb") as audio_file:
                                self.plugin.set_status(trans('audio.speak.wait'))
                                transcript = client.audio.transcriptions.create(
                                    model=self.plugin.get_option_value('model'),
                                    file=audio_file,
                                    response_format="text"
                                )
                                self.plugin.set_status('')

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

                                    self.finished.emit(transcript)
                                    time.sleep(1)

                                    # stop listening if not continuous mode or stop word detected
                                    stop_words = self.plugin.get_stop_words()
                                    is_stop_word = False
                                    if len(stop_words) > 0:
                                        is_stop_word = transcript.replace('.', '').strip().lower() in stop_words
                                    if not self.plugin.get_option_value('continuous_listen') \
                                            or is_stop_word:
                                        self.plugin.listening = False
                                        self.stopped.emit()
                                        self.plugin.set_status('')  # clear status
                                        break

                    except sr.UnknownValueError:
                        print("Audio error\n")
                    except sr.RequestError as e:
                        print(f"Could not request results; {e}\n")
                    except Exception as e:
                        print(f"An error occurred: {str(e)}\n")

            self.destroyed.emit()

        except Exception as e:
            self.destroyed.emit()
            print(e)
