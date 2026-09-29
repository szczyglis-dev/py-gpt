#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : RheagalFire                          #
# Updated Date: 2026.09.29 13:00:00                  #
# ================================================== #

from __future__ import annotations
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from llama_index.core.base.embeddings.base import BaseEmbedding
    from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM

from pygpt_net.core.types import MODE_EMBEDDINGS, MODE_LLAMA_INDEX
from pygpt_net.item.model import ModelItem
from pygpt_net.provider.llms.base import BaseLLM


__all__ = ["LiteLLMProvider", "LiteLLMIndex"]


class LiteLLMProvider(BaseLLM):
    """PyGPT provider backed by the native LlamaIndex LiteLLM integration."""

    def __init__(self, *args, **kwargs):
        super(LiteLLMProvider, self).__init__(*args, **kwargs)
        self.id = "litellm"
        self.name = "LiteLLM"
        self.type = [MODE_LLAMA_INDEX, MODE_EMBEDDINGS]

    def setup(self) -> dict:
        return {
            "require_api_key": False,
            "settings": {
                "api_key": {"type": "str", "default": "", "secret": True},
                "api_base": {"type": "str", "default": ""},
            },
        }

    @staticmethod
    def _positive_int(value: Any) -> int | None:
        try:
            value = int(value or 0)
        except (TypeError, ValueError):
            return None
        return value if value > 0 else None

    def _get_max_tokens(self, window, model: ModelItem, args: Dict[str, Any]) -> int | None:
        """Return the effective output cap while preserving explicit overrides."""
        configured = args.pop("max_tokens", None)
        if configured is not None:
            return self._positive_int(configured)

        # ``max_completion_tokens`` is a provider-specific LiteLLM kwarg.  When
        # it is explicitly configured, do not also synthesize ``max_tokens``.
        if "max_completion_tokens" in args:
            return None

        model_limit = self._positive_int(getattr(model, "tokens", 0))
        app_limit = self._positive_int(window.core.config.get("max_output_tokens"))
        limits = [value for value in (model_limit, app_limit) if value is not None]
        return min(limits) if limits else None

    def llama(
            self,
            window,
            model: ModelItem,
            stream: bool = False,
    ) -> LlamaBaseLLM:
        """Return the native ``llama_index.llms.litellm.LiteLLM`` adapter.

        PyGPT remains the source of model ID, credentials, endpoint and
        reasoning effort.  LlamaIndex/LiteLLM owns message conversion,
        multimodal blocks, streaming, retries and function/tool calling.
        """
        from .index import LiteLLMIndex

        args = self.parse_args(model.llama_index or {}, window)
        model_name = args.pop("model", model.id)
        max_tokens = self._get_max_tokens(window, model, args)

        client_args = window.core.models.prepare_client_args(MODE_LLAMA_INDEX, model)
        api_key = args.pop("api_key", None) or client_args.get("api_key") or None
        api_base = args.pop("api_base", None) or client_args.get("base_url") or None
        api_type = args.pop("api_type", None)

        # Constructor-owned options must not be forwarded again as completion
        # kwargs.  Leave temperature unspecified when PyGPT/model config does
        # not provide one so the integration can use its own default.
        temperature = args.pop("temperature", None)
        # Streaming is selected by the LlamaIndex method (stream_chat /
        # stream_complete); keeping it in additional_kwargs would duplicate the
        # keyword used internally by the native adapter.
        args.pop("stream", None)
        max_retries = args.pop("max_retries", None)
        custom_llm_provider = args.pop("custom_llm_provider", None)
        additional_kwargs = args.pop("additional_kwargs", None)
        if not isinstance(additional_kwargs, dict):
            additional_kwargs = {}
        else:
            additional_kwargs = dict(additional_kwargs)

        # Everything else from model -> LlamaIndex args is a LiteLLM completion
        # kwarg (top_p, seed, timeout, max_completion_tokens, thinking, etc.).
        additional_kwargs.update(args)
        additional_kwargs.setdefault("drop_params", True)

        # Reasoning remains controlled by PyGPT.  Keep an explicit per-model
        # override compatible with the old provider, but only for models marked
        # as supporting reasoning in PyGPT.
        reasoning_override = additional_kwargs.pop("reasoning_effort", None)
        reasoning_effort = window.core.models.get_reasoning_effort(model)
        if getattr(model, "reasoning_effort", False):
            reasoning_effort = reasoning_override or reasoning_effort
            if reasoning_effort:
                additional_kwargs["reasoning_effort"] = reasoning_effort

        constructor_args: Dict[str, Any] = {
            "model": model_name,
            "additional_kwargs": additional_kwargs,
            "pygpt_context_window": self._positive_int(getattr(model, "ctx", 0)),
            "pygpt_tool_calls": bool(getattr(model, "tool_calls", False)),
        }
        if temperature is not None:
            constructor_args["temperature"] = temperature
        if max_tokens is not None:
            constructor_args["max_tokens"] = max_tokens
        if max_retries is not None:
            constructor_args["max_retries"] = max_retries
        if api_key:
            constructor_args["api_key"] = api_key
        if api_base:
            constructor_args["api_base"] = api_base
        if api_type:
            constructor_args["api_type"] = api_type
        if custom_llm_provider:
            # llama-index-llms-litellm 0.7.1 uses this both for routing and for
            # function-calling capability detection.
            constructor_args["custom_llm_provider"] = custom_llm_provider

        self.log_llama_create(
            window,
            model,
            constructor_args,
            "llama_index.llms.litellm.LiteLLM",
        )
        return LiteLLMIndex(**constructor_args)

    def get_embeddings_model(
            self,
            window,
            config: Optional[List[Dict]] = None,
    ) -> "BaseEmbedding":
        """Return the native LlamaIndex LiteLLM embeddings adapter.

        The embedding model is selected by PyGPT's global/default embedding
        configuration, while credentials and endpoint fall back to the LiteLLM
        provider settings.  LiteLLM routing remains available through the model
        name (for example ``openai/text-embedding-3-small`` or a proxy alias).
        """
        from llama_index.embeddings.litellm import LiteLLMEmbedding

        args = self.prepare_openai_compatible_embedding_args(window, config)

        # The native integration accepts ``model_name`` rather than ``model``.
        # ``prepare_openai_compatible_embedding_args`` also resolves the
        # provider-global API key/base URL and keeps explicit embedding args as
        # overrides.  Do not pass empty values to LiteLLM -- an empty api_base
        # is not equivalent to an omitted endpoint for all routed providers.
        if not args.get("api_key"):
            args.pop("api_key", None)
        if not args.get("api_base"):
            args.pop("api_base", None)

        if not args.get("timeout"):
            args["timeout"] = int(self.get_embeddings_timeout(window.core.config))

        self.log_llama_create(
            window,
            None,
            args,
            "llama_index.embeddings.litellm.LiteLLMEmbedding",
            kind="embeddings",
        )
        return LiteLLMEmbedding(**args)

    def get_models(self, window) -> List[Dict]:
        """Return text/chat models known by the installed LiteLLM package."""
        items: List[Dict] = []
        try:
            import litellm

            model_cost = getattr(litellm, "model_cost", {}) or {}
            model_ids = list(getattr(litellm, "model_list", []) or [])

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

                info = model_cost.get(model_id, {}) if isinstance(model_cost, dict) else {}
                mode = info.get("mode") if isinstance(info, dict) else None
                if mode and mode not in {"chat", "completion", "responses"}:
                    continue

                seen.add(model_id)
                item: Dict[str, Any] = {
                    "id": model_id,
                    "name": model_id,
                    "input": ["text"],
                }

                if isinstance(info, dict):
                    if info.get("supports_vision") is True:
                        item["input"].append("image")
                    if info.get("supports_function_calling") is not None:
                        item["tool_calls"] = bool(info.get("supports_function_calling"))
                    if info.get("supports_reasoning") is not None:
                        item["reasoning_effort"] = bool(info.get("supports_reasoning"))

                    ctx = self._positive_int(
                        info.get("max_input_tokens") or info.get("max_tokens")
                    )
                    tokens = self._positive_int(info.get("max_output_tokens"))
                    if ctx is not None:
                        item["ctx"] = ctx
                    if tokens is not None:
                        item["tokens"] = tokens

                # Some LiteLLM registries omit capability fields in model_cost.
                # Ask its capability helper as a fallback; failure simply leaves
                # PyGPT's conservative default in place.
                if "tool_calls" not in item:
                    try:
                        item["tool_calls"] = bool(
                            litellm.supports_function_calling(model_id)
                        )
                    except Exception:
                        pass

                items.append(item)
        except Exception as e:
            window.core.debug.log(e)

        return items


def __getattr__(name):
    # Backward-compatible lazy export. ``LiteLLMIndex`` is now only a thin
    # metadata subclass of the official LlamaIndex LiteLLM integration.
    if name == "LiteLLMIndex":
        from .index import LiteLLMIndex
        return LiteLLMIndex
    raise AttributeError(name)
