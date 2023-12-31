#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.31 04:00:00                  #
# ================================================== #

import os
import re
from pygpt_net.core.locale import Locale

locale = None
init_file_meta = None


def _(key: str, reload: bool = False, domain: str = None) -> str:
    """
    Short alias for trans()

    :param key: translation key
    :param reload: force reload translations
    :param domain: translation domain
    :return: translated string
    """
    return trans(key, reload, domain)


def trans(key: str, reload: bool = False, domain: str = None) -> str:
    """
    Return translation

    :param key: translation key
    :param reload: force reload translations
    :param domain: translation domain
    :return: translated string
    """
    global locale
    if locale is None:
        locale = Locale(domain)
    if reload:
        locale.reload(domain)
    return locale.get(key, domain)


def get_init_value(key: str = "__version__") -> str:
    """
    Return config value from __init__.py

    :param key: config key
    :return: config value
    """
    global init_file_meta

    if __file__.endswith('.pyc'):  # if compiled with pyinstaller
        root = '.'
    else:
        root = os.path.dirname(__file__)
    path = os.path.abspath(os.path.join(root, '__init__.py'))
    try:
        if init_file_meta is None:
            f = open(path, "r", encoding="utf-8")
            init_file_meta = f.read()
            f.close()
        result = re.search(r'{}\s*=\s*[\'"]([^\'"]*)[\'"]'.format(key), init_file_meta)
        return result.group(1)
    except Exception as e:
        print(e)


def get_app_meta() -> dict:
    """
    Return app meta data
    :return: app meta data=
    """
    return {
        'github': get_init_value("__github__"),
        'website': get_init_value("__website__"),
        'docs': get_init_value("__documentation__"),
        'pypi': get_init_value("__pypi__"),
        'snap': get_init_value("__snap__"),
        'version': get_init_value("__version__"),
        'build': get_init_value("__build__"),
        'author': get_init_value("__author__"),
        'email': get_init_value("__email__")
    }
