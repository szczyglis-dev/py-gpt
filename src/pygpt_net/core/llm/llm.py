#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.02 20:00:00                  #
# ================================================== #

import hashlib
import re
from typing import Optional, List, Dict, Any


class LLM:
    def __init__(self, window=None):
        """
        LLMs manager

        :param window: Window instance
        """
        self.window = window
        self.llms = {}
        self._runtime_custom_ids = set()
        self._runtime_custom_signature = None


    @staticmethod
    def is_custom_provider(id: str) -> bool:
        """Return True for a runtime custom provider ID."""
        return isinstance(id, str) and id.startswith("custom_")

    @staticmethod
    def make_custom_provider_id(name: str) -> str:
        """Build a deterministic internal provider ID from its display name."""
        raw = (name or "").strip()
        normalized = raw.casefold()
        slug = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_") or "provider"
        slug = slug[:40]
        digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:8]
        return f"custom_{slug}_{digest}"

    def sync_custom(self, force: bool = False):
        """Synchronize runtime custom providers from ``api_custom_providers`` config."""
        if self.window is None or not hasattr(self.window, "core"):
            return
        config = getattr(self.window.core, "config", None)
        if config is None:
            return

        rows = config.get("api_custom_providers", []) or []
        if not isinstance(rows, list):
            rows = []
        signature = repr([
            (
                str(item.get("name", "") or "").strip(),
                str(item.get("api_base", "") or "").strip(),
                str(item.get("api_key", "") or ""),
            )
            for item in rows if isinstance(item, dict)
        ])
        if not force and signature == self._runtime_custom_signature:
            return

        # Remove only providers previously created from runtime config. Providers
        # registered through a custom launcher remain untouched.
        for provider_id in list(self._runtime_custom_ids):
            self.llms.pop(provider_id, None)
        self._runtime_custom_ids.clear()

        if not rows:
            self._runtime_custom_signature = signature
            return

        from pygpt_net.provider.llms.custom import CustomLLM

        for item in rows:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "") or "").strip()
            api_base = str(item.get("api_base", "") or "").strip()
            api_key = str(item.get("api_key", "") or "")
            if not name or not api_base:
                continue

            provider_id = self.make_custom_provider_id(name)
            # Do not overwrite a provider registered by code with the same ID.
            if provider_id in self.llms and provider_id not in self._runtime_custom_ids:
                continue
            provider = CustomLLM(
                provider_id=provider_id,
                name=name,
                api_base=api_base,
                api_key=api_key,
            )
            if hasattr(provider, "bind"):
                provider.bind(self.window)
            self.llms[provider_id] = provider
            self._runtime_custom_ids.add(provider_id)

        self._runtime_custom_signature = signature

    def get_ids(
            self,
            type: Optional[str] = None
    ) -> List[str]:
        """
        Get providers ids

        :param type: provider type
        :return: providers ids
        """
        self.sync_custom()
        if type is not None:
            return [id for id in self.llms.keys() if type in self.llms[id].type]
        return list(self.llms.keys())  # get all

    def get_choices(
            self,
            type: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Get providers choices

        :param type: provider type
        :return: providers choices
        """
        self.sync_custom()
        choices = {}
        if type is not None:
            for id in list(self.llms.keys()):
                if type in self.llms[id].type:
                    choices[id] = self.llms[id].name
        else:
            for id in list(self.llms.keys()):
                choices[id] = self.llms[id].name

        # sorted by name
        return dict(sorted(choices.items(), key=lambda item: item[1].lower()))

    def get_provider_name(self, id: str) -> str:
        """
        Get provider name by id

        :param id: LLM id
        :return: provider name
        """
        self.sync_custom()
        return self.llms[id].name if id in self.llms else id

    def get(self, id: str):
        """
        Get LLM provider by id

        :param id: LLM id
        :return: LLM provider instance
        """
        self.sync_custom()
        return self.llms[id] if id in self.llms else None

    def get_config(self, provider_id: str, key: str, default: Any = None) -> Any:
        """Read provider-scoped config through the registered provider."""
        provider = self.get(provider_id)
        if provider is None or not hasattr(provider, "get_config"):
            return default
        return provider.get_config(key, default)

    def set_config(self, provider_id: str, key: str, value: Any):
        """Write provider-scoped config through the registered provider."""
        provider = self.get(provider_id)
        if provider is not None and hasattr(provider, "set_config"):
            provider.set_config(key, value)

    def register(
            self,
            id: str,
            llm
    ):
        """
        Register LLM provider

        :param id: LLM id
        :param llm: LLM object
        """
        if hasattr(llm, "bind"):
            llm.bind(self.window)
        self.llms[id] = llm
        # Provider-owned settings are assembled after registration, so force a
        # refresh if Settings happened to be loaded earlier during bootstrap.
        try:
            self.window.core.settings.initialized = False
        except (AttributeError, RuntimeError):
            pass

    def get_by_config_id(self, config_id: str):
        """Return the first registered provider using a logical config ID."""
        self.sync_custom()
        for provider in self.llms.values():
            current = provider.get_config_id() if hasattr(provider, "get_config_id") else getattr(provider, "id", "")
            if current == config_id:
                return provider
        return None

    def sync_provider_configs(self, save: bool = False) -> bool:
        """Materialize defaults declared by registered providers."""
        self.sync_custom()
        changed = False
        seen = set()
        for provider in self.llms.values():
            if not hasattr(provider, "sync_config"):
                continue
            config_id = provider.get_config_id() if hasattr(provider, "get_config_id") else getattr(provider, "id", "")
            if not config_id or config_id in seen:
                continue
            seen.add(config_id)
            if provider.sync_config():
                changed = True
        if changed and save:
            self.window.core.config.save()
        return changed

    @staticmethod
    def _setting_type(value: str) -> str:
        return {
            "str": "text",
            "string": "text",
            "text": "text",
            "bool": "bool",
            "int": "int",
            "float": "float",
            "combo": "combo",
            "textarea": "textarea",
            "dict": "dict",
        }.get(str(value or "str").lower(), str(value or "text").lower())

    def _build_setting_option(self, provider, config_id: str, key: str, field: dict, *, is_extra: bool) -> tuple[str, dict]:
        """Convert a provider schema field into the regular Settings format."""
        provider_name = getattr(provider, "config_name", "") or getattr(provider, "name", "") or config_id
        path = f"extra.{key}" if is_extra else key
        option_id = f"provider.{config_id}.{path}"
        use_locale = bool(field.get("use_locale", False))

        label = field.get("label")
        description = field.get("desc", field.get("description"))
        label_params = field.get("label_params") or {}
        description_params = field.get("description_params") or {}

        # Common credentials use generic, translated labels automatically.
        if key == "api_key" and not is_extra and not label:
            label = "settings.provider.api_key.label"
            description = description or "settings.provider.api_key.desc"
            description_params = {"provider": provider_name}
            use_locale = True
        elif key == "api_base" and not is_extra and not label:
            label = "settings.provider.api_base.label"
            description = description or "settings.provider.api_base.desc"
            description_params = {"provider": provider_name}
            use_locale = True
        elif not label:
            label = key.replace("_", " ").strip().capitalize()

        option = {
            "section": "api_keys",
            "type": self._setting_type(field.get("type", "str")),
            "label": label,
            "description": description,
            "value": field.get("default"),
            "secret": bool(field.get("secret", False)),
            "persist": True,
            "advanced": bool(field.get("advanced", False)),
            "tab": config_id,
            "_provider": getattr(provider, "id", config_id),
            "_provider_config_id": config_id,
            "_provider_key": path,
            "_provider_dynamic": True,
            "_tab_label": provider_name,
            "_use_locale": use_locale,
            "_label_params": label_params,
            "_description_params": description_params,
            "_ui_key": f"settings.{option_id}",
        }
        if key == "api_key" and not is_extra:
            option["secret"] = field.get("secret", True)
            option["extra"] = dict(field.get("extra") or {"bold": True})
        elif field.get("extra"):
            option["extra"] = dict(field.get("extra") or {})
        for name in ("urls", "min", "max", "step", "multiplier", "choices", "from_defaults", "slider", "real_time"):
            if name in field:
                option[name] = field[name]
        return option_id, option

    def get_settings_options(self) -> Dict[str, dict]:
        """Build Settings -> API Keys fields from all registered LLM providers."""
        self.sync_custom()
        options = {}
        seen = set()
        for provider in self.llms.values():
            if not hasattr(provider, "get_settings_schema"):
                continue
            schema = provider.get_settings_schema()
            if not schema:
                continue
            config_id = provider.get_config_id() if hasattr(provider, "get_config_id") else getattr(provider, "id", "")
            if not config_id or config_id in seen:
                continue
            seen.add(config_id)

            for key in ("api_key", "api_base"):
                field = schema.get(key)
                if isinstance(field, dict):
                    option_id, option = self._build_setting_option(provider, config_id, key, field, is_extra=False)
                    options[option_id] = option

            extra = schema.get("extra", {})
            if not isinstance(extra, dict):
                continue
            # Advanced fields are always rendered after regular extra fields.
            regular = [(key, field) for key, field in extra.items() if isinstance(field, dict) and not field.get("advanced", False)]
            advanced = [(key, field) for key, field in extra.items() if isinstance(field, dict) and field.get("advanced", False)]
            for key, field in regular + advanced:
                option_id, option = self._build_setting_option(provider, config_id, key, field, is_extra=True)
                options[option_id] = option
        return options

    def get_settings_option_id(self, provider_id: str, key: str) -> Optional[str]:
        """Return generated Settings option ID for a provider key."""
        provider = self.get(provider_id)
        if provider is None or not hasattr(provider, "get_config_id"):
            return None
        config_id = provider.get_config_id()
        path = key if key in ("api_key", "api_base") or key.startswith("extra.") else f"extra.{key}"
        return f"provider.{config_id}.{path}"
