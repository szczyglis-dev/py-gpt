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

from typing import Optional


class LocaleDomain:
    """Small mixin for runtime objects that can own a translation domain."""

    def init_locale_domain(self):
        """Initialize locale metadata without forcing a Locale instance."""
        self.locale_domain: Optional[str] = None
        self.locale_dir: Optional[str] = None

    def set_locale_domain(
            self,
            domain: Optional[str],
            path: Optional[str] = None,
            register: bool = False,
    ):
        """Assign a logical translation domain and, optionally, its directory."""
        self.locale_domain = str(domain).strip() if domain else None
        self.locale_dir = str(path) if path else None
        if register and self.locale_domain and self.locale_dir:
            from pygpt_net.utils import register_locale_domain
            register_locale_domain(self.locale_domain, self.locale_dir)

    def get_locale_domain(self) -> Optional[str]:
        """Return the object's logical translation domain, if any."""
        return getattr(self, 'locale_domain', None)

    def get_locale_dir(self) -> Optional[str]:
        """Return the directory that contains ``locale.<lang>.ini`` files."""
        return getattr(self, 'locale_dir', None)

    def trans(self, key: str, reload: bool = False) -> str:
        """Translate a key using this object's domain, falling back to main locale."""
        from pygpt_net.utils import trans
        return trans(key, reload=reload, domain=self.get_locale_domain())
