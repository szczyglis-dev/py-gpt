#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.20 12:45:00
# ================================================== #

from enum import Enum


class SandboxMode(str, Enum):
    DISABLED = "disabled"
    BUILTIN = "builtin"
    DOCKER = "docker"

    @classmethod
    def options(cls) -> list[dict[str, str]]:
        return [
            {cls.DISABLED.value: "sandbox.mode.disabled"},
            {cls.BUILTIN.value: "sandbox.mode.builtin"},
            {cls.DOCKER.value: "sandbox.mode.docker"},
        ]
