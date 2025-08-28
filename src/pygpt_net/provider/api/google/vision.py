#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.28 20:00:00                  #
# ================================================== #

import os
from typing import Optional, Dict, List, Union

from google.genai.types import Part

from pygpt_net.item.attachment import AttachmentItem
from pygpt_net.item.ctx import CtxItem


class Vision:
    def __init__(self, window=None):
        """
        Vision helpers for Google GenAI

        :param window: Window instance
        """
        self.window = window
        self.attachments: Dict[str, str] = {}
        self.urls: List[str] = []
        self.input_tokens = 0

    def build_parts(
        self,
        content: Union[str, list],
        attachments: Optional[Dict[str, AttachmentItem]] = None,
    ) -> List[Part]:
        """
        Build image parts from local attachments (inline bytes)

        :param content: Message content (str or list)
        :param attachments: Attachments dict (id -> AttachmentItem)
        :return: List of Parts
        """
        parts: List[Part] = []
        self.attachments = {}
        self.urls = []

        if attachments:
            for id_, attachment in attachments.items():
                if attachment.path and os.path.exists(attachment.path):
                    if self.is_image(attachment.path):
                        mime = self._guess_mime(attachment.path)
                        with open(attachment.path, "rb") as f:
                            data = f.read()
                        parts.append(Part.from_bytes(data=data, mime_type=mime))
                        self.attachments[id_] = attachment.path
                        attachment.consumed = True

        return parts

    def is_image(self, path: str) -> bool:
        """
        Check if path looks like an image

        :param path: File path
        :return: True if image, False otherwise
        """
        return path.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif', '.webp'))

    def _guess_mime(self, path: str) -> str:
        """
        Guess mime type from file extension

        :param path: File path
        :return: Mime type string
        """
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        if ext in ("jpg", "jpeg"):
            return "image/jpeg"
        if ext == "png":
            return "image/png"
        if ext == "gif":
            return "image/gif"
        if ext == "bmp":
            return "image/bmp"
        if ext == "webp":
            return "image/webp"
        if ext == "tiff":
            return "image/tiff"
        return "image/jpeg"

    def append_images(self, ctx: CtxItem):
        """
        Append sent images paths to context for UI/history

        :param ctx: CtxItem
        """
        images = self.get_attachments()
        if len(images) > 0:
            ctx.images = self.window.core.filesystem.make_local_list(list(images.values()))

    def get_attachments(self) -> Dict[str, str]:
        """
        Return attachments dict (id -> path)

        :return: Dict of attachments
        """
        return self.attachments

    def get_urls(self) -> List[str]:
        """
        Return image urls (unused here)

        :return: List of URLs
        """
        return self.urls

    def reset_tokens(self):
        """Reset input tokens counter"""
        self.input_tokens = 0

    def get_used_tokens(self) -> int:
        """
        Return input tokens counter

        :return: Number of input tokens
        """
        return self.input_tokens