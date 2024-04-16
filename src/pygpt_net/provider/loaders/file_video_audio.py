#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.17 01:00:00                  #
# ================================================== #

from llama_index.core.readers.base import BaseReader

from .hub.video_audio.base import VideoAudioReader
from .base import BaseLoader


class Loader(BaseLoader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = "video_audio"
        self.name = "Video/audio"
        self.extensions = ["mp4", "avi", "mov", "mkv", "webm", "mp3", "mpeg", "mpga", "m4a", "wav"]
        self.type = ["file"]
        self.init_args = {
            "use_local": False,  # use local model instead of API
            "model_version": "base", # Whisper model version
        }
        self.init_args_types = {
            "use_local": "bool",
            "model_version": "str",
        }
        """
        https://github.com/openai/whisper
        Allowed models:
        - tiny (39 M)
        - base (74 M)
        - small (244 M)
        - medium (769 M)
        - large (1550 M)
        - large-v2 (1550 M)
        """

    def get(self) -> BaseReader:
        """
        Get reader instance

        :return: Data reader instance
        """
        args = self.get_args()
        args["window"] = self.window  # pass window instance
        if self.window is not None:
            args["use_local"] = self.window.core.config.get("llama.hub.loaders.use_local", False)
        return VideoAudioReader(**args)
