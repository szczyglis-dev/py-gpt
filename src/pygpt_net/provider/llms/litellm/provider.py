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

        args = self.prepare_openai_compatible_args(window, model)
        model_name = args.pop("model", model.id)
        temperature = float(args.pop("temperature", 0.7))
        max_tokens = int(args.pop("max_tokens", 1024))
        api_key = args.pop("api_key", "")
        api_base = args.pop("api_base", "")
        reasoning_effort = window.core.models.get_reasoning_effort(model)
        constructor_args = {
            "model_name": model_name,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "api_key": api_key or None,
            "api_base": api_base or None,
            "reasoning_effort": reasoning_effort,
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

