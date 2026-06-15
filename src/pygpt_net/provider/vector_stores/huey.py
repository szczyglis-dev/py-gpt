#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Huey vector-store backend selection.

This module is intentionally small. It gives PyHuey a stable policy layer
around PyGPT's existing vector-store providers without depending on Chroma.

Default policy:
- Qdrant is the native Python 3.13 default.
- Chroma is treated as a legacy/deprecated backend.
- The old Python 3.12 Chroma sidecar is migration-only and is never selected
  implicitly by the main Python 3.13 runtime.
"""

import os
from collections.abc import Mapping
from typing import Optional


DEFAULT_VECTOR_STORE_ID = "QdrantVectorStore"

LEGACY_CHROMA_IDS = {
    "ChromaVectorStore",
    "chroma",
    "chroma_sidecar",
    "chromadb",
}

DISABLED_VECTOR_IDS = {
    "none",
    "null",
    "disabled",
    "off",
}


def _normalize(value: object) -> str:
    """Normalize a configured vector-store value for comparison."""
    if value is None:
        return ""
    return str(value).strip()


def resolve_storage_id(
    configured: Optional[str],
    available: Mapping[str, object],
) -> Optional[str]:
    """
    Resolve the active vector-store provider ID.

    Environment override:
        HUEY_VECTOR_BACKEND=qdrant -> QdrantVectorStore
        HUEY_VECTOR_BACKEND=none   -> no vector store

    Blank, missing, "_", unavailable, and legacy Chroma values resolve to
    Qdrant when Qdrant is registered.

    Legacy Chroma values are deliberately remapped to Qdrant when Qdrant is
    available. This prevents old configs from breaking startup after Chroma is
    removed from the main runtime.
    """
    env_value = _normalize(os.getenv("HUEY_VECTOR_BACKEND")).lower()

    if env_value in DISABLED_VECTOR_IDS:
        return None

    if env_value == "qdrant":
        if DEFAULT_VECTOR_STORE_ID in available:
            return DEFAULT_VECTOR_STORE_ID
        return None

    configured_value = _normalize(configured)
    configured_key = configured_value.lower()

    if configured_key in DISABLED_VECTOR_IDS:
        return None

    if (
        not configured_value
        or configured_key in {item.lower() for item in LEGACY_CHROMA_IDS}
        or configured_value not in available
    ):
        if DEFAULT_VECTOR_STORE_ID in available:
            return DEFAULT_VECTOR_STORE_ID
        return None

    return configured_value
