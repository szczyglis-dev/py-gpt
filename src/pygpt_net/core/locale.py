#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.15 10:00:00                  #
# ================================================== #

import os
import configparser
import io

from pygpt_net.config import Config


class Locale:
    def __init__(self, domain: str = None, config=None):
        """
        Locale loader

        :param domain: translation domain
        :param config: Config instance
        """
        if config is None:
            self.config = Config()
        else:
            self.config = config
        self.lang = 'en'  # default language = en
        self.fallback = 'en'  # fallback language = en
        self.default_domain = 'locale'  # default translation domain
        self.ini_key = 'LOCALE'  # ini key for translations
        self.data = {}
        self.config.init(False)  # load config
        if self.config.has('lang'):
            self.lang = self.config.get_lang()
        self.load(self.lang, domain)

    def reload_config(self):
        """Reload configuration"""
        workdir = self.config.prepare_workdir()
        self.config.set_workdir(workdir)
        self.config.load(False)
        if self.config.has('lang'):
            self.lang = self.config.get_lang()
        self.load(self.lang)

    def reload(self, domain: str = None):
        """
        Reload translations for domain

        :param domain: translation domain
        """
        self.config.load(False)
        if self.config.has('lang'):
            self.lang = self.config.get_lang()
        self.load(self.lang, domain)

    def from_file(self, path: str) -> dict:
        """
        Load and parse translations from file

        :param path: path to ini file
        :return: dict with translations
        """
        ini = configparser.ConfigParser()
        data = io.open(path, mode="r", encoding="utf-8")
        ini.read_string(data.read())
        return dict(ini.items(self.ini_key))

    def load_by_lang(self, lang: str, domain: str = None):
        """
        Load translation data by language code

        :param lang: language code
        :param domain: translation domain
        """
        id = self.default_domain
        if domain is not None:
            id = domain
        if id not in self.data:
            self.data[id] = {}
        try:
            path = self.get_base_path(id, lang)
            if os.path.exists(path):
                data = self.from_file(path)
                for key in data:
                    self.data[id][key] = data[key]
            path = self.get_user_path(id, lang)
            if os.path.exists(path):
                data = self.from_file(path)
                for key in data:
                    self.data[id][key] = data[key]
        except Exception as e:
            print(e)

    def load(self, lang: str, domain: str = None):
        """
        Load translation data

        :param lang: language code
        :param domain: translation domain
        """
        if type(lang) is not str:
            lang = self.fallback
        if lang != self.fallback:
            self.load_by_lang(self.fallback, domain)  # load fallback first
        self.load_by_lang(lang, domain)

    def get(self, key: str, domain: str = None, params: dict = None) -> str:
        """
        Return translation for key and domain

        :param key: translation key
        :param domain: translation domain
        :param params: translation params dict for replacement
        :return: translated string or key if not found
        """
        id = self.default_domain
        if domain is not None:
            id = domain
        if id not in self.data:
            self.load(self.lang, domain)
        if id in self.data and key in self.data[id]:
            if type(params) is dict and len(params) > 0:
                try:
                    return self.data[id][key].replace('\\n', "\n").format(**params)
                except KeyError:
                    pass
            return self.data[id][key].replace('\\n', "\n")
        else:
            return key

    def get_base_path(self, domain: str, lang: str) -> str:
        """
        Get base path for locale file

        :param domain: translation domain
        :param lang: language code
        :return: path to translations file
        """
        return os.path.join(self.config.get_app_path(), 'data', 'locale', domain + '.' + lang + '.ini')

    def get_user_path(self, domain: str, lang: str) -> str:
        """
        Get user path for locale file (overwrites base path)

        :param domain: translation domain
        :param lang: language code
        :return: path to translations file
        """
        return os.path.join(self.config.get_user_path(), 'locale', domain + '.' + lang + '.ini')