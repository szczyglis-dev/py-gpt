#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.16 11:50:00                  #
# ================================================== #

"""Forward-compatible model capability helpers.

Known legacy limitations should be handled explicitly by provider adapters.  The
helpers in this module are intentionally forward-only: once a provider family
has reached a capability baseline, later numeric generations are assumed to keep
that capability unless a provider-specific blacklist says otherwise.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple


def normalize_model_id(model_id) -> str:
    value = str(model_id or "").strip().lower()
    if value.startswith("models/"):
        value = value[7:]
    return value


def numeric_version(model_id, prefix: str) -> Optional[Tuple[int, int, int]]:
    """Return the numeric version immediately following *prefix*.

    Supports common provider IDs such as ``gpt-5.6-sol``, ``gemini-3.8-flash``,
    ``grok-4.6`` and ``deepseek-v4-pro``.  Missing minor/patch components are
    normalized to zero.
    """
    value = normalize_model_id(model_id)
    prefix = str(prefix or "").lower()
    if not value.startswith(prefix):
        return None
    tail = value[len(prefix):]
    match = re.match(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", tail)
    if not match:
        return None
    return tuple(int(part or 0) for part in match.groups(default="0"))


def version_at_least(model_id, prefix: str, minimum) -> bool:
    version = numeric_version(model_id, prefix)
    if version is None:
        return False
    minimum = tuple(int(v) for v in minimum)
    minimum = (minimum + (0, 0, 0))[:3]
    return version >= minimum


def _claude_version(model_id) -> Optional[Tuple[int, int, int]]:
    """Extract the generation suffix from Claude family IDs.

    Examples: claude-opus-4-8 -> (4, 8, 0), claude-fable-5-1 -> (5, 1, 0).
    Date suffixes are ignored because the first numeric token is the generation.
    """
    value = normalize_model_id(model_id)
    if not value.startswith("claude-"):
        return None
    match = re.search(r"-(\d+)(?:-(\d+))?(?:-(\d+))?(?:-|$)", value)
    if not match:
        return None
    return tuple(int(part or 0) for part in match.groups(default="0"))


def is_openai_o_series(model_id) -> bool:
    value = normalize_model_id(model_id)
    return re.match(r"^o\d+(?:[-.]|$)", value) is not None


def is_openai_reasoning_model_id(model_id) -> bool:
    """Recognize present and future OpenAI reasoning families."""
    value = normalize_model_id(model_id)
    if is_openai_o_series(value):
        return True
    return version_at_least(value, "gpt-", (5, 0))


def supports_future_computer_mode(provider: str, model_id) -> bool:
    """Infer Computer Use only at/after the newest capability baselines."""
    provider = str(provider or "").lower()
    value = normalize_model_id(model_id)

    if provider in ("openai", "azure_openai"):
        return value.startswith("computer-use") or version_at_least(value, "gpt-", (5, 6))

    if provider == "google":
        known = {
            "gemini-3.8-flash",
            "gemini-3.7-flash",
            "gemini-3.5-flash-lite",
            "gemini-3.5-flash",
            "gemini-3-flash-preview",
            "gemini-2.5-computer-use-preview-10-2025",
        }
        return value in known or version_at_least(value, "gemini-", (3, 8))

    if provider == "anthropic":
        known_prefixes = (
            "claude-fable-5",
            "claude-mythos-5",
            "claude-opus-5",
            "claude-sonnet-5",
            "claude-opus-4-8",
            "claude-opus-4-7",
            "claude-opus-4-6",
            "claude-sonnet-4-6",
            "claude-opus-4-5",
            "claude-sonnet-4-5",
            "claude-haiku-4-5",
        )
        if any(value.startswith(prefix) for prefix in known_prefixes):
            return True
        version = _claude_version(value)
        return version is not None and version >= (4, 8, 0)

    return False


def supports_anthropic_adaptive_thinking(model_id) -> bool:
    """Claude 4.6+ and later generations use adaptive thinking."""
    version = _claude_version(model_id)
    return version is not None and version >= (4, 6, 0)


def supports_xai_native_files(model_id) -> bool:
    """xAI native file references: Grok 4+ text models, including future IDs."""
    value = normalize_model_id(model_id)
    if "imagine" in value:
        return False
    return version_at_least(value, "grok-", (4, 0))
