#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.04 00:00:00                  #
# ================================================== #

import os
from typing import Union


class Archives:
    """Files archives for one explorer frontend."""

    def __init__(self, explorer):
        self.explorer = explorer

    def pack(self, path: Union[str, list], fmt: str):
        """
        Pack selected items into an archive.

        :param path: path or list of paths to include
        :param fmt: 'zip' or 'tar.gz'
        """
        explorer = self.explorer
        paths = path if isinstance(path, list) else [path]
        try:
            dst = explorer.window.core.filesystem.packer.pack_paths(paths, fmt)
        except Exception as e:
            try:
                explorer.window.core.debug.log(e)
            except Exception:
                pass
            dst = None

        try:
            explorer.tool.refresh()
        except Exception:
            explorer.update_view()

        if dst and os.path.exists(dst):
            explorer.reveal([dst], select_first=True)

    def unpack(self, path: Union[str, list]):
        """
        Unpack selected archives directly into their parent directories ("Extract Here" behavior).
        - If archive root contains a single directory, that directory is created next to the archive
          (renamed with " (n)" suffix if a directory with the same name exists).
        - If archive root contains files and/or multiple items, they are placed directly next to the archive,
          each using " (n)" suffixes on name collisions, preserving the archive structure.
        """
        explorer = self.explorer
        paths = path if isinstance(path, list) else [path]
        created = []
        for p in paths:
            try:
                if explorer.window.core.filesystem.packer.can_unpack(p):
                    items = explorer.window.core.filesystem.packer.unpack_here(p)
                    if items:
                        created.extend(items)
            except Exception as e:
                try:
                    explorer.window.core.debug.log(e)
                except Exception:
                    pass

        try:
            explorer.tool.refresh()
        except Exception:
            explorer.update_view()

        if created:
            explorer.reveal(created, select_first=True)

