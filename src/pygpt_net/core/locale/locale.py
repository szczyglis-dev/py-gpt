#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.30 18:45:00                  #
# ================================================== #

import os
import configparser
from typing import Optional, Dict, Tuple, List

from pygpt_net.config import Config


class Locale:
    # Logical domain -> ordered directories containing locale.<lang>.ini.
    # This is class-scoped so add-ons can register domains before the lazy,
    # process-wide Locale instance in pygpt_net.utils is created.
    _domain_dirs: Dict[str, List[str]] = {}

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

    @classmethod
    def register_domain(cls, domain: str, path: str, prepend: bool = False) -> bool:
        """
        Register a directory for a logical translation domain.

        Registered directories use the canonical add-on/plugin layout:
        ``<path>/locale.<lang>.ini``. Multiple directories can be registered for
        one domain; later directories override earlier ones.

        :param domain: logical translation domain
        :param path: directory containing locale.<lang>.ini files
        :param prepend: insert before existing domain directories
        :return: True when registry changed
        """
        if not isinstance(domain, str) or not domain.strip() or not path:
            return False
        domain = domain.strip()
        path = os.path.realpath(os.path.abspath(str(path)))
        paths = cls._domain_dirs.setdefault(domain, [])
        if path in paths:
            return False
        if prepend:
            paths.insert(0, path)
        else:
            paths.append(path)
        return True

    @classmethod
    def unregister_domain(cls, domain: str, path: Optional[str] = None):
        """Unregister a complete domain or one directory assigned to it."""
        if domain not in cls._domain_dirs:
            return
        if path is None:
            cls._domain_dirs.pop(domain, None)
            return
        path = os.path.realpath(os.path.abspath(str(path)))
        paths = cls._domain_dirs.get(domain, [])
        cls._domain_dirs[domain] = [item for item in paths if item != path]
        if not cls._domain_dirs[domain]:
            cls._domain_dirs.pop(domain, None)

    @classmethod
    def get_domain_dirs(cls, domain: str) -> List[str]:
        """Return a copy of registered directories for a logical domain."""
        return list(cls._domain_dirs.get(domain, []))

    def _clear_cache(self):
        """Clear internal file cache."""
        self._file_cache.clear()

    def reload_config(self):
        """Reload configuration and every translation domain already in use."""
        workdir = self.config.prepare_workdir()
        self.config.set_workdir(workdir)
        self.config.load(False)
        if self.config.has('lang'):
            self.lang = self.config.get_lang()
        self._clear_cache()

        # The main domain is always present. Keep every lazily loaded custom
        # domain in sync too, so add-on/provider labels switch language live.
        domains = list(self.data.keys())
        if self.default_domain not in domains:
            domains.insert(0, self.default_domain)
        for domain in domains:
            self.load(self.lang, None if domain == self.default_domain else domain)

    def reload(self, domain: Optional[str] = None):
        """
        Reload translations for domain

        :param domain: translation domain
        """
        self.config.load(False)
        if self.config.has('lang'):
            self.lang = self.config.get_lang()
        self._clear_cache()
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
        after all existing files (bundled/custom domain sources + user override)
        have been parsed successfully. This prevents partially loaded/broken
        locale data from replacing the English fallback.

        :param lang: language code
        :param domain: translation domain
        :return: True if locale files were loaded without errors
        """
        domain_id = domain or self.default_domain
        mapping = self.data.setdefault(domain_id, {})
        pending = {}
        current_path = None

        try:
            paths = self.get_paths(domain_id, lang)
            for current_path in paths:
                if os.path.isfile(current_path):
                    pending.update(self.from_file(current_path))
        except Exception as e:
            if lang != self.fallback:
                filename = (
                    os.path.basename(current_path)
                    if current_path
                    else f'locale.{lang}.ini'
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

    def get_paths(self, domain: str, lang: str) -> List[str]:
        """Return ordered locale file paths for a domain and language."""
        registered = self.get_domain_dirs(domain)
        if registered:
            paths = [os.path.join(path, f'locale.{lang}.ini') for path in registered]
        elif domain.startswith('plugin.'):
            plugin_id = domain[len('plugin.'):]
            paths = [os.path.join(
                self.config.get_app_path(),
                'data', 'locale', 'plugin', plugin_id,
                f'locale.{lang}.ini',
            )]
        else:
            paths = [self.get_base_path(domain, lang)]

        # Keep the existing profile override mechanism as the last source. This
        # remains useful for the main locale and for users overriding a custom
        # logical domain without modifying an add-on directory.
        paths.append(self.get_user_path(domain, lang))
        return paths

    def get_base_path(
            self,
            domain: str,
            lang: str
    ) -> str:
        """
        Get legacy/default base path for locale file.

        Custom domains should be registered with :meth:`register_domain`; their
        canonical filename is ``locale.<lang>.ini`` inside the registered dir.

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
        Get user path for locale file (overwrites base/custom domain sources)

        :param domain: translation domain
        :param lang: language code
        :return: path to translations file
        """
        return os.path.join(
            self.config.get_user_path(),
            'locale',
            f'{domain}.{lang}.ini'
        )
