#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.12 06:00:00                  #
# ================================================== #

from llama_index.core.readers.base import BaseReader

from .hub.yt.base import YoutubeTranscriptReader
from .base import BaseLoader


class Loader(BaseLoader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = "youtube"
        self.name = "YouTube"
        self.type = ["web"]
        self.instructions = [
            {
                "youtube": {
                    "description": "read and index YouTube video URL",
                    "args": {
                        "url": {
                            "type": "str",
                        },
                    },
                }
            }
        ]

    def get(self) -> BaseReader:
        """
        Get reader instance

        :return: Data reader instance
        """
        return YoutubeTranscriptReader()

    def prepare_args(self, **kwargs) -> dict:
        """
        Prepare arguments for reader

        :param kwargs: keyword arguments
        :return: args to pass to reader
        """
        args = {}
        args["ytlinks"] = [kwargs.get("url")]  # list of links
        return args
