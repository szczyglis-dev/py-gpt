#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.05 16:00:00                  #
# ================================================== #
"""Lightweight reference decoding shared by stored turns and mention rendering."""


def attachment_reference(value: str) -> tuple[str, str]:
    """Decode a project-library reference into stable source ID and filename."""
    value = str(value or "")
    if value.startswith("project-attachment:"):
        parts = value.split(":", 2)
        if len(parts) == 3 and parts[1] and parts[2]:
            return parts[1], parts[2]
    return "", value
