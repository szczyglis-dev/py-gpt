#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.18 19:20:00                  #
# ================================================== #

"""Helpers for durable attachment/file/conversation mention markers.

The XML-like form is an internal representation used by the UI/history so mention
semantics survive editing and reloads. Attachment/file markers are flattened
before text reaches a model. Conversation markers intentionally remain structured
because their body contains query-focused context retrieved from chat history.
"""

from dataclasses import dataclass
import html
import os
import re
from typing import Any, Callable, Iterator, Mapping, Optional

KIND_ATTACHMENT = "attachment"
KIND_FILE_CONTEXT = "file_context"
KIND_CONVERSATION = "conversation"
SUPPORTED_KINDS = (KIND_ATTACHMENT, KIND_FILE_CONTEXT, KIND_CONVERSATION)
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif", ".webp")

_SIMPLE_TAG_RE = re.compile(
    r"<(attachment|file_context)>(.*?)</\1>",
    re.IGNORECASE | re.DOTALL,
)
_CONVERSATION_TAG_RE = re.compile(
    r"<conversation\b([^>]*)>(.*?)</conversation>",
    re.IGNORECASE | re.DOTALL,
)
_ATTR_RE = re.compile(
    r"\b(id|title)\s*=\s*([\"'])(.*?)\2",
    re.IGNORECASE | re.DOTALL,
)


@dataclass(frozen=True, slots=True)
class MentionTag:
    """Parsed durable mention marker."""

    start: int
    end: int
    kind: str
    value: str
    label: str
    content: str = ""
    raw: str = ""


def encode_value(value: str) -> str:
    """Escape a mention value for the XML-like durable representation."""
    return html.escape(str(value or ""), quote=False)


def decode_value(value: str) -> str:
    """Decode a value stored inside a durable mention tag or attribute."""
    return html.unescape(str(value or ""))


def _conversation_attrs(raw_attrs: str) -> tuple[str, str]:
    attrs = {}
    for match in _ATTR_RE.finditer(str(raw_attrs or "")):
        attrs[str(match.group(1) or "").lower()] = decode_value(match.group(3))
    return str(attrs.get("id", "")).strip(), str(attrs.get("title", "")).strip()


def _conversation_content(value: str) -> str:
    """Keep summary text literal while neutralizing our structural closing tag."""
    return re.sub(
        r"</conversation>",
        "&lt;/conversation&gt;",
        str(value or ""),
        flags=re.IGNORECASE,
    )


def make_tag(
        kind: str,
        value: str,
        label: Optional[str] = None,
        content: str = "",
) -> str:
    """Create the durable internal tag for a mention.

    Conversation mentions use the same tag that is ultimately shown to the model:
    the UI initially stores an empty body, and the send boundary fills it with a
    query-focused summary while preserving ``id`` and ``title`` for rendering.
    """
    kind = str(kind or "").lower()
    if kind not in SUPPORTED_KINDS:
        return str(value or "")
    if kind == KIND_CONVERSATION:
        ctx_id = str(value or "").strip()
        title = str(label or "").strip()
        if not ctx_id.isdigit():
            return str(value or "")
        safe_id = html.escape(ctx_id, quote=True)
        safe_title = html.escape(title, quote=True)
        body = _conversation_content(content)
        return f'<conversation id="{safe_id}" title="{safe_title}">{body}</conversation>'
    return f"<{kind}>{encode_value(value)}</{kind}>"


def iter_tags(text: str) -> Iterator[MentionTag]:
    """Yield parsed durable mention markers in source order."""
    raw = str(text or "")
    tags = []

    for match in _SIMPLE_TAG_RE.finditer(raw):
        kind = str(match.group(1) or "").lower()
        value = decode_value(match.group(2))
        tags.append(MentionTag(
            start=match.start(),
            end=match.end(),
            kind=kind,
            value=value,
            label=label_for(kind, value),
            raw=match.group(0),
        ))

    for match in _CONVERSATION_TAG_RE.finditer(raw):
        ctx_id, title = _conversation_attrs(match.group(1))
        if not ctx_id.isdigit():
            continue
        tags.append(MentionTag(
            start=match.start(),
            end=match.end(),
            kind=KIND_CONVERSATION,
            value=ctx_id,
            label=title or ctx_id,
            content=str(match.group(2) or ""),
            raw=match.group(0),
        ))

    tags.sort(key=lambda item: item.start)
    last_end = -1
    for tag in tags:
        if tag.start < last_end:
            continue
        last_end = tag.end
        yield tag


def label_for(kind: str, value: str, label: Optional[str] = None) -> str:
    """Return the compact label shown to the user for a durable mention."""
    kind = str(kind or "").lower()
    value = str(value or "").strip()
    if kind == KIND_ATTACHMENT:
        return value
    if kind == KIND_CONVERSATION:
        return str(label or value).strip()

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
    """Build filename -> ``Attached Image #N`` mapping in provider attachment order.

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
            labels.setdefault(name.casefold(), f"Attached Image #{image_index}")

    return labels


def resolve_conversation_mentions(
        text: str,
        resolver: Callable[[int, str, str], str],
        query: Optional[str] = None,
) -> str:
    """Fill conversation mention bodies using a query-focused resolver.

    ``resolver`` receives ``(context_id, title, query)``. Existing non-empty
    conversation bodies are kept so restored/history input is not summarized
    again. This function is intentionally independent of plugin enable state.
    """
    raw = str(text or "")
    if not raw or resolver is None:
        return raw
    query_text = str(query if query is not None else to_display_text(raw)).strip()

    def repl(match: re.Match[str]) -> str:
        ctx_id, title = _conversation_attrs(match.group(1))
        if not ctx_id.isdigit():
            return match.group(0)
        existing = str(match.group(2) or "").strip()
        if existing:
            return match.group(0)
        try:
            summary = str(resolver(int(ctx_id), title, query_text) or "").strip()
        except Exception:
            summary = ""
        # Keep code/markup in the retrieved context literal; make_tag() only
        # neutralizes our own closing delimiter so the structural wrapper cannot
        # be terminated by model-generated text.
        return make_tag(KIND_CONVERSATION, ctx_id, label=title, content=summary)

    return _CONVERSATION_TAG_RE.sub(repl, raw)


def to_model_text(
        text: str,
        attachments: Optional[Mapping[str, Any]] = None,
) -> str:
    """Flatten durable attachment/file mentions to provider-facing text.

    File/directory mentions become their stored path. Attachment mentions
    normally become the attachment filename. When current attachments are
    supplied, image mentions become stable ``Attached Image #N`` labels.

    Conversation tags are preserved. Their body has already been populated at
    the send boundary with query-focused context, so keeping the structured tag
    gives the target model both provenance (ID/title) and retrieved content.
    """
    raw = str(text or "")
    image_labels = _image_attachment_mentions(attachments)
    out = []
    pos = 0

    # Iterate top-level durable markers rather than applying the simple-tag regex
    # globally. This preserves literal code such as <attachment>...</attachment>
    # when it appears inside a retrieved <conversation> body.
    for tag in iter_tags(raw):
        out.append(raw[pos:tag.start])
        if tag.kind == KIND_CONVERSATION:
            out.append(tag.raw)
        else:
            value = tag.value
            if tag.kind == KIND_ATTACHMENT and image_labels:
                label = image_labels.get(value.strip().casefold())
                if label is not None:
                    value = label
            out.append(value)
        pos = tag.end
    out.append(raw[pos:])
    return "".join(out)


def to_display_text(text: str) -> str:
    """Replace durable tags with the plain ``@label`` representation."""
    raw = str(text or "")
    out = []
    pos = 0
    for tag in iter_tags(raw):
        out.append(raw[pos:tag.start])
        out.append("@" + (tag.label or tag.value))
        pos = tag.end
    out.append(raw[pos:])
    return "".join(out)
