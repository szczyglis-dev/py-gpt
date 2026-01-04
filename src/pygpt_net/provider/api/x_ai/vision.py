#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.04 19:00:00                  #
# ================================================== #

import os
from typing import Optional, Dict, List

from pygpt_net.item.attachment import AttachmentItem
from pygpt_net.item.ctx import CtxItem


class Vision:
    def __init__(self, window=None):
        """
        Vision helpers for xAI (image inputs as data: URIs).

        :param window: Window instance
        """
        self.window = window
        self.attachments: Dict[str, str] = {}
        self.urls: List[str] = []
        self.input_tokens = 0
        self.allowed_mimes = {"image/jpeg", "image/png"}

    def build_images_for_chat(self, attachments: Optional[Dict[str, AttachmentItem]]) -> List[str]:
        """
        Build image inputs for xai_sdk.chat.image(...).
        Returns list of image sources (URLs or data: URIs).

        :param attachments: Attachments dict (id -> AttachmentItem)
        :return: List of image sources
        """
        import base64

        images: List[str] = []
        self.attachments = {}
        self.urls = []

        if not attachments:
            return images

        for id_, att in (attachments or {}).items():
            try:
                if att.path and self.window.core.api.xai.vision.is_image(att.path):
                    mime = self.window.core.api.xai.vision.guess_mime(att.path)
                    with open(att.path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode("utf-8")
                    images.append(f"data:{mime};base64,{b64}")
                    self.attachments[id_] = att.path
                    att.consumed = True
            except Exception:
                continue
        return images

    def is_image(self, path: str) -> bool:
        """
        Return True if path looks like an image file.

        :param path: File path
        """
        return path.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif', '.webp'))

    def guess_mime(self, path: str) -> str:
        """Guess MIME by extension.

        :param path: File path
        :return: MIME type string
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
        Append sent images list to context for UI/history.

        :param ctx: CtxItem
        """
        images = self.get_attachments()
        if len(images) > 0:
            ctx.images = self.window.core.filesystem.make_local_list(list(images.values()))

    def get_attachments(self) -> Dict[str, str]:
        return self.attachments

    def get_urls(self) -> List[str]:
        return self.urls

    def reset_tokens(self):
        self.input_tokens = 0

    def get_used_tokens(self) -> int:
        return self.input_tokens

    def reset(self):
        self.attachments = {}
        self.urls = []
        self.input_tokens = 0