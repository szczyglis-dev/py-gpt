#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# ================================================== #

import os
import re
from dataclasses import dataclass
from typing import Optional, Union
from urllib.parse import unquote

from PySide6.QtCore import QUrl


@dataclass(frozen=True)
class ResolvedWebLink:
    """Normalized href/media target used by WebEngine and URL handlers."""

    original: str
    target: str = ""
    kind: str = "invalid"
    bridge_action: Optional[str] = None
    bridge_payload: str = ""
    local_path: Optional[str] = None

    @property
    def is_bridge(self) -> bool:
        return self.bridge_action is not None

    @property
    def is_bridge_command(self) -> bool:
        return self.kind == "bridge-command"

    @property
    def can_open_external(self) -> bool:
        return self.kind in ("web", "local", "external")

    @property
    def can_open_internal(self) -> bool:
        return self.kind in ("web", "local", "data")

    @property
    def can_download(self) -> bool:
        return self.kind in ("web", "local", "data", "blob")


class WebLinkResolver:
    """Resolve WebEngine links, including all PyGPT ``bridge://`` wrappers."""

    BRIDGE_PREFIX = "bridge://"
    BRIDGE_TARGET_ACTIONS = frozenset(("open_image", "play_video", "download"))
    BRIDGE_COMMAND_ACTIONS = frozenset(("open_find", "escape", "focus"))
    APP_ACTION_SCHEMES = frozenset((
        "extra-audio-read",
        "extra-code-copy",
        "extra-copy",
        "extra-delete",
        "extra-delete-chain",
        "extra-edit",
        "extra-replay",
    ))

    _WINDOWS_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")

    def __init__(self, window=None):
        self.window = window

    def resolve(self, value: Union[str, QUrl], ctx=None) -> ResolvedWebLink:
        """Resolve a raw href/QUrl into one actionable target description."""
        raw = self._stringify(value).strip()
        if not raw:
            return ResolvedWebLink(original=raw)

        if raw.lower().startswith(self.BRIDGE_PREFIX):
            return self._resolve_bridge(raw, ctx=ctx)
        return self._resolve_target(raw, original=raw, ctx=ctx)

    @staticmethod
    def _stringify(value: Union[str, QUrl]) -> str:
        if isinstance(value, QUrl):
            return value.toString()
        return str(value or "")

    def _resolve_bridge(self, raw: str, ctx=None) -> ResolvedWebLink:
        body = raw[len(self.BRIDGE_PREFIX):]
        lower = body.lower()

        # Historical find syntax is bridge://open_find:<pid>; accept slash too.
        if lower.startswith("open_find:"):
            return ResolvedWebLink(
                original=raw,
                kind="bridge-command",
                bridge_action="open_find",
                bridge_payload=body[len("open_find:"):],
            )
        if lower.startswith("open_find/"):
            return ResolvedWebLink(
                original=raw,
                kind="bridge-command",
                bridge_action="open_find",
                bridge_payload=body[len("open_find/"):],
            )

        action_name = body.rstrip("/").lower()
        if action_name in ("escape", "focus"):
            return ResolvedWebLink(
                original=raw,
                kind="bridge-command",
                bridge_action=action_name,
            )

        # Resource bridge actions carry a real URL/path after the action name.
        # Do not globally unquote the payload: signed HTTP URLs may depend on
        # their original percent-encoding. Local decoding happens later.
        for action in self.BRIDGE_TARGET_ACTIONS:
            prefix = action + "/"
            if lower.startswith(prefix):
                payload = body[len(prefix):]
                resolved = self._resolve_target(payload, original=raw, ctx=ctx)
                return ResolvedWebLink(
                    original=raw,
                    target=resolved.target,
                    kind=resolved.kind,
                    bridge_action=action,
                    bridge_payload=payload,
                    local_path=resolved.local_path,
                )

        # Future/unknown bridge actions are still treated as app commands, so
        # the opaque bridge:// URL is never passed to an external browser.
        action, payload = self._split_unknown_bridge(body)
        return ResolvedWebLink(
            original=raw,
            kind="bridge-command",
            bridge_action=action or "unknown",
            bridge_payload=payload,
        )

    @staticmethod
    def _split_unknown_bridge(body: str):
        slash = body.find("/")
        colon = body.find(":")
        cuts = [pos for pos in (slash, colon) if pos >= 0]
        if not cuts:
            return body.lower(), ""
        pos = min(cuts)
        return body[:pos].lower(), body[pos + 1:]

    def _resolve_target(self, raw: str, original: str, ctx=None) -> ResolvedWebLink:
        target = str(raw or "").strip()
        if not target:
            return ResolvedWebLink(original=original)

        lower = target.lower()

        if lower.startswith("sandbox:") or "%workdir%" in lower:
            return self._local(target, original=original, ctx=ctx)

        if os.path.isabs(target) or self._WINDOWS_PATH_RE.match(target):
            return self._local(target, original=original, ctx=ctx)

        qurl = QUrl(target, QUrl.TolerantMode)
        scheme = qurl.scheme().lower()

        if scheme == "file":
            return self._local(target, original=original, ctx=ctx)
        if scheme in ("http", "https"):
            return ResolvedWebLink(original=original, target=qurl.toString(), kind="web")
        if scheme == "data":
            return ResolvedWebLink(original=original, target=target, kind="data")
        if scheme == "blob":
            return ResolvedWebLink(original=original, target=target, kind="blob")
        if scheme == "qrc":
            return ResolvedWebLink(original=original, target=target, kind="qrc")
        if scheme in self.APP_ACTION_SCHEMES:
            return ResolvedWebLink(original=original, target=target, kind="app-action")
        if scheme:
            # mailto:, ftp:, and other OS handlers can be opened externally,
            # but are not treated as browser-downloadable resources here.
            return ResolvedWebLink(original=original, target=target, kind="external")

        # Bridge payloads may contain a relative path. Context-menu linkUrl()
        # normally gives us an absolute URL for ordinary hrefs already.
        return self._local(target, original=original, ctx=ctx)

    def _local(self, raw: str, original: str, ctx=None) -> ResolvedWebLink:
        try:
            path = self.window.core.filesystem.normalize_local_path(
                raw,
                auto_prefix=True,
                ctx=ctx,
            )
        except Exception:
            path = unquote(raw)
            if path.lower().startswith("file://"):
                local = QUrl(path, QUrl.TolerantMode).toLocalFile()
                if local:
                    path = local
        path = os.path.normpath(path) if path else path
        target = QUrl.fromLocalFile(path).toString(QUrl.FullyEncoded) if path else ""
        return ResolvedWebLink(
            original=original,
            target=target,
            kind="local",
            local_path=path,
        )
