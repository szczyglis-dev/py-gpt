#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# ================================================== #

import copy

from packaging.version import parse as parse_version, Version

from pygpt_net.core.types import MODE_AGENT_LLAMA, MODE_AGENT_OPENAI


# Legacy provider settings removed from the fresh config.json in 2.8.33.
# The defaults are kept here solely so migrations from older profiles do not
# depend on keys that no longer exist in the base config file.
LEGACY_DEFAULTS = {
    "api_key": "",
    "organization_key": "",
    "api_endpoint": "https://api.openai.com/v1",
    "api_use_responses": True,
    "api_use_responses_llama": True,
    "api_key_google": "",
    "api_endpoint_google": "https://generativelanguage.googleapis.com/v1beta/openai",
    "api_native_google": True,
    "api_native_google.use_vertex": False,
    "api_native_google.cloud_project": "",
    "api_native_google.cloud_location": "us-central1",
    "api_native_google.app_credentials": "",
    "api_key_anthropic": "",
    "api_endpoint_anthropic": "https://api.anthropic.com/v1",
    "api_native_anthropic": True,
    "api_key_hugging_face": "",
    "api_endpoint_hugging_face": "https://router.huggingface.co/v1",
    "api_key_deepseek": "",
    "api_endpoint_deepseek": "https://api.deepseek.com/v1",
    "api_key_xai": "",
    "api_key_management_xai": "",
    "api_endpoint_xai": "https://api.x.ai/v1",
    "api_native_xai": True,
    "api_azure_endpoint": "https://<your-resource-name>.openai.azure.com/",
    "api_azure_version": "2023-07-01-preview",
    "api_key_perplexity": "",
    "api_endpoint_perplexity": "https://api.perplexity.ai",
    "api_key_mistral": "",
    "api_endpoint_mistral": "https://api.mistral.ai/v1",
    "api_key_voyage": "",
    "api_key_open_router": "",
    "api_endpoint_open_router": "https://openrouter.ai/api/v1",
    "api_key_forge": "",
    "api_endpoint_forge": "https://api.forge.tensorblock.co/v1",
    "api_key_edenai": "",
    "api_endpoint_edenai": "https://api.edenai.run/v3",
    "api_key_jev": "",
    "api_endpoint_jev": "https://api.typesafe.ai",
}

# old key -> one or more (provider config id, path)
LEGACY_PROVIDER_MAP = {
    "api_key": [("openai", "api_key"), ("azure_openai", "api_key")],
    "organization_key": [("openai", "extra.organization")],
    "api_endpoint": [("openai", "api_base")],
    "api_use_responses": [("openai", "extra.responses_api")],
    "api_use_responses_llama": [("openai", "extra.responses_api_llama")],
    "api_key_google": [("google", "api_key")],
    "api_endpoint_google": [("google", "api_base")],
    "api_native_google": [("google", "extra.native")],
    "api_native_google.use_vertex": [("google", "extra.use_vertex")],
    "api_native_google.cloud_project": [("google", "extra.cloud_project")],
    "api_native_google.cloud_location": [("google", "extra.cloud_location")],
    "api_native_google.app_credentials": [("google", "extra.app_credentials")],
    "api_key_anthropic": [("anthropic", "api_key")],
    "api_endpoint_anthropic": [("anthropic", "api_base")],
    "api_native_anthropic": [("anthropic", "extra.native")],
    "api_key_hugging_face": [("huggingface", "api_key")],
    "api_endpoint_hugging_face": [("huggingface", "api_base")],
    "api_key_deepseek": [("deepseek_api", "api_key")],
    "api_endpoint_deepseek": [("deepseek_api", "api_base")],
    "api_key_xai": [("x_ai", "api_key")],
    "api_key_management_xai": [("x_ai", "extra.management_api_key")],
    "api_endpoint_xai": [("x_ai", "api_base")],
    "api_native_xai": [("x_ai", "extra.native")],
    "api_native_xai.proxy": [("x_ai", "extra.proxy")],
    "api_native_xai.timeout": [("x_ai", "extra.timeout")],
    "api_azure_endpoint": [("azure_openai", "api_base")],
    "api_azure_version": [("azure_openai", "extra.api_version")],
    "api_key_perplexity": [("perplexity", "api_key")],
    "api_endpoint_perplexity": [("perplexity", "api_base")],
    "api_key_mistral": [("mistral_ai", "api_key")],
    "api_endpoint_mistral": [("mistral_ai", "api_base")],
    "api_key_voyage": [("voyage", "api_key")],
    "api_native_voyage.max_retries": [("voyage", "extra.max_retries")],
    "api_key_open_router": [("open_router", "api_key")],
    "api_endpoint_open_router": [("open_router", "api_base")],
    "api_key_forge": [("forge", "api_key")],
    "api_endpoint_forge": [("forge", "api_base")],
    "api_key_edenai": [("edenai", "api_key")],
    "api_endpoint_edenai": [("edenai", "api_base")],
    "api_key_jev": [("jev", "api_key")],
    "api_endpoint_jev": [("jev", "api_base")],
    "api_native_hf.proxy": [("huggingface", "extra.proxy")],
    "api_native_hf.trust_env": [("huggingface", "extra.trust_env")],
}

PLACEHOLDER_MAP = {
    "{api_key}": "{providers[openai][api_key]}",
    "{organization_key}": "{providers[openai][extra][organization]}",
    "{api_endpoint}": "{providers[openai][api_base]}",
    "{api_use_responses}": "{providers[openai][extra][responses_api]}",
    "{api_use_responses_llama}": "{providers[openai][extra][responses_api_llama]}",
    "{api_key_google}": "{providers[google][api_key]}",
    "{api_endpoint_google}": "{providers[google][api_base]}",
    "{api_key_anthropic}": "{providers[anthropic][api_key]}",
    "{api_endpoint_anthropic}": "{providers[anthropic][api_base]}",
    "{api_key_hugging_face}": "{providers[huggingface][api_key]}",
    "{api_endpoint_hugging_face}": "{providers[huggingface][api_base]}",
    "{api_key_deepseek}": "{providers[deepseek_api][api_key]}",
    "{api_endpoint_deepseek}": "{providers[deepseek_api][api_base]}",
    "{api_key_xai}": "{providers[x_ai][api_key]}",
    "{api_endpoint_xai}": "{providers[x_ai][api_base]}",
    "{api_azure_endpoint}": "{providers[azure_openai][api_base]}",
    "{api_azure_version}": "{providers[azure_openai][extra][api_version]}",
    "{api_key_perplexity}": "{providers[perplexity][api_key]}",
    "{api_endpoint_perplexity}": "{providers[perplexity][api_base]}",
    "{api_key_mistral}": "{providers[mistral_ai][api_key]}",
    "{api_endpoint_mistral}": "{providers[mistral_ai][api_base]}",
    "{api_key_voyage}": "{providers[voyage][api_key]}",
    "{api_key_open_router}": "{providers[open_router][api_key]}",
    "{api_endpoint_open_router}": "{providers[open_router][api_base]}",
    "{api_key_forge}": "{providers[forge][api_key]}",
    "{api_endpoint_forge}": "{providers[forge][api_base]}",
    "{api_key_edenai}": "{providers[edenai][api_key]}",
    "{api_endpoint_edenai}": "{providers[edenai][api_base]}",
    "{api_key_jev}": "{providers[jev][api_key]}",
    "{api_endpoint_jev}": "{providers[jev][api_base]}",
}


def rewrite_placeholders(value):
    """Recursively rewrite legacy config placeholders."""
    if isinstance(value, str):
        for old, new in PLACEHOLDER_MAP.items():
            value = value.replace(old, new)
        return value
    if isinstance(value, list):
        return [rewrite_placeholders(item) for item in value]
    if isinstance(value, dict):
        return {key: rewrite_placeholders(item) for key, item in value.items()}
    return value


def _has_path(provider: dict, path: str) -> bool:
    if path in ("api_key", "api_base"):
        return path in provider
    key = path[6:] if path.startswith("extra.") else path
    extra = provider.get("extra")
    return isinstance(extra, dict) and key in extra


def _set_path(provider: dict, path: str, value):
    if path in ("api_key", "api_base"):
        provider[path] = copy.deepcopy(value)
        return
    key = path[6:] if path.startswith("extra.") else path
    extra = provider.setdefault("extra", {})
    if not isinstance(extra, dict):
        extra = {}
        provider["extra"] = extra
    extra[key] = copy.deepcopy(value)


class Patch:
    def __init__(self, window=None):
        self.window = window

    def execute(self, version: Version):
        """Migrate flat provider API settings to config.providers for 2.8.33."""
        data = self.window.core.config.all()
        current = "0.0.0"
        if isinstance(data.get("__meta__"), dict):
            current = data["__meta__"].get("version", current)
        old = parse_version(current)
        if old >= parse_version("2.8.33") or old >= version:
            return data, False, False

        print("Migrating config from < 2.8.33...")
        updated = False

        # OpenAI Agents remains available internally for loading old data, but
        # it is no longer a user-selectable work mode. Persist the supported
        # LlamaIndex-backed Custom agents mode for profiles that had it active.
        if data.get("mode") == MODE_AGENT_OPENAI:
            data["mode"] = MODE_AGENT_LLAMA
            updated = True
        providers = data.get("providers")
        if not isinstance(providers, dict):
            providers = {}
            data["providers"] = providers
            updated = True

        for legacy_key, targets in LEGACY_PROVIDER_MAP.items():
            existed = legacy_key in data
            if existed:
                value = data.get(legacy_key)
            elif legacy_key in LEGACY_DEFAULTS:
                value = copy.deepcopy(LEGACY_DEFAULTS[legacy_key])
            else:
                continue

            for provider_id, path in targets:
                provider = providers.get(provider_id)
                if not isinstance(provider, dict):
                    provider = {}
                    providers[provider_id] = provider
                    updated = True
                if not _has_path(provider, path):
                    _set_path(provider, path, value)
                    updated = True

            # Remove only provider legacy settings. Global API infrastructure
            # keys such as api_proxy and api_custom_providers stay top-level.
            if existed:
                del data[legacy_key]
                updated = True

        # Rewrite formatter placeholders only in config surfaces that are used
        # to build runtime/LlamaIndex arguments. Avoid touching arbitrary user
        # strings such as prompts that may legitimately contain ``{api_key}``.
        for key in list(data.keys()):
            if key == "app.env" or key.startswith("llama."):
                value = data.get(key)
                rewritten = rewrite_placeholders(value)
                if rewritten != value:
                    data[key] = rewritten
                    updated = True

        return data, updated, True
