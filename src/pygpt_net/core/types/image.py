#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.10 19:25:00                  #
# ================================================== #

VIDEO_AVAILABLE_ASPECT_RATIOS = {
    "1:1": "1:1",
    "2:3": "2:3",
    "3:2": "3:2",
    "3:4": "3:4",
    "4:3": "4:3",
    "4:5": "4:5",
    "5:4": "5:4",
    "9:16": "9:16",
    "16:9": "16:9",
    "21:9": "21:9",
}

VIDEO_AVAILABLE_RESOLUTIONS = {
    "480p": "480p",
    "720p": "720p",
    "1080p": "1080p",
    "1440p": "1440p",
    "4K": "4K",
    "8K": "8K",
}


_GEMINI_31_FLASH_512 = (
    "512x512", "256x1024", "192x1536", "424x632", "632x424",
    "448x600", "1024x256", "600x448", "464x576", "576x464",
    "1536x192", "384x688", "688x384", "792x168",
)

_GEMINI_31_FLASH_1K = (
    "1024x1024", "512x2048", "384x3072", "848x1264", "1264x848",
    "896x1200", "2048x512", "1200x896", "928x1152", "1152x928",
    "3072x384", "768x1376", "1376x768", "1584x672",
)

_GEMINI_3_COMMON_1K = (
    "1024x1024", "848x1264", "1264x848", "896x1200", "1200x896",
    "928x1152", "1152x928", "768x1376", "1376x768", "1584x672",
)

_GEMINI_25_FLASH = (
    "1024x1024", "832x1248", "1248x832", "864x1184", "1184x864",
    "896x1152", "1152x896", "768x1344", "1344x768", "1536x672",
)


_GPT_IMAGE_LEGACY = (
    "auto", "1024x1024", "1536x1024", "1024x1536",
)

# GPT Image 2+ accepts arbitrary WIDTHxHEIGHT values within the API limits.
# The UI exposes a practical set of common choices; per-call tool overrides may
# still use any valid custom dimensions and are validated by the provider.
_GPT_IMAGE_2_COMMON = (
    "auto",
    "1024x1024",
    "1536x1024",
    "1024x1536",
    "1536x864",
    "864x1536",
    "2048x2048",
    "2048x1152",
    "1152x2048",
    "2560x1440",
    "1440x2560",
    "3840x2160",
    "2160x3840",
)

_XAI_IMAGE_RESOLUTIONS = ("1k", "2k")

_NANO_BANANA_PRO_LEGACY = (
    "2048x2048", "4096x4096",
    "1664x2496", "2496x1664", "3328x4992", "4992x3328",
    "1728x2368", "2368x1728", "3456x4736", "4736x3456",
    "1792x2304", "2304x1792", "3584x4608", "4608x3584",
    "1536x2688", "2688x1536", "3072x5376", "5376x3072",
    "3072x1344", "6144x2688",
)

def _scale_resolutions(values, factor):
    out = []
    for value in values:
        w, h = value.split("x")
        out.append(f"{int(w) * factor}x{int(h) * factor}")
    return tuple(out)

def _resolution_map(values):
    return {value: value for value in values}

_GEMINI_31_FLASH_ALL = (
    _GEMINI_31_FLASH_512
    + _GEMINI_31_FLASH_1K
    + _scale_resolutions(_GEMINI_31_FLASH_1K, 2)
    + _scale_resolutions(_GEMINI_31_FLASH_1K, 4)
)

_GEMINI_3_PRO_ALL = (
    _GEMINI_3_COMMON_1K
    + _scale_resolutions(_GEMINI_3_COMMON_1K, 2)
    + _scale_resolutions(_GEMINI_3_COMMON_1K, 4)
)


IMAGE_AVAILABLE_RESOLUTIONS = {
    # Keep the newer family before the legacy prefix. get_available_resolutions()
    # also applies version-aware future fallbacks before ordinary prefix matching.
    "gpt-image-2": _resolution_map(_GPT_IMAGE_2_COMMON),
    "gpt-image": _resolution_map(_GPT_IMAGE_LEGACY),
    "chatgpt-image": _resolution_map(_GPT_IMAGE_LEGACY),
    "imagen-3.0": {
        "1024x1024": "1024x1024",
        "896x1280": "896x1280",
        "1280x896": "1280x896",
        "768x1408": "768x1408",
        "1408x768": "1408x768"
    },
    "imagen-4.0": {
        "1024x1024": "1024x1024",
        "896x1280": "896x1280",
        "1280x896": "1280x896",
        "768x1408": "768x1408",
        "1408x768": "1408x768",
        "2048x2048": "2048x2048",
        "1792x2560": "1792x2560",
        "2560x1792": "2560x1792",
        "1536x2816": "1536x2816",
        "2816x1536": "2816x1536"
    },

    # Gemini native image models. Put exact model families before the aliases
    # below because get_available_resolutions() uses prefix matching.
    "gemini-3.1-flash-image": _resolution_map(_GEMINI_31_FLASH_ALL),
    "gemini-3.1-flash-lite-image": _resolution_map(_GEMINI_31_FLASH_1K),
    "gemini-3-pro-image": _resolution_map(_GEMINI_3_PRO_ALL),
    "gemini-2.5-flash-image": _resolution_map(_GEMINI_25_FLASH),

    # UI aliases kept for backward compatibility with existing configs.
    "nano-banana-pro": _resolution_map(_NANO_BANANA_PRO_LEGACY),
    "nano-banana": _resolution_map(_GEMINI_25_FLASH),

    # xAI Imagine uses resolution tiers rather than explicit pixel dimensions.
    # Known aliases keep working, while numbered 2.x+ models are also handled by
    # the version-aware future fallback in core.image.Image.
    "grok-imagine-image-2": _resolution_map(_XAI_IMAGE_RESOLUTIONS),
    "grok-imagine-image-quality": _resolution_map(_XAI_IMAGE_RESOLUTIONS),
    "grok-imagine-image": _resolution_map(_XAI_IMAGE_RESOLUTIONS),

    "sora-2-pro": {
        "1280x720": "1280x720",
        "720x1280": "720x1280",
        "1792x1024": "1792x1024",
        "1024x1792": "1024x1792"
    },
    "sora-2": {
        "1280x720": "1280x720",
        "720x1280": "720x1280"
    },
    "veo-3": {
        "1280x720": "1280x720",
        "720x1280": "720x1280",
        "1920x1080": "1920x1080",
        "1080x1920": "1080x1920"
    },
}

def _numeric_model_version(model_id, prefix):
    """Return a numeric version tuple immediately following *prefix*."""
    try:
        value = str(model_id or "").lower().split("/")[-1]
        prefix = str(prefix or "").lower()
        if not value.startswith(prefix):
            return None
        tail = value[len(prefix):]
        parts = []
        for token in tail.split("-")[0].split("."):
            if not token.isdigit():
                break
            parts.append(int(token))
        if not parts:
            return None
        while len(parts) < 3:
            parts.append(0)
        return tuple(parts[:3])
    except Exception:
        return None


def model_version_at_least(model_id, prefix, minimum):
    """Return True when a numbered model family is at or above *minimum*."""
    version = _numeric_model_version(model_id, prefix)
    if version is None:
        return False
    minimum = tuple(minimum)
    minimum = minimum + (0,) * (3 - len(minimum))
    return version >= minimum[:3]


def get_future_image_resolutions(model_id):
    """
    Resolve a conservative forward-only fallback for not-yet-listed image models.

    The rule deliberately does not back-port the newest capabilities to older
    numeric generations. Known older models continue to use their explicit maps.
    """
    mid = str(model_id or "").lower().split("/")[-1]

    # OpenAI: GPT Image 2 and newer inherit the current custom-size capability.
    if model_version_at_least(mid, "gpt-image-", (2, 0)):
        return _resolution_map(_GPT_IMAGE_2_COMMON)

    # Google Imagen: use the newest known Imagen 4 sizing for 4.x and later.
    if model_version_at_least(mid, "imagen-", (4, 0)):
        return IMAGE_AVAILABLE_RESOLUTIONS["imagen-4.0"]

    # Google Gemini image families. Keep Flash Lite conservative at 1K; Flash
    # inherits 512/1K/2K/4K from 3.1+, and Pro/generic image families inherit
    # the common 1K/2K/4K set from Gemini 3+.
    if mid.startswith("gemini-") and "image" in mid:
        if "flash-lite-image" in mid and model_version_at_least(mid, "gemini-", (3, 1)):
            return _resolution_map(_GEMINI_31_FLASH_1K)
        if "flash-image" in mid and model_version_at_least(mid, "gemini-", (3, 1)):
            return _resolution_map(_GEMINI_31_FLASH_ALL)
        if "pro-image" in mid and model_version_at_least(mid, "gemini-", (3, 0)):
            return _resolution_map(_GEMINI_3_PRO_ALL)
        if model_version_at_least(mid, "gemini-", (3, 1)):
            return _resolution_map(_GEMINI_3_PRO_ALL)

    # xAI: numbered Imagine Image 2.x and later use the current 1K/2K tiers.
    if model_version_at_least(mid, "grok-imagine-image-", (2, 0)):
        return _resolution_map(_XAI_IMAGE_RESOLUTIONS)

    return None

