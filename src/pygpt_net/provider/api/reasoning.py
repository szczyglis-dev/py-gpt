#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.08.16 17:40:00                  #
# ================================================== #

"""Shared helpers for provider-supplied reasoning/thinking summaries.

The public APIs covered here generally do not expose a model's private raw
chain-of-thought.  This module therefore treats any readable provider payload
as a *reasoning trace* (usually a summary) and keeps it separate from the
assistant's actual output stored in ``CtxItem.output``.
"""

import io
from typing import Any, Optional, Tuple


THINK_OPEN = "<think>"
THINK_CLOSE = "</think>\n\n"


def is_tagged_reasoning_model(model) -> bool:
    """Return True for local model backends that expose reasoning via <think> tags."""
    if model is None:
        return False

    try:
        if model.is_ollama():
            return True
    except Exception:
        pass

    provider = str(getattr(model, "provider", "") or "").strip().lower()
    if provider == "local_ai":
        return True

    llama_cfg = getattr(model, "llama_index", None)
    if isinstance(llama_cfg, dict):
        llama_provider = str(llama_cfg.get("provider") or "").strip().lower()
        if llama_provider == "local_ai" or "ollama" in llama_provider:
            return True

    return False


def extract_tagged_reasoning(output: Any) -> Tuple[str, str]:
    """Split model-authored ``<think>`` blocks from regular assistant output.

    Local reasoning models (notably DeepSeek variants served through Ollama or
    an OpenAI-compatible local endpoint) often expose their reasoning directly
    in the text stream.  The renderer understands those tags, but persisted
    conversation history must not contain the reasoning trace.

    Complete blocks are extracted, and an unfinished final block is treated as
    reasoning too so stopping generation mid-thought cannot leak it into the
    next request.  Unmatched closing tags are left untouched.
    """
    if output is None:
        return "", ""

    text = str(output)
    if THINK_OPEN not in text:
        return text, ""

    answer_parts = []
    reasoning_parts = []
    pos = 0
    close_tag = "</think>"

    while True:
        start = text.find(THINK_OPEN, pos)
        if start < 0:
            answer_parts.append(text[pos:])
            break

        answer_parts.append(text[pos:start])
        body_start = start + len(THINK_OPEN)
        end = text.find(close_tag, body_start)

        if end < 0:
            # Generation may have been stopped while the model was still
            # thinking. Keep the partial trace as reasoning and remove it from
            # the normal assistant response.
            reasoning_parts.append(text[body_start:])
            pos = len(text)
            break

        reasoning_parts.append(text[body_start:end])
        pos = end + len(close_tag)

        # DeepSeek-style output commonly uses blank lines only as a separator
        # between </think> and the actual answer.  Remove that separator when
        # the think block starts the response, matching the provider reasoning
        # pipeline which emits THINK_CLOSE with two trailing newlines.
        if not "".join(answer_parts).strip():
            if text.startswith("\r\n\r\n", pos):
                pos += 4
            elif text.startswith("\n\n", pos):
                pos += 2
            elif text.startswith("\r\n", pos):
                pos += 2
            elif text.startswith("\n", pos):
                pos += 1

    reasoning = "\n\n".join(part.strip() for part in reasoning_parts if part.strip())
    return "".join(answer_parts), reasoning


def strip_and_store_tagged_reasoning(
        ctx,
        output: Any,
        provider: str = "local",
) -> str:
    """Persist local ``<think>`` reasoning in ``ctx.extra`` and return clean output."""
    cleaned, reasoning = extract_tagged_reasoning(output)
    if reasoning:
        store_reasoning(
            ctx=ctx,
            provider=provider,
            text=reasoning,
            kind="thinking",
            raw=True,
            visible=True,
            encrypted=False,
        )
    return cleaned


def _ensure_buffer(state) -> io.StringIO:
    buf = getattr(state, "reasoning_buffer", None)
    if buf is None:
        buf = io.StringIO()
        state.reasoning_buffer = buf
    return buf


def _ensure_display_buffer(state) -> io.StringIO:
    buf = getattr(state, "reasoning_display_buffer", None)
    if buf is None:
        buf = io.StringIO()
        state.reasoning_display_buffer = buf
    return buf


def stream_reasoning_delta(
        state,
        text: Any,
        provider: str,
        kind: str = "summary",
        raw: bool = False,
) -> Optional[str]:
    """Wrap a streamed reasoning delta in the existing ``<think>`` UI flow."""
    if text is None:
        return None
    text = str(text)
    if text == "":
        return None

    state.reasoning_provider = provider
    state.reasoning_kind = kind
    state.reasoning_raw = bool(raw)

    buf = _ensure_buffer(state)
    display = _ensure_display_buffer(state)

    prefix = ""
    if not getattr(state, "reasoning_open", False):
        # Preserve separation between multiple thinking blocks in the normalized
        # DB value while keeping each UI block independent.
        if buf.tell() > 0:
            buf.write("\n\n")
        state.reasoning_open = True
        prefix = THINK_OPEN
        display.write(prefix)

    buf.write(text)
    display.write(text)
    return prefix + text


def close_stream_reasoning(state) -> str:
    """Close an active streamed reasoning block and remember its exact markup."""
    if not getattr(state, "reasoning_open", False):
        return ""

    state.reasoning_open = False
    display = getattr(state, "reasoning_display_buffer", None)
    if display is None:
        return ""

    display.write(THINK_CLOSE)
    block = display.getvalue()
    blocks = getattr(state, "reasoning_display_blocks", None)
    if blocks is None:
        blocks = []
        state.reasoning_display_blocks = blocks
    blocks.append(block)

    try:
        display.close()
    except Exception:
        pass
    state.reasoning_display_buffer = None
    return THINK_CLOSE


def stream_text_delta(state, text: Any) -> Optional[str]:
    """Return a normal answer delta, closing a preceding thinking block first."""
    if text is None:
        return None
    text = str(text)
    if text == "":
        return None
    return close_stream_reasoning(state) + text


def strip_stream_reasoning(output: str, state) -> str:
    """Remove only reasoning markup generated by this module from persisted output."""
    if not output:
        return output
    for block in getattr(state, "reasoning_display_blocks", None) or []:
        # A provider-generated block should occur once, but limiting replacement
        # prevents an identical model-authored block later in the answer from
        # being removed accidentally.
        output = output.replace(block, "", 1)
    return output


def store_reasoning(
        ctx,
        provider: str,
        text: Any = "",
        kind: str = "summary",
        raw: bool = False,
        visible: bool = True,
        encrypted: bool = False,
        reasoning_tokens: Optional[int] = None,
):
    """Persist a normalized reasoning descriptor in ``ctx.extra``."""
    if not isinstance(getattr(ctx, "extra", None), dict):
        ctx.extra = {}

    normalized = str(text or "").strip()
    data = ctx.extra.get("reasoning")
    if not isinstance(data, dict):
        data = {}

    data.update({
        "provider": str(provider or ""),
        "type": str(kind or "summary"),
        "text": normalized,
        "raw": bool(raw),
        "visible": bool(visible and normalized),
        "encrypted": bool(encrypted),
    })
    if reasoning_tokens is not None:
        try:
            data["tokens"] = int(reasoning_tokens)
        except Exception:
            pass

    ctx.extra["reasoning"] = data


def ensure_reasoning_metadata(ctx, provider: str, reasoning_tokens: Any):
    """Store hidden-reasoning metadata when only token usage is exposed."""
    try:
        tokens = int(reasoning_tokens or 0)
    except Exception:
        tokens = 0
    if tokens <= 0:
        return

    current = getattr(ctx, "extra", None)
    if isinstance(current, dict):
        reasoning = current.get("reasoning")
        if isinstance(reasoning, dict) and reasoning.get("text"):
            reasoning["tokens"] = tokens
            return

    # The exact hidden representation differs by provider.  Mark it explicitly
    # as unavailable for display instead of presenting encrypted/internal data.
    store_reasoning(
        ctx=ctx,
        provider=provider,
        text="",
        kind="hidden",
        raw=False,
        visible=False,
        encrypted=False,
        reasoning_tokens=tokens,
    )


def persist_stream_reasoning(ctx, state):
    """Persist the readable reasoning accumulated by the streaming pipeline."""
    buf = getattr(state, "reasoning_buffer", None)
    if buf is None:
        return
    try:
        text = buf.getvalue()
    except Exception:
        text = ""

    if text.strip():
        store_reasoning(
            ctx=ctx,
            provider=getattr(state, "reasoning_provider", "") or "",
            text=text,
            kind=getattr(state, "reasoning_kind", "summary") or "summary",
            raw=bool(getattr(state, "reasoning_raw", False)),
            visible=True,
            encrypted=False,
            reasoning_tokens=(getattr(state, "usage_payload", {}) or {}).get("reasoning"),
        )


def cleanup_stream_reasoning(state):
    """Release reasoning buffers after a stream finishes."""
    for attr in ("reasoning_buffer", "reasoning_display_buffer"):
        buf = getattr(state, attr, None)
        if buf is not None:
            try:
                buf.close()
            except Exception:
                pass
            try:
                setattr(state, attr, None)
            except Exception:
                pass
    blocks = getattr(state, "reasoning_display_blocks", None)
    if isinstance(blocks, list):
        blocks.clear()
