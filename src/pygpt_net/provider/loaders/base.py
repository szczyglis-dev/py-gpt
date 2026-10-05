#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.26 04:00:00                  #
# ================================================== #

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llama_index.core.readers.base import BaseReader

from pygpt_net.core.locale import LocaleDomain


def normalize_field(definition):
    """Accept legacy type names and extended field schemas without mutating either."""
    import copy
    meta = copy.deepcopy(definition) if isinstance(definition, dict) else {'type': definition or 'str'}
    meta.setdefault('type', 'str')
    meta['extra'] = dict(meta.get('extra') or {})
    if meta['type'] in ('secret', 'path'):
        meta['extra'][meta['type']] = True
        meta['type'] = 'str'
    return meta


class BaseLoader(LocaleDomain):
    def __init__(self, *args, **kwargs):
        self.init_locale_domain()
        self.window = None
        self.id = ""
        self.name = ""
        self.icon = ":/icons/language.svg"  # Override per loader for connection tiles/pickers.
        self.extensions = []
        self.type = ["file"]  # list of types: file, web
        self.instructions = []  # list of instructions for 'web_index' command for how to handle this type
        self.args = {}  # custom keyword arguments
        self.init_args = {}  # initial keyword arguments
        self.init_args_labels = {}
        self.init_args_types = {}
        self.init_args_desc = {}
        self.init_args_required = {}
        self.allow_compiled = True  # allow in compiled and Snap versions
        # This is required due to some readers may require Python environment to install additional packages

    def attach_window(self, window):
        """
        Attach window instance

        :param window: Window instance
        """
        self.window = window

    def configure_locale(self, source, required_config=(), required_options=()):
        """Bind field metadata to a loader-owned domain after defining its schema.

        Built-ins and add-ons keep translations beside their module in locale/locale.en.ini. Add-on loaders
        can use the same method or continue supplying their own locale domain.
        """
        from pathlib import Path
        self.set_locale_domain(
            'loader.' + self.id,
            str(Path(source).parent / 'locale'), register=True,
        )
        self.localize_fields(required_config, required_options)

    def localize_fields(self, required_config=(), required_options=()):
        """Supply standard keys while preserving explicit add-on metadata."""
        for key in self.init_args:
            self.init_args_labels.setdefault(key, f'config.{key}.label')
            self.init_args_desc.setdefault(key, f'config.{key}.desc')
            self.init_args_required.setdefault(key, key in required_config)
        for item in self.instructions:
            for instruction in item.values():
                for key, meta in instruction.get('args', {}).items():
                    meta.setdefault('label', f'options.{key}.label')
                    meta.setdefault('description', f'options.{key}.desc')
                    meta.setdefault('required', key in required_options)

    def set_args(self, args: dict):
        """
        Set loader initial keyword arguments

        :param args: keyword arguments dict
        """
        self.args = args

    def explode(self, value: str) -> list:
        """
        Explode list from string

        :param value: value string
        :return: list
        """
        if value:
            items = value.split(",")
            return [item.strip() for item in items]
        return []

    def get_args(self):
        """
        Prepare keyword arguments for reader init method

        :return: keyword arguments dict
        """
        args = {}
        for key in self.init_args:
            args[key] = self.init_args[key]
            if key in self.args:
                args[key] = self.args[key]
        return args

    def prepare_args(self, **kwargs) -> dict:
        """
        Prepare arguments for reader load method

        :param kwargs: keyword arguments
        :return: args to pass to reader
        """
        return kwargs

    def get_external_id(self, args: dict = None) -> str:
        """
        Get unique web content identifier

        :param args: load_data args
        :return: unique content identifier
        """
        if "url" in args:
            return args.get("url")
        return ""

    def is_supported_attachment(self, source: str) -> bool:
        """
        Check if attachment is supported by loader

        :param source: attachment source
        :return: True if supported
        """
        return False

    def get(self) -> "BaseReader":
        """
        Get reader instance

        :return: Data reader instance
        """
        pass
