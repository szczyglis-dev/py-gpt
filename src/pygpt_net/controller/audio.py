#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.19 06:00:00                  #
# ================================================== #

import os

from PySide6.QtWidgets import QFileDialog

from pygpt_net.core.dispatcher import Event
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class Audio:
    def __init__(self, window=None):
        """
        Audio/voice controller

        :param window: Window instance
        """
        self.window = window
        self.is_transcribe = False

    def setup(self):
        """Setup controller"""
        self.update()
        self.restore_transcription()
        self.restore_auto_convert_video()

    def toggle_input(self, state: bool, btn: bool = True):
        """
        Toggle audio input

        :param state: True to enable, False to disable
        :param btn: True if called from button
        """
        self.window.core.dispatcher.dispatch(
            Event(Event.AUDIO_INPUT_TOGGLE, {
                "value": state,
            })
        )

    def toggle_output(self):
        """Toggle audio output"""
        if self.window.controller.plugins.is_enabled('audio_output'):
            self.disable_output()
        else:
            self.enable_output()

    def enable_output(self):
        """Enable audio output"""
        self.toggle_output_icon(True)
        self.window.controller.plugins.enable('audio_output')
        self.window.core.config.save()
        self.update()

    def disable_output(self):
        """Disable audio output"""
        self.toggle_output_icon(False)
        self.window.controller.plugins.disable('audio_output')
        self.window.core.config.save()
        self.update()

    def disable_input(self, update: bool = True):
        """
        Disable audio input

        :param update: True to update menu and listeners
        """
        self.window.controller.plugins.disable('audio_input')
        self.window.core.config.save()
        if update:
            self.update()

    def stop_input(self):
        """Stop audio input"""
        self.window.core.dispatcher.dispatch(
            Event(Event.AUDIO_INPUT_STOP, {
                "value": True,
            }), all=True)

    def stop_output(self):
        """Stop audio output"""
        self.window.core.dispatcher.dispatch(
            Event(Event.AUDIO_OUTPUT_STOP, {
                "value": True,
            }), all=True)

    def update(self):
        """Update UI and listeners"""
        self.update_listeners()
        self.update_menu()

    def is_output_enabled(self) -> bool:
        """
        Check if any audio output is enabled

        :return: True if enabled
        """
        if self.window.controller.plugins.is_enabled('audio_output'):
            return True
        return False

    def update_listeners(self):
        """Update audio listeners"""
        is_output = False
        if self.window.controller.plugins.is_enabled('audio_output'):
            is_output = True
        if not is_output:
            self.stop_output()

        if not self.window.controller.plugins.is_enabled('audio_input'):
            self.toggle_input(False)
            self.stop_input()
            if self.window.ui.plugin_addon['audio.input'].btn_toggle.isChecked():
                self.window.ui.plugin_addon['audio.input'].btn_toggle.setChecked(False)

    def update_menu(self):
        """Update audio menu"""
        if self.window.controller.plugins.is_enabled('audio_output'):
            self.window.ui.menu['audio.output'].setChecked(True)
        else:
            self.window.ui.menu['audio.output'].setChecked(False)

        if self.window.controller.plugins.is_enabled('audio_input'):
            self.window.ui.menu['audio.input'].setChecked(True)
        else:
            self.window.ui.menu['audio.input'].setChecked(False)

    def read_text(self, text: str):
        """
        Read text using audio output plugins

        :param text: text to read
        """
        ctx = CtxItem()
        ctx.output = text
        all = True  # to all plugins (even if disabled)
        event = Event(Event.AUDIO_READ_TEXT)
        event.ctx = ctx
        self.window.core.dispatcher.dispatch(event, all=all)

    def toggle_output_icon(self, state: bool):
        """
        Toggle input icon

        :param state: True to enable, False to disable
        """
        if state:
            self.window.ui.nodes['icon.audio.output'].set_icon(":/icons/volume.svg")
        else:
            self.window.ui.nodes['icon.audio.output'].set_icon(":/icons/mute.svg")

    def toggle_input_icon(self, state: bool):
        """
        Toggle input icon

        :param state: True to enable, False to disable
        """
        if state:
            self.window.ui.nodes['icon.audio.input'].set_icon(":/icons/mic.svg")
        else:
            self.window.ui.nodes['icon.audio.input'].set_icon(":/icons/mic_off.svg")

    def on_begin(self, text: str):
        """
        On audio playback init

        :param text: text to play
        """
        self.window.ui.status(trans("status.audio.start"))

    def on_play(self, event: str):
        """
        On audio playback start

        :param event: event name
        """
        if event == Event.AUDIO_READ_TEXT:
            self.window.ui.status("")

    def on_stop(self):
        """
        On audio playback stopped (force)
        """
        self.window.ui.status(trans("status.audio.stopped"))

    def is_playing(self) -> bool:
        """
        Check if any audio is playing

        :return: True if playing
        """
        from pygame import mixer
        try:
            mixer.init()
            return mixer.get_busy()
        except Exception as e:
            pass
        return False

    def open_transcribe_file(self):
        """Open transcribe file dialog"""
        path, _ = QFileDialog.getOpenFileName(
            self.window,
            trans("action.video.open"),
            "",
            "Audio Files (*.mp3 *.wav *.ogg *.flac *.m4a *.mp4 *.avi *.mov *.mkv *.webm)")
        if path:
            self.transcribe(path)

    def transcribe(self, path: str, force: bool = False):
        """
        Transcribe audio file

        :param path: audio file path
        :param force: force transcribe
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='audio.transcribe',
                id=path,
                msg=trans("audio.transcribe.confirm"),
            )
            return
        path = self.prepare_audio(path)
        if path is not None:
            event = Event(Event.AUDIO_INPUT_TRANSCRIBE, {
                'path': str(path),
            })
            event.ctx = CtxItem()  # tmp
            self.transcribe_clear(force=True)
            self.window.controller.command.dispatch_only(event)
            self.window.ui.nodes['audio.transcribe.status'].setText(
                "Transcribing: {} ... Please wait...".format(os.path.basename(path)))

    def prepare_audio(self, path: str) -> str:
        """
        Convert video to audio if needed

        :param path: video file path
        """
        # ffmpeg required here
        if self.is_video(path) and self.is_auto_convert_video():
            try:
                self.window.ui.nodes['audio.transcribe.status'].setText(
                    "Converting to audio: {} ... Please wait...".format(os.path.basename(path)))
                video_type = path.split(".")[-1].lower()
                try:
                    from pydub import AudioSegment
                except ImportError:
                    self.window.ui.nodes['audio.transcribe.status'].setText("Please install pydub 'pip install pydub'")
                    raise ImportError("Please install pydub 'pip install pydub' ")
                video = AudioSegment.from_file(path, format=video_type)
                # extract audio from video
                audio = video.split_to_mono()[0]
                file_str = os.path.join(self.window.core.config.get_user_path(), "transcript.mp3")
                if os.path.exists(file_str):
                    os.remove(file_str)
                audio.export(file_str, format="mp3")
                self.window.ui.nodes['audio.transcribe.status'].setText("Converted: {}".format(os.path.basename(file_str)))
                path = file_str
            except Exception as e:
                self.window.core.debug.log(e)
                self.window.ui.nodes['audio.transcribe.status'].setText(
                    "Aborted. Can't convert video to mp3! FFMPEG not installed?\n"
                    "Please install \"ffmpeg\" or disable the option \"Always convert video to mp3\" to transcribe from video file.")
                self.window.ui.dialogs.alert(e)
                path = None
        return path

    def toggle_auto_convert_video(self):
        """
        Toggle video conversion

        :param state: True to enable, False to disable
        """
        state = self.window.ui.nodes['audio.transcribe.convert_video'].isChecked()
        self.window.core.config.set('audio.transcribe.convert_video', state)
        self.window.core.config.save()

    def restore_auto_convert_video(self):
        """Restore auto video conversion"""
        if self.window.core.config.has('audio.transcribe.convert_video'):
            state = self.window.core.config.get('audio.transcribe.convert_video', True)
            self.window.ui.nodes['audio.transcribe.convert_video'].setChecked(state)

    def is_auto_convert_video(self) -> bool:
        """
        Check if auto video conversion is enabled

        :return: True if enabled
        """
        return self.window.ui.nodes['audio.transcribe.convert_video'].isChecked()

    def store_transcription(self, text: str):
        """
        Store transcription to file

        :param text: transcribed text
        """
        path = os.path.join(self.window.core.config.get_user_path(), "transcript.txt")
        with open(path, "w") as f:
            f.write(text)

    def restore_transcription(self):
        """Restore transcription from file"""
        path = os.path.join(self.window.core.config.get_user_path(), "transcript.txt")
        if os.path.exists(path):
            with open(path, "r") as f:
                data = f.read()
                self.window.ui.editor["audio.transcribe"].setPlainText(data)

    def is_video(self, file: str) -> bool:
        """
        Check if file is a video.

        :param file: file path
        :return: True if file is a video
        """
        ext = file.split(".")[-1].lower()
        return ext in ["mp4", "avi", "mov", "mkv", "webm"]

    def on_transcribe(self, path: str, text: str):
        """
        On audio transcribed

        :param path: audio file path
        :param text: transcribed text
        """
        self.store_transcription(text)
        self.window.ui.nodes['audio.transcribe.status'].setText(
            trans("audio.transcribe.result.finished").format(path=os.path.basename(path)))
        self.window.ui.editor["audio.transcribe"].setPlainText(text)

    def open_and_transcribe(self, path: str):
        """
        Open and transcribe audio file

        :param path: audio file path
        """
        self.open_transcribe()
        self.window.ui.nodes['audio.transcribe.status'].setText(
            trans("audio.transcribe.result.selected").format(path=os.path.basename(path)))
        self.transcribe(path)

    def open_transcribe(self):
        """Open transcriber"""
        self.window.ui.nodes['audio.transcribe.status'].setText("")
        self.window.ui.dialogs.open('audio.transcribe', width=800, height=600)
        self.is_transcribe = True
        self.update()

    def close_transcribe(self):
        """Close transcribe"""
        self.window.ui.dialogs.close('audio.transcribe')
        self.is_transcribe = False

    def show_hide_transcribe(self, show: bool = True):
        """
        Show/hide transcribe window

        :param show: show/hide
        """
        if show:
            self.open_transcribe()
        else:
            self.close_transcribe()

    def on_close_transcribe(self):
        """On transcribe window close"""
        self.is_transcribe = False
        self.update_transcribe()

    def transcribe_clear(self, force: bool = False):
        """
        Clear transcribe data

        :param force: force clear
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='audio.transcribe.clear',
                id=0,
                msg=trans("audio.transcribe.clear.confirm"),
            )
            return
        id = 'audio.transcribe'
        self.window.ui.editor[id].clear()
        self.window.ui.nodes['audio.transcribe.status'].setText("")
        self.store_transcription("")

    def update_transcribe(self):
        """Update transcribe data"""
        if self.is_transcribe:
            self.window.ui.menu['audio.transcribe'].setChecked(True)
        else:
            self.window.ui.menu['audio.transcribe'].setChecked(False)
