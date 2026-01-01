#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.01 15:00:00                  #
# ================================================== #
from typing import Optional

from pygpt_net.core.types import (
    MODEL_DEFAULT,
    MODEL_DEFAULT_MINI
)


def apply(text: Optional[str]) -> str:
    """
    Apply placeholders to the given text.

    :param text: input text with placeholders
    :return: text with applied placeholders
    """
    if text is None:
        return ""
    placeholders = {
        "%MODEL_DEFAULT_MINI%": MODEL_DEFAULT_MINI,
        "%MODEL_DEFAULT%": MODEL_DEFAULT,
    }
    for placeholder, value in placeholders.items():
        if placeholder in text:
            text = text.replace(placeholder, value)
    return text