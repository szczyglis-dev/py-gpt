#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.24 23:00:00                  #
# ================================================== #

from __future__ import annotations
from typing import Any, List, Optional

from agents import TResponseInputItem


def ellipsize(text: str, limit: int = 280) -> str:
    """Shorten text for logs."""
    if text is None:
        return ""
    s = str(text).replace("\n", " ").replace("\r", " ")
    return s if len(s) <= limit else s[: max(0, limit - 3)] + "..."


def content_to_text(content: Any) -> str:
    """Convert 'content' which may be str or list[dict] to plain text for logs."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out: List[str] = []
        for part in content:
            if isinstance(part, dict):
                if "text" in part and isinstance(part["text"], str):
                    out.append(part["text"])
                elif part.get("type") in ("output_text", "input_text") and "text" in part:
                    out.append(str(part["text"]))
                else:
                    # fallback – best-effort stringify
                    t = part.get("text") or ""
                    out.append(str(t))
            else:
                out.append(str(part))
        return " ".join(out)
    return str(content or "")


def items_preview(items: List[TResponseInputItem], total_chars: int = 280, max_items: int = 4) -> str:
    """
    Produce compact preview of last N messages with roles and truncated content.
    """
    if not items:
        return "(empty)"
    pick = items[-max_items:]
    per = max(32, total_chars // max(1, len(pick)))
    lines: List[str] = []
    for it in pick:
        if not isinstance(it, dict):
            lines.append(ellipsize(str(it), per))
            continue
        role = it.get("role", "?")
        text = content_to_text(it.get("content"))
        lines.append(f"- {role}: {ellipsize(text, per)}")
    return " | ".join(lines)