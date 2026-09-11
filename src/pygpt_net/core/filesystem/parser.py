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

    def extract_local_paths(self, text: str) -> list:
        """Extract quoted/unquoted absolute-looking local paths from text."""
        if not text:
            return []

        def is_url(p: str) -> bool:
            return re.match(r"^[a-z][a-z0-9+.-]*://", p, re.I) is not None

        results = []
        quoted_pat = re.compile(r"(?P<q>['\"])(?P<p>(?:[A-Za-z]:)?[\\/](?:(?!\1).)+?)\1")
        for m in quoted_pat.finditer(text):
            p = m.group("p").strip()
            if not is_url(p):
                results.append(p)

        unquoted_pat = re.compile(r"(?P<p>(?:[A-Za-z]:)?(?:[\\/][^\s'\"),;]+)+)")
        for m in unquoted_pat.finditer(text):
            p = m.group("p").strip()
            if not is_url(p):
                results.append(p)

        seen = set()
        out = []
        for p in results:
            if p not in seen:
                seen.add(p)
                out.append(p)
        return out

    def extract_data_paths(self, text: str) -> list:
        """
        Extract file paths from text that contain 'data' segment (case-insensitive).
        Supports quoted and unquoted paths, POSIX/Windows, and ignores URLs.
        """
        return [
            p for p in self.extract_local_paths(text)
            if re.search(r"(?i)(?:^|[\\/])data(?:[\\/]|$)", p) is not None
        ]

    def extract_data_files(self, ctx: "CtxItem", response: str) -> list:
        """
        Extract files from tool outputs and return list of file paths.
        """
        if response is None:
            return []
        images_list = []
        filesystem = self.window.core.filesystem
        local_data_dir = filesystem.get_data_dir(ctx=ctx)
        shared_data_dir = filesystem.get_shared_data_dir()

        # Parse concrete paths first instead of replacing the active project
        # root in the whole response string. A broad project root may contain
        # the base PyGPT profile; blind replacement would then turn e.g.
        # <base>/tmp/plot.png into /data/... and incorrectly classify tmp as
        # project data.
        raw_paths = self.extract_local_paths(str(response))

        def replace_with_local(path):
            """Resolve sandbox/legacy data paths without remapping globals."""
            normalized = str(path).replace("\\", "/")

            # An absolute host path already inside the active project data root
            # is authoritative, unless it belongs to a protected base-profile
            # branch such as tmp/img/capture/upload.
            if os.path.isabs(path) and filesystem._is_path_in(path, local_data_dir):
                if not filesystem.is_global_profile_path(path, ctx=ctx):
                    return os.path.normpath(path)

            # Explicit base/shared data must remain base data while a project
            # override is active; do not reinterpret it as project /data.
            if os.path.isabs(path) and filesystem._is_path_in(path, shared_data_dir):
                if os.path.normcase(os.path.abspath(local_data_dir)) != os.path.normcase(os.path.abspath(shared_data_dir)):
                    return None

            segments = re.split(r"[\\/]+", normalized)
            data_index = next((i for i, s in enumerate(segments) if s.lower() == "data"), None)
            if data_index is None:
                return None
            tail = segments[data_index + 1:]
            return os.path.join(local_data_dir, *tail) if tail else local_data_dir

        processed_paths = []
        for file in raw_paths:
            new_file = replace_with_local(file)
            if new_file is not None and new_file not in processed_paths:
                processed_paths.append(new_file)

        for path in processed_paths:
            ext = os.path.splitext(path)[1].lower().lstrip(".")
            if ext in ["png", "jpg", "jpeg", "gif", "bmp", "tiff", "webp"]:
                if path not in images_list:
                    images_list.append(path)

        local_images = self.window.core.filesystem.make_local_list(images_list, ctx=ctx)
        ctx.files = processed_paths
        ctx.images = local_images
        return processed_paths
