#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.07 04:00:00                  #
# ================================================== #

from .Version20231227152900 import Version20231227152900  # 2.0.59
from .Version20231230095000 import Version20231230095000  # 2.0.66
from .Version20231231230000 import Version20231231230000  # 2.0.71
from .Version20240106060000 import Version20240106060000  # 2.0.84
from .Version20240107060000 import Version20240107060000  # 2.0.88


class Migrations:
    def __init__(self):
        pass

    @staticmethod
    def get_versions() -> list:
        """
        Return migrations

        :return: list with migrations classes
        """
        return [
            Version20231227152900(),  # 2.0.59
            Version20231230095000(),  # 2.0.66
            Version20231231230000(),  # 2.0.71
            Version20240106060000(),  # 2.0.84
            Version20240107060000(),  # 2.0.88
        ]
