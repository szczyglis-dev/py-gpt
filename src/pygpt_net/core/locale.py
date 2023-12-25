#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.25 21:00:00                  #
# ================================================== #

import json
import os
import configparser
import io

from pygpt_net.config import Config


class Locale:
    def __init__(self, domain=None):
        """
        Locale handler

        :param domain: translation domain
        """
        self.config = Config()
        self.config.init(False)
        self.lang = 'en'
        if self.config.has('lang'):
            self.lang = self.config.get('lang')
        self.data = {}
        self.load(self.lang, domain)

    def reload(self, domain=None):
        """
        Reload translations for domain

        :param domain: translation domain
        """
        self.config.load(False)
        if self.config.has('lang'):
            self.lang = self.config.get('lang')
        self.load(self.lang, domain)

    def load(self, lang, domain=None):
        """
        Load translation ini file

        :param lang: language code
        :param domain: translation domain
        """
        if type(lang) is not str:
            lang = 'en'
        locale_id = 'locale'
        if domain is not None:
            locale_id = domain

        # at first check if file exists in user data dir (override)
        path = os.path.join(self.config.get_user_path(), 'locale', locale_id + '.' + lang + '.ini')
        if not os.path.exists(path):
            # if not check if file exists in app data dir
            path = os.path.join(self.config.get_root_path(), 'data', 'locale', locale_id + '.' + lang + '.ini')
        if not os.path.exists(path):
            print("FATAL ERROR: {} not found!".format(path))
            return None
        # TODO: add home dir override as option
        try:
            ini = configparser.ConfigParser()
            data = io.open(path, mode="r", encoding="utf-8")
            ini.read_string(data.read())
            self.data[locale_id] = dict(ini.items('LOCALE'))
        except Exception as e:
            print(e)

    def get(self, key, domain=None):
        """
        Return translation for key and domain

        :param key: translation key
        :param domain: translation domain
        :return: translated string
        :rtype: str
        """
        locale_id = 'locale'
        if domain is not None:
            locale_id = domain

        if locale_id not in self.data:
            self.load(self.lang, domain)

        if locale_id in self.data and key in self.data[locale_id]:
            return self.data[locale_id][key].replace('\\n', "\n")
        else:
            return key
