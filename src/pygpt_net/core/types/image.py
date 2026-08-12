#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.08.12 16:30:00                  #
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
    "gpt-image": {
        "auto": "auto",
        "1024x1024": "1024x1024",
        "1536x1024": "1536x1024",
        "1024x1536": "1024x1536"
    },
    "dall-e-3": {
        "1792x1024": "1792x1024",
        "1024x1792": "1024x1792",
        "1024x1024": "1024x1024"
    },
    "dall-e-2": {
        "1024x1024": "1024x1024",
        "512x512": "512x512",
        "256x256": "256x256"
    },
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
