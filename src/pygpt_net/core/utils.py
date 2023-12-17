#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.17 22:00:00                  #
# ================================================== #

import os
import re
from .locale import Locale

locale = None


def trans(key, reload=False):
    """
    Return translation

    :param key: translation key
    :param reload: force reload translations
    :return: translated string
    :rtype: str
    """
    global locale
    if locale is None:
        locale = Locale()
    if reload:
        locale.reload()
    return locale.get(key)


def get_init_value(key="__version__"):
    """
    Return config value from __init__.py

    :param key: config key
    :return: config value
    :rtype: str
    """
    if __file__.endswith('.pyc'):  # if compiled with pyinstaller
        root = '.'
    else:
        root = os.path.join(os.path.dirname(__file__), os.pardir)
    path = os.path.abspath(os.path.join(root, '__init__.py'))
    try:
        f = open(path, "r", encoding="utf-8")
        data = f.read()
        f.close()
        result = re.search(r'{}\s*=\s*[\'"]([^\'"]*)[\'"]'.format(key), data)
        return result.group(1)
    except Exception as e:
        print(e)
