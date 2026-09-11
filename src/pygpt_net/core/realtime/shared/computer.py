#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.10 15:55:00                  #
# ================================================== #

"""Shared client-side Computer Use bridge for realtime voice sessions.

Realtime/Live APIs expose normal function calling but do not expose the same
provider-native Computer Use tool contract used by Responses, Generate Content
or Anthropic Messages.  PyGPT therefore advertises a small, provider-neutral
subset of the existing ``cmd_mouse_control`` plugin as realtime functions and
feeds the plugin's transport-only screenshot back into the live session after
each action.

The execution path itself remains the ordinary PyGPT command/plugin path.  This
module only handles discovery, prompt/tool injection and screenshot transport,
so realtime provider controllers do not duplicate mouse/keyboard code.
"""

from __future__ import annotations

import base64
import mimetypes
import os
from typing import Iterable, Optional


CTX_FLAG = "realtime_computer_use_bridge"

# Keep one compact command dialect for voice models.  These are the mature
# cmd_mouse_control commands also referenced by the plugin's configurable
# Computer Use prompt; aliases/provider-specific actions stay inside the native
# provider adapters and are not duplicated here.
COMMANDS = (
    "get_screenshot",
    "get_mouse_position",
    "mouse_move",
    "mouse_click",
    "mouse_scroll",
    "mouse_drag",
    "keyboard_key",
    "keyboard_keys",
    "keyboard_type",
    "wait",
    "open_web_browser",
)


def _preset_has_computer_use(context) -> bool:
    preset = getattr(context, "preset", None)
    raw = getattr(preset, "remote_tools", None) if preset is not None else None
    if not raw:
        return False
    if isinstance(raw, str):
        values = [item.strip() for item in raw.split(",") if item.strip()]
    elif isinstance(raw, (list, tuple, set)):
        values = [str(item).strip() for item in raw if str(item).strip()]
    else:
        return False
    return "computer_use" in values


def is_enabled(window, context=None, provider: str = "") -> bool:
    """Return True when realtime Computer Use bridge should be advertised.

    Provider-native configuration keys remain authoritative.  A preset-level
    ``computer_use`` selection is also accepted for expert/internal calls.
    xAI currently has no PyGPT/native Computer Use setting, so it is left out
    until the voice endpoint exposes a documented visual Computer Use contract.
    """
    provider = str(provider or "").lower()
    cfg = window.core.config

    if _preset_has_computer_use(context):
        requested = True
    elif provider == "google":
        requested = bool(cfg.get("remote_tools.google.computer_use", False))
    elif provider == "openai":
        requested = bool(cfg.get("remote_tools.computer_use", False))
    else:
        requested = False

    if not requested:
        return False

    try:
        return window.core.plugins.get("cmd_mouse_control") is not None
    except Exception:
        return False


def mark_context(ctx) -> None:
    """Mark a ctx so the command dispatcher can execute bridge functions even
    when the normal local Tools switch is disabled.
    """
    if ctx is None:
        return
    if not isinstance(getattr(ctx, "extra", None), dict):
        ctx.extra = {}
    ctx.extra[CTX_FLAG] = True


def is_context_command(window, ctx, cmd_id: str) -> bool:
    """Return True if *cmd_id* is one of the realtime bridge commands."""
    if ctx is None or not isinstance(getattr(ctx, "extra", None), dict):
        return False
    if not ctx.extra.get(CTX_FLAG, False):
        return False
    if cmd_id not in COMMANDS:
        return False
    try:
        plugin = window.core.plugins.get("cmd_mouse_control")
        return bool(plugin and plugin.has_cmd(cmd_id))
    except Exception:
        return False


def prepare(window, context, functions: Optional[list], provider: str) -> tuple[list, str]:
    """Inject shared Computer Use function declarations and prompt for realtime.

    Returns ``(functions, system_prompt)``.  Existing functions are preserved and
    de-duplicated by name.  No plugin/resource state is modified.
    """
    items = list(functions or [])
    system_prompt = str(getattr(context, "system_prompt", "") or "")
    if not is_enabled(window, context=context, provider=provider):
        return items, system_prompt

    try:
        plugin = window.core.plugins.get("cmd_mouse_control")
    except Exception:
        plugin = None
    if plugin is None:
        return items, system_prompt

    mark_context(getattr(context, "ctx", None))

    cmds = []
    for name in COMMANDS:
        try:
            if not plugin.has_cmd(name):
                continue
            command = plugin.get_cmd(name)
            if command:
                cmds.append(command)
        except Exception:
            continue

    try:
        bridge_functions = window.core.command.cmds_to_functions(cmds)
    except Exception:
        bridge_functions = []

    known = {
        str(item.get("name") or "")
        for item in items
        if isinstance(item, dict) and item.get("name")
    }
    for function in bridge_functions:
        name = str(function.get("name") or "") if isinstance(function, dict) else ""
        if name and name not in known:
            items.append(function)
            known.add(name)

    # Reuse the same user-configurable instructions as the normal mouse plugin.
    # This avoids a second Computer Use prompt drifting away from plugin syntax.
    try:
        computer_prompt = str(plugin.get_option_value("prompt") or "").strip()
    except Exception:
        computer_prompt = ""
    if computer_prompt and computer_prompt not in system_prompt:
        if system_prompt.strip():
            system_prompt = system_prompt.rstrip() + "\n\n" + computer_prompt
        else:
            system_prompt = computer_prompt

    return items, system_prompt


def latest_transport_image(window, ctx) -> Optional[str]:
    """Return the newest existing transport-only screenshot from ctx lineage."""
    seen = set()
    candidate = ctx
    filesystem = getattr(getattr(window, "core", None), "filesystem", None)
    for _ in range(6):
        if candidate is None or id(candidate) in seen:
            break
        seen.add(id(candidate))
        values = getattr(candidate, "transport_images", None) or []
        for value in reversed(list(values)):
            raw = str(value or "").strip()
            if not raw:
                continue
            paths = []
            if filesystem is not None:
                try:
                    paths.append(filesystem.to_workdir(raw, auto_prefix=False, ctx=candidate))
                except Exception:
                    pass
            paths.append(raw)
            for path in paths:
                if path and os.path.isfile(path):
                    return path
        candidate = getattr(candidate, "prev_ctx", None) or getattr(candidate, "turn_parent", None)
    return None


def image_bytes(path: str) -> tuple[bytes, str]:
    """Read an image and return ``(bytes, mime_type)`` for live transport."""
    with open(path, "rb") as handle:
        data = handle.read()
    mime = mimetypes.guess_type(path)[0] or "image/png"
    if mime not in ("image/png", "image/jpeg", "image/jpg", "image/webp"):
        mime = "image/png"
    if mime == "image/jpg":
        mime = "image/jpeg"
    return data, mime


def image_data_uri(path: str) -> str:
    """Return a base64 data URI for OpenAI-compatible realtime image input."""
    data, mime = image_bytes(path)
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def normalize_image_paths(paths: Optional[Iterable[str]]) -> list[str]:
    """Return unique, existing image paths while preserving order."""
    out = []
    seen = set()
    for value in paths or []:
        path = str(value or "").strip()
        if not path or path in seen or not os.path.isfile(path):
            continue
        out.append(path)
        seen.add(path)
    return out
