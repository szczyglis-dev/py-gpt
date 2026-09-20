#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.13 09:20:00                  #
# ================================================== #

"""Runtime reasoning-effort capabilities.

The provider table is intentionally separate from the model catalog.  A model
must opt in with ``ModelItem.reasoning_effort`` before the runtime selector is
shown.  Known bundled models additionally get a model-specific list so the UI
never offers a value which the provider documents as unsupported for that
model.  Custom models that explicitly opt in fall back to their provider list.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


REASONING_EFFORT_ORDER: Tuple[str, ...] = (
    "none",
    "minimal",
    "low",
    "medium",
    "high",
    "xhigh",
    "max",
)

# Provider/API-level vocabulary.  Empty lists are deliberate: those adapters do
# not currently expose a portable reasoning-effort control in PyGPT.
PROVIDER_REASONING_EFFORTS: Dict[str, Tuple[str, ...]] = {
    "openai": ("none", "minimal", "low", "medium", "high", "xhigh", "max"),
    "azure_openai": ("none", "minimal", "low", "medium", "high", "xhigh", "max"),
    "anthropic": ("low", "medium", "high", "xhigh", "max"),
    "google": ("minimal", "low", "medium", "high"),
    "x_ai": ("none", "low", "medium", "high"),
    "deepseek_api": ("low", "high", "max"),
    "perplexity": ("low", "medium", "high"),
    "huggingface_router": ("low", "medium", "high"),
    "ollama": ("low", "medium", "high"),
    "open_router": ("none", "minimal", "low", "medium", "high", "xhigh", "max"),
    # LiteLLM uses one OpenAI-shaped parameter and translates/drops it per
    # downstream provider.  Per-model support is still gated by the model's
    # explicit reasoning_effort flag.
    "litellm": ("none", "minimal", "low", "medium", "high", "xhigh", "max"),
    # Providers below currently have no portable runtime effort knob in their
    # PyGPT adapters.  Keeping them explicit makes the capability table total
    # for all built-in LLM provider IDs.
    "huggingface": (),
    "huggingface_api": (),
    "local_ai": (),
    "mistral_ai": (),
    "forge": (),
    "edenai": (),
}

# Exact model/API capabilities used for the bundled catalog.  Unknown custom
# models can still be enabled manually and will use the provider-level list.
MODEL_REASONING_EFFORTS: Dict[Tuple[str, str], Tuple[str, ...]] = {
    # OpenAI
    ("openai", "gpt-5.6-luna"): ("none", "low", "medium", "high", "xhigh", "max"),
    ("openai", "gpt-5.6-sol"): ("none", "low", "medium", "high", "xhigh", "max"),
    ("openai", "gpt-5.6-terra"): ("none", "low", "medium", "high", "xhigh", "max"),
    ("openai", "gpt-5.3-codex"): ("low", "medium", "high", "xhigh"),
    ("openai", "gpt-6-astra"): ("low", "medium", "high", "xhigh", "max"),
    ("openai", "o1"): ("low", "medium", "high"),
    ("openai", "o3"): ("low", "medium", "high"),
    ("openai", "o3-mini"): ("low", "medium", "high"),
    ("openai", "o4-mini"): ("low", "medium", "high"),

    # Anthropic Claude API
    ("anthropic", "claude-fable-5"): ("low", "medium", "high", "xhigh", "max"),
    ("anthropic", "claude-fable-5-1"): ("low", "medium", "high", "xhigh", "max"),
    ("anthropic", "claude-opus-4-5"): ("low", "medium", "high"),
    ("anthropic", "claude-opus-5"): ("low", "medium", "high", "xhigh", "max"),
    ("anthropic", "claude-sonnet-5"): ("low", "medium", "high", "xhigh", "max"),
    ("anthropic", "claude-opus-4-6"): ("low", "medium", "high", "max"),
    ("anthropic", "claude-opus-4-7"): ("low", "medium", "high", "xhigh", "max"),
    ("anthropic", "claude-opus-4-8"): ("low", "medium", "high", "xhigh", "max"),
    ("anthropic", "claude-sonnet-4-6"): ("low", "medium", "high", "max"),

    # Google Gemini API
    ("google", "gemini-2.5-flash"): ("low", "medium", "high"),
    ("google", "gemini-2.5-flash-lite"): ("low", "medium", "high"),
    ("google", "gemini-2.5-pro"): ("low", "medium", "high"),
    ("google", "gemini-3-flash-preview"): ("minimal", "low", "medium", "high"),
    ("google", "gemini-3-pro-preview"): ("low", "high"),
    ("google", "gemini-3.1-pro-preview"): ("low", "medium", "high"),
    ("google", "gemini-3.1-flash-image"): ("minimal", "high"),
    ("google", "gemini-3.1-flash-lite-image"): ("minimal", "high"),
    ("google", "gemini-3.5-flash"): ("minimal", "low", "medium", "high"),
    ("google", "gemini-3.5-flash-lite"): ("minimal", "low", "medium", "high"),
    ("google", "gemini-3.6-flash"): ("minimal", "low", "medium", "high"),
    ("google", "gemini-3.7-flash"): ("low", "medium", "high"),
    ("google", "gemini-3.8-flash"): ("low", "medium", "high"),

    # xAI
    ("x_ai", "grok-4.3"): ("none", "low", "medium", "high"),
    ("x_ai", "grok-4.5"): ("low", "medium", "high"),
    ("x_ai", "grok-4.5-latest"): ("low", "medium", "high"),
    ("x_ai", "grok-4.6"): ("low", "medium", "high"),
    ("x_ai", "grok-4.6-latest"): ("low", "medium", "high"),

    # DeepSeek API
    ("deepseek_api", "deepseek-v4-flash"): ("low", "high", "max"),
    ("deepseek_api", "deepseek-v4-pro"): ("low", "high", "max"),

    # Hugging Face Inference Providers (OpenAI-compatible gpt-oss)
    ("huggingface_router", "openai/gpt-oss-120b:novita"): ("low", "medium", "high"),
    ("huggingface_router", "openai/gpt-oss-20b:novita"): ("low", "medium", "high"),

    # Ollama gpt-oss thinking levels
    ("ollama", "gpt-oss:120b"): ("low", "medium", "high"),
    ("ollama", "gpt-oss:20b"): ("low", "medium", "high"),

    # Perplexity Sonar
    ("perplexity", "sonar-deep-research"): ("low", "medium", "high"),
    ("perplexity", "sonar-reasoning"): ("low", "medium", "high"),
    ("perplexity", "sonar-reasoning-pro"): ("low", "medium", "high"),
}

# Legacy catalog keys encoded effort in the key while sharing one provider model
# ID, e.g. ``gpt-5.6-terra-high``.  Only these historical suffixes are migrated.
LEGACY_REASONING_SUFFIXES: Tuple[str, ...] = ("low", "medium", "high", "xhigh")
_LEGACY_SUFFIX_RE = re.compile(r"-(low|medium|high|xhigh)$", re.IGNORECASE)


def get_provider_efforts(provider: Optional[str]) -> List[str]:
    """Return the provider/API-level effort values in UI order."""
    return list(PROVIDER_REASONING_EFFORTS.get(str(provider or ""), ()))


def get_model_efforts(model: Any) -> List[str]:
    """Return valid runtime efforts for an opted-in model."""
    if model is None or not bool(getattr(model, "reasoning_effort", False)):
        return []

    provider = str(getattr(model, "provider", "") or "")
    model_id = str(getattr(model, "id", "") or "")
    provider_efforts = get_provider_efforts(provider)
    if not provider_efforts:
        return []

    model_efforts = MODEL_REASONING_EFFORTS.get((provider, model_id))
    if model_efforts is None:
        # Explicitly enabled custom models use their provider/API vocabulary.
        return provider_efforts

    allowed = set(model_efforts)
    return [effort for effort in provider_efforts if effort in allowed]


def get_google_thinking_kwargs(model_id: Optional[str], effort: Any) -> Dict[str, Any]:
    """Translate the common effort vocabulary to native Google GenAI fields."""
    value = normalize_effort(effort)
    if not value:
        return {}
    model_id = str(model_id or "").lower()
    if model_id.startswith("models/"):
        model_id = model_id[7:]
    if model_id.startswith("gemini-2.5"):
        # Gemini 2.5 GenerateContent uses token budgets rather than named
        # thinking levels. Map the runtime vocabulary to valid, monotonic
        # budgets; Pro has a larger documented upper bound than Flash.
        high_budget = 32768 if model_id.startswith("gemini-2.5-pro") else 24576
        budget_by_effort = {
            "minimal": 1024,
            "low": 1024,
            "medium": 8192,
            "high": high_budget,
        }
        budget = budget_by_effort.get(value)
        return {"thinking_budget": budget} if budget is not None else {}
    return {"thinking_level": value}


def legacy_key_parts(key: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Return ``(base_key, effort)`` for a legacy ``-<effort>`` model key."""
    value = str(key or "")
    match = _LEGACY_SUFFIX_RE.search(value)
    if not match:
        return None, None
    return value[:match.start()], match.group(1).lower()


def legacy_base_key(key: Optional[str]) -> Optional[str]:
    """Return the base key for a historical effort-suffixed model key."""
    return legacy_key_parts(key)[0]


def normalize_effort(value: Any) -> Optional[str]:
    """Normalize an effort value to the runtime vocabulary."""
    effort = str(value or "").strip().lower()
    return effort if effort in REASONING_EFFORT_ORDER else None


def choose_effort(value: Any, available: List[str]) -> Optional[str]:
    """Choose the closest valid effort without maintaining per-model state."""
    if not available:
        return None

    current = normalize_effort(value)
    if current in available:
        return current

    # Default to high when no valid global state exists, then choose the nearest
    # supported level on the common effort scale.
    target = current or "high"
    try:
        target_idx = REASONING_EFFORT_ORDER.index(target)
    except ValueError:
        target_idx = REASONING_EFFORT_ORDER.index("high")

    ranked = []
    for effort in available:
        try:
            idx = REASONING_EFFORT_ORDER.index(effort)
        except ValueError:
            continue
        # On equal distance prefer the lower effort to avoid accidentally
        # increasing compute/latency when switching providers.
        ranked.append((abs(idx - target_idx), idx > target_idx, idx, effort))

    if not ranked:
        return available[0]
    ranked.sort()
    return ranked[0][3]
