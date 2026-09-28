#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : RheagalFire                          #
# Updated Date: 2026.09.28 14:10:00                  #
# ================================================== #

from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict


if TYPE_CHECKING:
    from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM

from pygpt_net.core.types import MODE_LLAMA_INDEX
from pygpt_net.item.model import ModelItem
from pygpt_net.provider.llms.base import BaseLLM




__all__ = ["LiteLLMProvider", "LiteLLMIndex"]

class LiteLLMProvider(BaseLLM):
    """PyGPT LLM provider that routes to 100+ providers via LiteLLM."""

    def __init__(self, *args, **kwargs):
        super(LiteLLMProvider, self).__init__(*args, **kwargs)
        self.id = "litellm"
        self.name = "LiteLLM"
        self.type = [MODE_LLAMA_INDEX]

    def setup(self) -> dict:
        return {"require_api_key": False, "settings": {
            "api_key": {"type": "str", "default": "", "secret": True},
            "api_base": {"type": "str", "default": ""},
        }}

    def llama(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ) -> LlamaBaseLLM:
        """
        Return LLM provider instance for llama

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: LLM provider instance
        """
        from .index import LiteLLMIndex

        # LiteLLM resolves provider credentials from its own environment when
        # no explicit override is configured. Do not inherit OpenAI credentials.
        args = self.parse_args(model.llama_index or {}, window)
        model_name = args.pop("model", model.id)
        # The model's output capacity and the app limit are independent caps.
        # Zero means that a particular cap is disabled.
        configured_limit = args.pop("max_tokens", None)
        if configured_limit is None and "max_completion_tokens" not in args:
            model_limit = int(getattr(model, "tokens", 0) or 0)
            app_limit = int(window.core.config.get("max_output_tokens") or 0)
            limits = [limit for limit in (model_limit, app_limit) if limit > 0]
            configured_limit = min(limits) if limits else None
        max_tokens = int(configured_limit or 0) or None
        # Sampling is optional: reasoning models often reject temperature.
        temperature = args.pop("temperature", None)
        client_args = window.core.models.prepare_client_args(MODE_LLAMA_INDEX, model)
        api_key = args.pop("api_key", None) or client_args.get("api_key")
        api_base = args.pop("api_base", None) or client_args.get("base_url")
        # The model capability flag gates reasoning, including manual overrides.
        reasoning_effort_override = args.pop("reasoning_effort", None)
        reasoning_effort = window.core.models.get_reasoning_effort(model)
        if not getattr(model, "reasoning_effort", False):
            reasoning_effort_override = None
        constructor_args = {
            "model_name": model_name,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "context_window": int(getattr(model, "ctx", 0) or 0) or None,
            "api_key": api_key or None,
            "api_base": api_base or None,
            "reasoning_effort": reasoning_effort_override or reasoning_effort,
            "completion_kwargs": args,
        }
        self.log_llama_create(window, model, constructor_args, "LiteLLMIndex")
        return LiteLLMIndex(**constructor_args)

    def get_models(
            self,
            window,
    ) -> List[Dict]:
        """
        Return text LLM models known by the installed LiteLLM package.

        LiteLLM is a routing library rather than an OpenAI-compatible model
        endpoint.  Do not use ``BaseLLM.get_models()`` here, because that
        implementation queries an OpenAI-compatible ``/models`` endpoint and
        therefore returns the OpenAI model list for this provider.

        :param window: window instance
        :return: list of LiteLLM models
        """
        items: List[Dict] = []
        try:
            import litellm

            model_cost = getattr(litellm, "model_cost", {}) or {}
            model_ids = list(getattr(litellm, "model_list", []) or [])

            # Compatibility fallback for LiteLLM versions where model_list is
            # absent or empty.  Keep this local/lazy so importing the PyGPT
            # provider itself does not eagerly import LiteLLM at startup.
            if not model_ids:
                models_by_provider = getattr(litellm, "models_by_provider", {}) or {}
                if isinstance(models_by_provider, dict):
                    for provider_models in models_by_provider.values():
                        if isinstance(provider_models, (list, tuple, set)):
                            model_ids.extend(provider_models)

            seen = set()
            for value in model_ids:
                model_id = str(value).strip()
                if not model_id or model_id in seen:
                    continue

                # The PyGPT model importer creates text/chat model entries.
                # LiteLLM's registry also contains embeddings, image, audio,
                # rerank, moderation, etc.; do not expose those here.
                info = model_cost.get(model_id, {}) if isinstance(model_cost, dict) else {}
                mode = info.get("mode") if isinstance(info, dict) else None
                if mode and mode not in {"chat", "completion", "responses"}:
                    continue

                seen.add(model_id)
                items.append({
                    "id": model_id,
                    "name": model_id,
                })
        except Exception as e:
            window.core.debug.log(e)

        return items

def __getattr__(name):
    # Backward-compatible lazy export; the LlamaIndex adapter is loaded only
    # when callers explicitly request it.
    if name == "LiteLLMIndex":
        from .index import LiteLLMIndex
        return LiteLLMIndex
    raise AttributeError(name)
