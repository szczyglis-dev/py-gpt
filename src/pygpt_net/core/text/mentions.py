#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.15 14:00:00
# ================================================== #

"""Helpers for durable attachment/file mention markers.

The XML-like form is an internal representation used by the UI/history so mention
semantics survive editing and reloads. It must be flattened before text reaches a
model/provider.
"""

import html
import os
import re
from typing import Iterator, Match, Optional, Mapping, Any

KIND_ATTACHMENT = "attachment"
KIND_FILE_CONTEXT = "file_context"
SUPPORTED_KINDS = (KIND_ATTACHMENT, KIND_FILE_CONTEXT)
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif", ".webp")

TAG_RE = re.compile(
    r"<(attachment|file_context)>(.*?)</\1>",
    re.IGNORECASE | re.DOTALL,
)


def encode_value(value: str) -> str:
    """Escape a mention value for the XML-like durable representation."""
    return html.escape(str(value or ""), quote=False)


def decode_value(value: str) -> str:
    """Decode a value stored inside a durable mention tag."""
    return html.unescape(str(value or ""))


def make_tag(kind: str, value: str) -> str:
    """Create the durable internal tag for a mention."""
    kind = str(kind or "").lower()
    if kind not in SUPPORTED_KINDS:
        return str(value or "")
    return f"<{kind}>{encode_value(value)}</{kind}>"


def iter_tags(text: str) -> Iterator[Match[str]]:
    """Yield durable mention-tag matches in ``text``."""
    return TAG_RE.finditer(str(text or ""))


def label_for(kind: str, value: str) -> str:
    """Return the compact label shown to the user for a durable mention."""
    kind = str(kind or "").lower()
    value = str(value or "").strip()
    if kind == KIND_ATTACHMENT:
        return value

    normalized = value.replace("\\", "/")
    low = normalized.lower()
    prefix = "%workdir%/data/"
    if low.startswith(prefix.lower()):
        normalized = normalized[len(prefix):]
    elif low == "%workdir%/data":
        normalized = "data/"
    elif low.startswith("data/"):
        normalized = normalized[len("data/"):]

    return normalized or value


def _image_attachment_mentions(attachments: Optional[Mapping[str, Any]]) -> dict[str, str]:
    """Build filename -> ``Image #N`` mapping in provider attachment order.

    Only local image attachments that can actually be sent are counted. The
    mapping is runtime-only; durable mention tags keep the original filename.
    """
    labels: dict[str, str] = {}
    if not attachments:
        return labels

    image_index = 0
    for attachment in attachments.values():
        path = str(getattr(attachment, "path", None) or "").strip()
        if not path or not os.path.exists(path):
            continue
        if not path.lower().endswith(IMAGE_EXTENSIONS):
            continue

        image_index += 1
        name = str(getattr(attachment, "name", None) or "").strip()
        if not name:
            name = os.path.basename(path.rstrip("/\\"))
        if name:
            labels.setdefault(name.casefold(), f"Image #{image_index}")

    return labels


def to_model_text(
        text: str,
        attachments: Optional[Mapping[str, Any]] = None,
) -> str:
    """Flatten durable mention tags to provider-facing text.

    File/directory mentions become their stored path. Attachment mentions
    normally become the attachment filename. When current attachments are
    supplied, mentions that resolve to image attachments become stable
    ``Image #N`` labels, where ``N`` follows the same attachment iteration
    order used by multimodal provider payload builders.
    """
    raw = str(text or "")
    image_labels = _image_attachment_mentions(attachments)

    def repl(match: Match[str]) -> str:
        kind = match.group(1).lower()
        value = decode_value(match.group(2))
        if kind == KIND_ATTACHMENT and image_labels:
            label = image_labels.get(value.strip().casefold())
            if label is not None:
                return label
        return value

    return TAG_RE.sub(repl, raw)


def to_display_text(text: str) -> str:
    """Replace durable tags with the plain ``@label`` representation."""
    raw = str(text or "")

    def repl(match: Match[str]) -> str:
        kind = match.group(1).lower()
        value = decode_value(match.group(2))
        return "@" + label_for(kind, value)

    return TAG_RE.sub(repl, raw)
