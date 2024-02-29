#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.29 02:00:00                  #
# ================================================== #

from llama_index.core.readers.base import BaseReader
from llama_index.readers.file.video_audio import VideoAudioReader

from .base import BaseLoader


class Loader(BaseLoader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = "mp4"
        self.name = "Video/audio .mp4 files"
        self.extensions = ["mp4"]
        self.type = ["file"]
        self.init_args = {
            "model_version": "base",
        }

    def get(self) -> BaseReader:
        """
        Get reader instance

        :return: Data reader instance
        """
        args = self.get_args()
        return VideoAudioReader(**args)
