#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.24 18:45:00                  #
# ================================================== #

"""Renderer transport protocol.

The protocol deliberately describes *DOM mutations*, not chat/provider modes.
Every producer (chat, Agents v2, evaluator, anonymous agent, tools, etc.) can
therefore converge on the same small set of operations.
"""

from dataclasses import dataclass, field
import json
from typing import Any, Optional


class RenderOp:
    """Stable operation names understood by both Python and the Web renderer."""

    APPEND_INPUT = "append_input"
    APPEND_OUTPUT = "append_output"
    REPLACE_INPUT = "replace_input"
    REPLACE_OUTPUT = "replace_output"

    # Synchronize metadata/structure of an already materialized assistant row.
    # Text is preserved unless ``replace_text`` is explicitly true.
    SYNC_OUTPUT = "sync_output"

    # End a live stream and promote its existing DOM node into durable history.
    # This is intentionally not a text replacement operation.
    FINALIZE_OUTPUT = "finalize_output"

    APPEND_ARTIFACT = "append_artifact"
    APPEND_ARTIFACTS = "append_artifacts"
    REPLACE_ARTIFACTS = "replace_artifacts"

    REMOVE_MESSAGE = "remove_message"
    REMOVE_FROM = "remove_from"


@dataclass(slots=True)
class RenderMutation:
    """Serializable renderer mutation envelope."""

    op: str
    msg_id: Optional[Any] = None
    block: Optional[dict] = None
    replace_text: bool = False
    reason: Optional[str] = None
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        data = {
            "op": self.op,
            "msg_id": self.msg_id,
            "block": self.block,
            "replace_text": bool(self.replace_text),
            "extra": self.extra or {},
        }
        if self.reason:
            data["reason"] = self.reason
        return data

    def to_json(self) -> str:
        return json.dumps(
            {"mutation": self.to_dict()},
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        )
