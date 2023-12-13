#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.13 19:00:00                  #
# ================================================== #
import os
import threading

from PySide6.QtCore import QObject, Signal, Qt, Slot
from PySide6.QtWidgets import QCheckBox
import speech_recognition as sr
from openai import OpenAI

from ..base_plugin import BasePlugin
from ...utils import trans


class Plugin(BasePlugin):
    def __init__(self):
        super(Plugin, self).__init__()
        self.id = "audio_openai_whisper"
        self.name = "Audio Input (OpenAI Whisper)"
        self.description = "Enables speech recognition using OpenAI Whisper API"
        self.stop_words = ['stop', 'exit', 'quit', 'end', 'finish', 'close', 'terminate', 'kill', 'halt', 'abort']
        self.input_text = None
        self.window = None
        self.speech_enabled = False
        self.thread_started = False
        self.thread = None
        self.listening = False
        self.waiting = False
        self.order = 1
        self.init_options()

    def init_options(self):
        """
        Initializes options
        """
        self.add_option("model", "text", "whisper-1",
                        "Model",
                        "Specify model, default: whisper-1")
        self.add_option("timeout", "int", 2,
                        "Timeout",
                        "Speech recognition timeout", min=1, max=30, slider=True, tooltip="Timeout, default: 2")
        self.add_option("phrase_length", "int", 3,
                        "Phrase max length",
                        "Speech recognition phrase length", min=1, max=30, slider=True, tooltip="Phrase max length, "
                                                                                                "default: 3")
        self.add_option("min_energy", "int", 4000,
                        "Min. energy",
                        "Minimum energy (loudness) to start recording, 0 = disabled", min=0, max=20000, slider=True,
                        tooltip="Min. energy, default: 4000, 0 = disabled, adjust for your microphone")
        self.add_option("adjust_noise", "bool", True,
                        "Adjust ambient noise",
                        "Adjust for ambient noise")
        self.add_option("continuous_listen", "bool", True,
                        "Continuous listening",
                        "Continuous listening (do not stop after single input)")

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
        self.window.plugin_data['speech.enable'] = QCheckBox(trans('speech.enable'))
        self.window.plugin_data['speech.enable'].setStyleSheet(
            self.window.controller.theme.get_style('checkbox'))  # Windows fix
        self.window.plugin_data['speech.enable'].stateChanged.connect(
            lambda: self.toggle_speech(self.window.plugin_data['speech.enable'].isChecked()))
        self.window.data['ui.input.buttons'].addWidget(self.window.plugin_data['speech.enable'], 0, Qt.AlignLeft)
        if self.enabled:
            self.window.plugin_data['speech.enable'].setVisible(True)
        else:
            self.window.plugin_data['speech.enable'].setVisible(False)

    def toggle_speech(self, state):
        """
        Toggle speech

        :param state: State
        """
        self.speech_enabled = state
        self.window.plugin_data['speech.enable'].setChecked(state)

        # Start thread if not started
        if state:
            self.listening = True
            self.handle_thread()
        else:
            self.listening = False

    def attach(self, window):
        """
        Attaches window

        :param window: Window
        """
        self.window = window

    def on_user_send(self, text):
        """Event: On user send text"""
        return text

    def on_ctx_begin(self, ctx):
        """Event: On new context begin"""
        self.waiting = True
        self.window.statusChanged.emit("")
        return ctx

    def on_ctx_end(self, ctx):
        """Event: On context end"""
        if self.listening:
            self.window.statusChanged.emit(trans('speech.listening'))
        self.waiting = False
        return ctx

    def on_system_prompt(self, prompt):
        """Event: On prepare system prompt"""
        return prompt

    def on_ai_name(self, name):
        """Event: On set AI name"""
        return name

    def on_user_name(self, name):
        """Event: On set user name"""
        return name

    def on_enable(self):
        """Event: On plugin enable"""
        self.window.plugin_data['speech.enable'].setVisible(True)
        self.speech_enabled = True
        self.handle_thread()

    def on_disable(self):
        """Event: On plugin disable"""
        self.window.plugin_data['speech.enable'].setVisible(False)
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

        :param ctx: Text
        :return: ctx
        """
        return ctx

    def on_ctx_after(self, ctx):
        """
        Event: After ctx

        :param ctx: ctx
        :return: ctx
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

    @Slot(str)
    def handle_input(self, text):
        """
        Insert text to input and send

        :param text: Text
        """
        if text is None or text.strip() == '':
            return

        self.window.data['input'].setText(text)
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
        self.window.statusChanged.emit(trans('speech.listening'))

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
            client = OpenAI()
            print("Starting audio listener....")
            path = os.path.join(self.plugin.window.config.path, 'input.wav')
            while self.plugin.listening:
                recognizer = sr.Recognizer()
                self.started.emit()
                try:
                    with sr.Microphone() as source:
                        if self.plugin.options["adjust_noise"]['value']:
                            recognizer.adjust_for_ambient_noise(source)
                        timeout = self.plugin.options["timeout"]['value']
                        phrase_length = self.plugin.options["phrase_length"]['value']
                        audio_data = recognizer.listen(source, timeout, phrase_length)

                        # check if audio data is not too silent
                        if audio_data.get_wav_data():
                            energy = recognizer.energy_threshold
                            if self.plugin.options["min_energy"]['value'] > 0 \
                                    and energy < self.plugin.options["min_energy"]['value']:
                                continue
                    try:
                        if not self.plugin.waiting and audio_data.get_wav_data():
                            with open(path, "wb") as file:
                                file.write(audio_data.get_wav_data())
                                file.close()

                            # transcribe audio file
                            if os.path.exists(path):
                                audio_file = open(path, "rb")
                                transcript = client.audio.transcriptions.create(
                                    model=self.plugin.options["model"]['value'],
                                    file=audio_file,
                                    response_format="text"
                                )
                                audio_file.close()

                                # remove file
                                os.remove(path)
                                if transcript is not None and transcript.strip() != '':
                                    self.finished.emit(transcript)

                                    # stop listening if not continuous
                                    if not self.plugin.options["continuous_listen"]['value'] \
                                            or transcript.replace('.', '').strip().lower() in self.plugin.stop_words:
                                        self.plugin.listening = False
                                        self.stopped.emit()
                                        break

                    except sr.UnknownValueError:
                        pass
                    except sr.RequestError as e:
                        print(f"Could not request results; {e}\n")
                    except Exception as e:
                        print(f"An error occurred: {str(e)}\n")
                except Exception as e:
                    print(f"An error occurred: {str(e)}\n")
            self.destroyed.emit()
        except Exception as e:
            self.destroyed.emit()
            print(e)
