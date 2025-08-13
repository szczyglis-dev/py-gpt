#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.13 16:00:00                  #
# ================================================== #

import os
import configparser
from typing import Optional, Dict, Tuple

from pygpt_net.config import Config


class Locale:
    def __init__(
            self,
            domain: Optional[str] = None,
            config: Optional[Config] = None
    ):
        """
        Locale loader

        :param domain: translation domain
        :param config: Config instance
        """
        self.config = config if config is not None else Config()
        self.lang = 'en'  # default language = en
        self.fallback = 'en'  # fallback language = en
        self.default_domain = 'locale'  # default translation domain
        self.ini_key = 'LOCALE'  # ini key for translations
        self.data: Dict[str, Dict[str, str]] = {}

        # cache: path -> (mtime, parsed_dict)
        self._file_cache: Dict[str, Tuple[float, Dict[str, str]]] = {}

        # load config once
        self.config.init(False)
        if self.config.has('lang'):
            self.lang = self.config.get_lang()

        self.load(self.lang, domain)

    def _clear_cache(self):
        """Clear internal file cache."""
        self._file_cache.clear()

    def reload_config(self):
        """Reload configuration"""
        workdir = self.config.prepare_workdir()
        self.config.set_workdir(workdir)
        self.config.load(False)
        if self.config.has('lang'):
            self.lang = self.config.get_lang()
        self._clear_cache()  # ensure fresh read
        self.load(self.lang)

    def reload(self, domain: Optional[str] = None):
        """
        Reload translations for domain

        :param domain: translation domain
        """
        self.config.load(False)
        if self.config.has('lang'):
            self.lang = self.config.get_lang()
        self._clear_cache()  # ensure fresh read
        self.load(self.lang, domain)

    def from_file(self, path: str) -> dict:
        """
        Load and parse translations from file (cached by mtime)

        :param path: path to ini file
        :return: dict with translations
        """
        try:
            mtime = os.path.getmtime(path)
        except FileNotFoundError:
            return {}

        cached = self._file_cache.get(path)
        if cached is not None and cached[0] == mtime:
            return cached[1]

        # RawConfigParser with interpolation disabled
        ini = configparser.RawConfigParser(interpolation=None)
        ini.read(path, encoding='utf-8')

        data = dict(ini.items(self.ini_key))
        self._file_cache[path] = (mtime, data)
        return data

    def load_by_lang(
            self,
            lang: str,
            domain: Optional[str] = None
    ):
        """
        Load translation data by language code

        :param lang: language code
        :param domain: translation domain
        """
        domain_id = domain or self.default_domain
        mapping = self.data.setdefault(domain_id, {})

        try:
            base_path = self.get_base_path(domain_id, lang)
            if os.path.isfile(base_path):
                mapping.update(self.from_file(base_path))

            user_path = self.get_user_path(domain_id, lang)
            if os.path.isfile(user_path):
                mapping.update(self.from_file(user_path))
        except Exception as e:
            print(e)

    def load(
            self,
            lang: str,
            domain: Optional[str] = None
    ):
        """
        Load translation data

        :param lang: language code
        :param domain: translation domain
        """
        if not isinstance(lang, str) or not lang:
            lang = self.fallback

        if lang != self.fallback:
            self.load_by_lang(self.fallback, domain)
        self.load_by_lang(lang, domain)

    def get(
            self,
            key: str,
            domain: Optional[str] = None,
            params: Optional[dict] = None
    ) -> str:
        """
        Return translation for key and domain

        :param key: translation key
        :param domain: translation domain
        :param params: translation params dict for replacement
        :return: translated string or key if not found
        """
        domain_id = domain or self.default_domain
        mapping = self.data.get(domain_id)

        if mapping is None:
            self.load(self.lang, domain)
            mapping = self.data.get(domain_id, {})

        val = mapping.get(key)
        if val is None:
            return key
        text = val.replace('\\n', '\n')

        if isinstance(params, dict) and params:
            try:
                return text.format(**params)
            except KeyError:
                pass
        return text

    def get_base_path(
            self,
            domain: str,
            lang: str
    ) -> str:
        """
        Get base path for locale file

        :param domain: translation domain
        :param lang: language code
        :return: path to translations file
        """
        return os.path.join(
            self.config.get_app_path(),
            'data', 'locale',
            f'{domain}.{lang}.ini'
        )

    def get_user_path(
            self,
            domain: str,
            lang: str
    ) -> str:
        """
        Get user path for locale file (overwrites base path)

        :param domain: translation domain
        :param lang: language code
        :return: path to translations file
        """
        return os.path.join(
            self.config.get_user_path(),
            'locale',
            f'{domain}.{lang}.ini'
        )