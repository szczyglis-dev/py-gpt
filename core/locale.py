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

import json
import os
import configparser
import io

from core.config import Config


class Locale:
    def __init__(self):
        """Locale handler"""
        self.config = Config()
        self.config.init(False)
        self.lang = self.config.data['lang']
        self.data = {}
        self.load(self.lang)

    def reload(self):
        """
        Reload translations
        """
        self.config.load_config()
        self.lang = self.config.data['lang']
        self.load(self.lang)

    def load(self, lang):
        """
        Loads translation ini file

        :param lang: language code
        """
        if type(lang) is not str:
            lang = 'en'
        path = os.path.join('.', 'data', 'locale', 'locale.' + lang + '.ini')
        if not os.path.exists(path):
            print("FATAL ERROR: {} not found!".format(path))
            return None
        try:
            ini = configparser.ConfigParser()
            data = io.open(path, mode="r", encoding="utf-8")
            ini.read_string(data.read())
            self.data = dict(ini.items('LOCALE'))
        except Exception as e:
            print(e)

    def get(self, key):
        """
        Returns translation for key

        :param key: translation key
        :return: translated string
        """
        if key in self.data:
            return self.data[key].replace('\\n', "\n")
        else:
            return key
