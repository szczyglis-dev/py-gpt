#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.06 01:00:00                  #
# ================================================== #

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llama_index.core.readers.base import BaseReader

from ..base import BaseLoader


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
                            "label": 'options.url.label',
                            "description": 'options.url.desc',
                        },
                    },
                }
            }
        ]
        self.init_args = {
            "languages": ["en"],
        }
        self.init_args_types = {
            "languages": {'type': 'list', 'extra': {}},
        }
        self.init_args_labels = {
            "languages": "config.languages.label",
        }
        self.init_args_desc = {
            "languages": "config.languages.desc",
        }

        self.configure_locale(__file__, required_config=[],
                              required_options=['url'])

    def get(self) -> BaseReader:
        """
        Get reader instance

        :return: Data reader instance
        """
        from ..hub.yt.base import YoutubeTranscriptReader
        args = self.get_args()
        return YoutubeTranscriptReader(**args)

    def prepare_args(self, **kwargs) -> dict:
        """
        Prepare arguments for reader

        :param kwargs: keyword arguments
        :return: args to pass to reader
        """
        args = {}
        args["ytlinks"] = [kwargs.get("url")]  # list of links
        return args

    def is_supported_attachment(self, source: str) -> bool:
        """
        Check if attachment is supported by loader

        :param source: attachment source
        :return: True if supported
        """
        yt_prefix = [
            "https://youtube.com",
            "https://youtu.be",
            "https://www.youtube.com",
            "https://m.youtube.com",
        ]
        for prefix in yt_prefix:
            if source.startswith(prefix):
                return True
        return False
