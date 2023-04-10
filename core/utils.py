#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Created Date: 2023.04.09 20:00:00                  #
# ================================================== #

import os
import re
from core.locale import Locale

locale = None


def trans(key, reload=False):
    """
    Get translation

    :param key: translation key
    :param reload: force reload translations
    :return: translation
    """
    global locale
    if locale is None:
        locale = Locale()
    if reload:
        locale.reload()
    return locale.get(key)


def get_init_value(key="__version__"):
    """
    Get version

    :return: version
    """
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '__init__.py'))
    result = re.search(r'{}\s*=\s*[\'"]([^\'"]*)[\'"]'.format(key),
                       open(path, "r", encoding="utf-8").read())
    return result.group(1)
