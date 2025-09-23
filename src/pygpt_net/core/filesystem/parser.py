#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.16 02:00:00                  #
# ================================================== #

import os
import re

from pygpt_net.item.ctx import CtxItem


class Parser:
    def __init__(self, window=None):
        """
        Filesystem parser

        :param window: Window instance
        """
        self.window = window

    def extract_data_paths(self, text: str) -> list:
        """
        Extract file paths from text that contain 'data' segment (case-insensitive).
        Supports quoted and unquoted paths, POSIX/Windows, and ignores URLs.
        """
        if not text:
            return []

        def is_data_path(p: str) -> bool:
            # 'data' (case-insensitive)
            return re.search(r"(?i)(?:^|[\\/])data(?:[\\/]|$)", p) is not None

        def is_url(p: str) -> bool:
            return re.match(r"^[a-z][a-z0-9+.-]*://", p, re.I) is not None

        results = []

        quoted_pat = re.compile(r"(?P<q>['\"])(?P<p>(?:[A-Za-z]:)?[\\/](?:(?!\1).)+?)\1")
        for m in quoted_pat.finditer(text):
            p = m.group("p").strip()
            if not is_url(p) and is_data_path(p):
                results.append(p)

        unquoted_pat = re.compile(r"(?P<p>(?:[A-Za-z]:)?(?:[\\/][^\s'\"),;]+)+)")
        for m in unquoted_pat.finditer(text):
            p = m.group("p").strip()
            if not is_url(p) and is_data_path(p):
                results.append(p)

        seen = set()
        out = []
        for p in results:
            if p not in seen:
                seen.add(p)
                out.append(p)
        return out

    def extract_data_files(self, ctx: "CtxItem", response: str) -> list:
        """
        Extract files from tool outputs and return list of file paths.
        """
        if response is None:
            return []
        images_list = []
        local_data_dir = self.window.core.config.get_user_dir('data')
        raw_paths = self.extract_data_paths(response)

        def replace_with_local(path):
            """
            Replace the path with local data directory path.
            """
            segments = re.split(r"[\\/]+", path)
            # case-insensitive find of 'data'
            data_index = next((i for i, s in enumerate(segments) if s.lower() == "data"), None)
            if data_index is None:
                return path
            tail = segments[data_index + 1:]
            new_path = os.path.join(local_data_dir, *tail) if tail else local_data_dir
            return new_path

        processed_paths = []
        for file in raw_paths:
            new_file = replace_with_local(file)
            if new_file not in processed_paths:
                processed_paths.append(new_file)

        for path in processed_paths:
            ext = os.path.splitext(path)[1].lower().lstrip(".")
            if ext in ["png", "jpg", "jpeg", "gif", "bmp", "tiff", "webp"]:
                if path not in images_list:
                    images_list.append(path)

        local_images = self.window.core.filesystem.make_local_list(images_list)
        ctx.files = processed_paths
        ctx.images = local_images
        return processed_paths
