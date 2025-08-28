#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 18:00:00                  #
# ================================================== #

import base64
from typing import Optional, Union, List, Dict, Any

from pygpt_net.core.bridge.context import MultimodalContext


class Audio:
    def __init__(self, window=None):
        """
        Audio input wrapper

        :param window: Window instance
        """
        self.window = window

    def build_content(
            self,
            content: Optional[Union[str, list]] = None,
            multimodal_ctx: Optional[MultimodalContext] = None,
    ) -> List[Dict[str, Any]]:
        """
        Build audio content from multimodal context

        :param content: previous content or input prompt
        :param multimodal_ctx: multimodal context
        :return: List of contents
        """
        if not isinstance(content, list):
            if content:
                content = [
                    {
                        "type": "text",
                        "text": str(content),
                    }
                ]
            else:
                content = []  # if empty input return empty list

        # abort if no audio input provided
        if not multimodal_ctx.is_audio_input:
            return content

        encoded = base64.b64encode(multimodal_ctx.audio_data).decode('utf-8')
        audio_format = multimodal_ctx.audio_format  # wav by default
        audio_data = {
            "type": "input_audio",
            "input_audio": {
                "data": encoded,
                "format": audio_format,
            }
        }
        content.append(audio_data)
        return content
