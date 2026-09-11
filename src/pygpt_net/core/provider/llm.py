#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.11 14:00:00                  #
# ================================================== #

from importlib import import_module
from typing import Any


class LlamaIndexLLMProxy:
    """Runtime compatibility proxy for stale LlamaIndex model registries.

    LlamaIndex integrations sometimes keep a hard-coded list of provider model
    IDs. A freshly released model can therefore be accepted by the provider API
    while an older installed ``llama-index-llms-*`` package rejects it locally.

    The proxy does not replace a provider adapter and does not alter request
    payloads. It only teaches the installed native LlamaIndex integration about
    a model already configured in PyGPT, using PyGPT's model metadata. This keeps
    the original transport (including OpenAI Responses), tools and reasoning
    behavior intact.
    """

    _anthropic_function_calling_models = set()

    SUPPORTED_PROVIDERS = {
        "openai",
        "google",
        "x_ai",
        "anthropic",
    }

    def __init__(self, window=None):
        self.window = window
        self._warned = set()

    def prepare(self, model) -> bool:
        """Register a configured model in a stale native LlamaIndex registry.

        Returns ``True`` only when a native registry was extended. Providers
        which do not use a static model registry in their current integration
        are intentionally left untouched.
        """
        if model is None:
            return False

        provider = self._provider_id(model)
        if provider not in self.SUPPORTED_PROVIDERS:
            return False

        model_name = self._model_name(model)
        if not model_name:
            return False

        patched = False
        if provider == "openai":
            patched = self._prepare_openai(model, model_name)
        elif provider == "anthropic":
            patched = self._prepare_anthropic(model, model_name)
        elif provider == "google":
            patched = self._prepare_google(model, model_name)
        elif provider == "x_ai":
            patched = self._prepare_xai(model, model_name)

        if patched:
            self._warn(provider, model_name)
        return patched

    @staticmethod
    def _provider_id(model) -> str:
        getter = getattr(model, "get_provider", None)
        if callable(getter):
            return str(getter() or "")
        return str(getattr(model, "provider", "") or "")

    @staticmethod
    def _model_name(model) -> str:
        """Return the exact LlamaIndex model ID configured for a PyGPT model."""
        options = getattr(model, "llama_index", None) or {}
        args = options.get("args") if isinstance(options, dict) else None

        if isinstance(args, dict):
            value = args.get("model")
            if value:
                return str(value).strip()
        elif isinstance(args, list):
            for item in args:
                if not isinstance(item, dict):
                    continue
                if item.get("name") != "model":
                    continue
                value = item.get("value")
                if value:
                    return str(value).strip()

        return str(getattr(model, "id", "") or "").strip()

    @staticmethod
    def _context_window(model, default: int) -> int:
        try:
            value = int(getattr(model, "ctx", 0) or 0)
        except (TypeError, ValueError):
            value = 0
        return value if value > 0 else default

    @staticmethod
    def _has_chat_mode(model) -> bool:
        has_mode = getattr(model, "has_mode", None)
        if callable(has_mode):
            try:
                return bool(has_mode("chat"))
            except Exception:
                pass
        modes = getattr(model, "mode", None) or []
        return "chat" in modes

    @staticmethod
    def _is_reasoning_model(model, model_name: str) -> bool:
        extra = getattr(model, "extra", None) or {}
        if isinstance(extra, dict) and extra.get("reasoning_effort") is not None:
            return True

        name = str(model_name or "").lower()
        if name.startswith(("o1", "o3", "o4", "o5")):
            return True

        if not name.startswith("gpt-"):
            return False
        version = name[4:].split("-", 1)[0].split(".", 1)[0]
        try:
            return int(version) >= 5
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _registry_contains(module: Any, name: str, model_name: str) -> bool:
        registry = getattr(module, name, None)
        try:
            return model_name in registry
        except TypeError:
            return False

    @staticmethod
    def _registry_add(
            module: Any,
            name: str,
            model_name: str,
            context_window: int,
    ) -> bool:
        """Add a model to a dict/set/list registry without replacing the object.

        LlamaIndex modules often import these registries by reference, therefore
        mutating the existing container also updates already-imported native LLM
        classes. Replacing the module attribute would not be as reliable.
        """
        registry = getattr(module, name, None)
        if isinstance(registry, dict):
            if model_name in registry:
                return False
            registry[model_name] = context_window
            return True
        if isinstance(registry, set):
            if model_name in registry:
                return False
            registry.add(model_name)
            return True
        if isinstance(registry, list):
            if model_name in registry:
                return False
            registry.append(model_name)
            return True
        return False

    def _prepare_openai(self, model, model_name: str) -> bool:
        try:
            utils = import_module("llama_index.llms.openai.utils")
        except (ImportError, ModuleNotFoundError):
            return False

        # ALL_AVAILABLE_MODELS is the source of the "Unknown model" exception
        # in llama-index-llms-openai. If it already contains the model there is
        # nothing to proxy.
        if self._registry_contains(utils, "ALL_AVAILABLE_MODELS", model_name):
            return False

        context_window = self._context_window(model, 128000)
        patched = self._registry_add(
            utils,
            "ALL_AVAILABLE_MODELS",
            model_name,
            context_window,
        )
        if not patched:
            return False

        if self._has_chat_mode(model):
            self._registry_add(utils, "CHAT_MODELS", model_name, context_window)

        if self._is_reasoning_model(model, model_name):
            # Different llama-index-llms-openai releases use different names for
            # the reasoning-model registry. Mutate whichever registry exists.
            for registry_name in (
                    "O1_MODELS",
                    "OPENAI_REASONING_MODELS",
                    "REASONING_MODELS",
            ):
                self._registry_add(
                    utils,
                    registry_name,
                    model_name,
                    context_window,
                )

        return True

    def _prepare_anthropic(self, model, model_name: str) -> bool:
        try:
            utils = import_module("llama_index.llms.anthropic.utils")
        except (ImportError, ModuleNotFoundError):
            return False

        if self._registry_contains(utils, "CLAUDE_MODELS", model_name):
            return False

        context_window = self._context_window(model, 200000)
        patched = self._registry_add(
            utils,
            "CLAUDE_MODELS",
            model_name,
            context_window,
        )
        if not patched:
            return False

        # CLAUDE_MODELS is normally built from ANTHROPIC_MODELS + Vertex/Bedrock
        # registries. Keep the provider-specific table in sync when it exists.
        self._registry_add(
            utils,
            "ANTHROPIC_MODELS",
            model_name,
            context_window,
        )

        if bool(getattr(model, "tool_calls", False)):
            self._anthropic_function_calling_models.add(model_name)
            self._install_anthropic_function_calling_proxy(utils)
        return True

    @classmethod
    def _install_anthropic_function_calling_proxy(cls, utils) -> None:
        """Extend Anthropic's generation-based tool capability check at runtime."""
        marker = "_pygpt_function_calling_proxy"
        if getattr(utils, marker, False):
            return

        original = getattr(utils, "is_function_calling_model", None)
        if not callable(original):
            return

        def is_function_calling_model(model_name: str) -> bool:
            if model_name in cls._anthropic_function_calling_models:
                return True
            return bool(original(model_name))

        utils.is_function_calling_model = is_function_calling_model
        setattr(utils, marker, True)

        # Anthropic.base imports this helper directly, so replace that local
        # binding too when the module is already available/importable.
        try:
            base = import_module("llama_index.llms.anthropic.base")
            base.is_function_calling_model = is_function_calling_model
        except (ImportError, ModuleNotFoundError):
            pass

    @staticmethod
    def _prepare_google(model, model_name: str) -> bool:
        """GoogleGenAI gets model metadata from the live Google API.

        Current ``llama-index-llms-google-genai`` does not gate model IDs through
        a static known-model table, so changing it would only risk breaking the
        native adapter. Keep the provider on its native path.
        """
        return False

    @staticmethod
    def _prepare_xai(model, model_name: str) -> bool:
        """xAI already uses explicit metadata/OpenAI-compatible adapters in PyGPT.

        There is no xAI model-name registry to bypass in the current path. In
        particular, xAI Responses receives ``context_window`` from PyGPT.
        """
        return False

    def _warn(self, provider: str, model_name: str) -> None:
        key = (provider, model_name)
        if key in self._warned:
            return
        self._warned.add(key)
        print(
            "WARNING: Model '{}' is not recognized by the native LlamaIndex "
            "provider '{}'. Using PyGPT model registry proxy fallback.".format(
                model_name,
                provider,
            )
        )
