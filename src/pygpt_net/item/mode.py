#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.05 19:35:00                  #
# ================================================== #

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class ModeItem:
    id: Optional[object] = None
    name: str = ""
    label: str = ""
    default: bool = False
    legacy: bool = False
