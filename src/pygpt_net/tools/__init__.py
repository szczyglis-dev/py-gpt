# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.20 06:00:00                  #
# ================================================== #

from pygpt_net.tools.audio_transcriber import AudioTranscriber
from pygpt_net.tools.code_interpreter import CodeInterpreter
from pygpt_net.tools.media_player import MediaPlayer
from pygpt_net.tools.text_editor import TextEditor

class Tools:
    def __init__(self, window=None):
        """
        Tools manager

        :param window: Window instance
        """
        self.window = window
        self.transcriber = AudioTranscriber(window)
        self.interpreter = CodeInterpreter(window)
        self.player = MediaPlayer(window)
        self.editor = TextEditor(window)

    def setup(self):
        """Setup tools"""
        self.transcriber.setup()
        self.interpreter.setup()
        self.player.setup()
        self.editor.setup()

    def post_setup(self):
        """Post-setup, after plugins are loaded"""
        pass

    def after_setup(self):
        """After-setup, after all loaded"""
        pass

    def on_update(self):
        """On app main loop update"""
        pass

    def on_exit(self):
        """On app exit"""
        self.transcriber.on_exit()
        self.interpreter.on_exit()
        self.player.on_exit()
        self.editor.on_exit()

    def init(self):
        """Init base settings"""
        pass
