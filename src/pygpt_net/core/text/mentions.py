#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.14 23:00:00                  #
# ================================================== #

"""Helpers for durable attachment/file mention markers.

The XML-like form is an internal representation used by the UI/history so mention
semantics survive editing and reloads. It must be flattened before text reaches a
model/provider.
"""

import html
import re
from typing import Iterator, Match

KIND_ATTACHMENT = "attachment"
KIND_FILE_CONTEXT = "file_context"
SUPPORTED_KINDS = (KIND_ATTACHMENT, KIND_FILE_CONTEXT)

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


def to_model_text(text: str) -> str:
    """Replace durable mention tags with only their raw model-facing values.

    Attachments become their filename and project file/directory mentions become
    their stored path (for example ``%workdir%/data/docs/spec.md``).
    """
    raw = str(text or "")

    def repl(match: Match[str]) -> str:
        return decode_value(match.group(2))

    return TAG_RE.sub(repl, raw)


def to_display_text(text: str) -> str:
    """Replace durable tags with the plain ``@label`` representation."""
    raw = str(text or "")

    def repl(match: Match[str]) -> str:
        kind = match.group(1).lower()
        value = decode_value(match.group(2))
        return "@" + label_for(kind, value)

    return TAG_RE.sub(repl, raw)
