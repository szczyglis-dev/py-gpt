#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.02.01 02:00:00                  #
# ================================================== #

import json
import os
import re
from datetime import datetime
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

def trans_reload():
    """
    Reload translations
    """
    global locale
    if locale is None:
        locale = Locale()
    locale.reload_config()


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
        root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    else:
        root = os.path.dirname(__file__)
    path = os.path.abspath(os.path.join(root, '__init__.py'))
    try:
        if init_file_meta is None:
            with open(path, "r", encoding="utf-8") as f:
                init_file_meta = f.read()
        result = re.search(r'{}\s*=\s*[\'"]([^\'"]*)[\'"]'.format(key), init_file_meta)
        return result.group(1)
    except Exception as e:
        print(e)


def get_app_meta() -> dict:
    """
    Return app meta data

    :return: app meta data
    """
    return {
        'github': get_init_value("__github__"),
        'website': get_init_value("__website__"),
        'docs': get_init_value("__documentation__"),
        'pypi': get_init_value("__pypi__"),
        'snap': get_init_value("__snap__"),
        'ms_store': get_init_value("__ms_store__"),
        'donate': get_init_value("__donate__"),
        'discord': get_init_value("__discord__"),
        'version': get_init_value("__version__"),
        'build': get_init_value("__build__"),
        'author': get_init_value("__author__"),
        'email': get_init_value("__email__"),
        'donate_coffee': get_init_value("__donate_coffee__"),
        'donate_paypal': get_init_value("__donate_paypal__"),
        'donate_github': get_init_value("__donate_github__"),
        'report': get_init_value("__report__"),
    }


def parse_args(data: list) -> dict:
    """
    Parse keyword arguments from list of items

    :param data: list of arguments items
    :return: dict of parsed keyword arguments
    """
    args = {}
    for item in data:
        type = "str"
        key = item['name']
        value = item['value']
        if "type" in item:
            type = item['type']
        if type == 'int':
            try:
                args[key] = int(value)
            except Exception:
                args[key] = 0
        elif type == 'float':
            try:
                args[key] = float(value)
            except Exception:
                args[key] = 0.0
        elif type == 'bool':
            if str(value).lower() == 'true':
                args[key] = True
            elif str(value).lower() == 'false':
                args[key] = False
            else:
                try:
                    args[key] = bool(int(value))
                except Exception:
                    args[key] = False
        elif type == 'dict':
            if isinstance(value, dict):
                args[key] = value
            else:
                try:
                    args[key] = json.loads(value)
                except:
                    args[key] = {}
        elif type == 'list':
            if isinstance(value, list):
                args[key] = value
            else:
                try:
                    args[key] = [x.strip() for x in value.split(',')]
                except:
                    args[key] = []
        elif type == 'None':
            args[key] = None
        else:
            args[key] = str(value)
    return args


def unpack_var(var: any, type: str) -> any:
    """
    Unpack variable from DB row

    :param var: Variable
    :param type: Variable type
    """
    if type == 'int':
        try:
            return int(var)
        except Exception:
            return 0
    elif type == 'float':
        try:
            return float(var)
        except Exception:
            return 0.0
    elif type == 'bool':
        try:
            return bool(var)
        except Exception:
            return False
    return var

def pack_arg(arg: any, type: str) -> any:
    """
    Pack argument to store in JSON

    :param arg: Argument value
    :param type: Argument type
    """
    if arg is None or arg == "":
        return ""
    if type == "list":
        try:
            return ",".join(arg)
        except Exception:
            return ""
    elif type == "dict":
        try:
            return json.dumps(arg)
        except Exception:
            return ""
    elif type == "bool":
        try:
            return str(arg)
        except Exception:
            return ""
    return arg


def get_image_extensions() -> list:
    """
    Return list of image extensions

    :return: list of image extensions
    """
    return ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp']

def is_image(path: str) -> bool:
    """
    Check if file is image

    :param path: path to file
    :return: True if image
    """
    return path.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif', '.webp'))


def get_tz_offset() -> int:
    """
    Return timezone offset

    :return: timezone offset (seconds)
    """
    utc_now = datetime.utcnow()
    utc_timestamp = int(utc_now.timestamp())
    now = datetime.now()
    now_timestamp = int(now.timestamp())
    return now_timestamp - utc_timestamp

def natsort(l: list) -> list:
    """
    Sort the given list in natural order

    :param l: list to sort
    """
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    return sorted(l, key=alphanum_key)