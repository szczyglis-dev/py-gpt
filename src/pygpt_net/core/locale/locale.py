#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.11 19:50:00                  #
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
    ) -> bool:
        """
        Load translation data by language code.

        Files for a language are loaded transactionally: values are applied only
        after all existing files (bundled + user override) have been parsed
        successfully. This prevents partially loaded/broken locale data from
        replacing the English fallback.

        :param lang: language code
        :param domain: translation domain
        :return: True if locale files were loaded without errors
        """
        domain_id = domain or self.default_domain
        mapping = self.data.setdefault(domain_id, {})
        pending = {}
        current_path = None

        try:
            paths = [
                self.get_base_path(domain_id, lang),
                self.get_user_path(domain_id, lang),
            ]
            for current_path in paths:
                if os.path.isfile(current_path):
                    pending.update(self.from_file(current_path))
        except Exception as e:
            if lang != self.fallback:
                filename = (
                    os.path.basename(current_path)
                    if current_path
                    else f'{domain_id}.{lang}.ini'
                )
                print(f"Locale file is broken: {filename} - {e}")
            else:
                print(e)
            return False

        mapping.update(pending)
        return True

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

        domain_id = domain or self.default_domain

        # Always rebuild the requested domain from scratch. Without clearing it,
        # keys left by a previously selected language could survive a reload.
        self.data[domain_id] = {}

        if lang == self.fallback:
            self.load_by_lang(self.fallback, domain)
            if domain_id == self.default_domain:
                self.lang = self.fallback
            return

        # English is the complete baseline. The selected locale is only applied
        # if every existing locale file parses successfully. On any error the
        # English mapping remains untouched.
        self.load_by_lang(self.fallback, domain)
        if not self.load_by_lang(lang, domain):
            if domain_id == self.default_domain:
                self.lang = self.fallback
            return

        if domain_id == self.default_domain:
            self.lang = lang

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