#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.02 00:00:00                  #
# ================================================== #

"""Frontend message payload. No WebView or session dependencies."""

import json
from dataclasses import dataclass, field
from typing import Optional

@dataclass(slots=True)
class RenderBlock:
    """
    JSON payload for node rendering in JS templates.

    Keep only raw data here. HTML is avoided except where there is
    no easy way to keep raw (e.g. plugin-provided tool extras), which are
    carried under extra.tool_extra_html.
    """
    id: int
    meta_id: Optional[int] = None
    input: Optional[dict] = None
    output: Optional[dict] = None
    files: dict = field(default_factory=dict)
    images: dict = field(default_factory=dict)
    urls: dict = field(default_factory=dict)
    tools: dict = field(default_factory=dict)
    tools_outputs: dict = field(default_factory=dict)
    extra: dict = field(default_factory=dict)

    # ========================================
    # Serialization
    # ========================================

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "meta_id": self.meta_id,
            "input": self.input,
            "output": self.output,
            "files": self.files,
            "images": self.images,
            "urls": self.urls,
            "tools": self.tools,
            "tools_outputs": self.tools_outputs,
            "extra": self.extra,
        }

    def to_json(self, wrap: bool = True) -> str:
        """
        Convert node to JSON string.

        :param wrap: wrap into {"node": {...}} (single appendNode case)
        """
        data = self.to_dict()
        if wrap:
            return json.dumps({"node": data}, ensure_ascii=False, separators=(',', ':'))
        return json.dumps(data, ensure_ascii=False, separators=(',', ':'))

    # ========================================
    # Debug
    # ========================================

    def debug(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
