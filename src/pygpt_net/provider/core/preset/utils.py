#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.27 10:00:00                  #
# ================================================== #

import os
import shutil
from typing import Optional


def safe_copy_preset(window, filename: str, dst: Optional[str] = None) -> bool:
    """
    Safely copy a bundled preset to the user's presets directory.

    Source path is resolved automatically from:
    ``<app_path>/data/config/presets/<filename>``.

    If ``dst`` is omitted, the preset is copied to:
    ``<user_presets_dir>/<filename>``. A relative ``dst`` is resolved against
    the user's presets directory; an absolute ``dst`` is used as-is.

    :param window: main application window
    :param filename: bundled preset filename
    :param dst: optional destination path or filename
    :return: True if copied successfully
    """
    src = filename
    target = dst or filename

    try:
        presets_dir = window.core.config.get_user_dir("presets")
        src = os.path.join(
            window.core.config.get_app_path(),
            "data",
            "config",
            "presets",
            filename,
        )

        if not dst:
            target = os.path.join(presets_dir, filename)
        elif not os.path.isabs(dst):
            target = os.path.join(presets_dir, dst)
        else:
            target = dst

        parent = os.path.dirname(target)
        if parent:
            os.makedirs(parent, exist_ok=True)

        shutil.copyfile(src, target)
        print("Patched file: {}.".format(target))
        return True
    except Exception as e:
        try:
            window.core.debug.log(e)
        except Exception:
            pass
        print("Failed to patch preset file: {} -> {}: {}".format(src, target, e))
        return False
