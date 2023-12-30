#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.30 09:00:00                  #
# ================================================== #

from .Version20231227152900 import Version20231227152900  # 2.0.59
from .Version20231230095000 import Version20231230095000  # 2.0.66


class Migrations:
    def __init__(self):
        pass

    @staticmethod
    def get_versions():
        """
        Return migrations

        :return: list with migrations classes
        :rtype: list
        """
        return [
            Version20231227152900(),  # 2.0.59
            Version20231230095000(),  # 2.0.66
        ]