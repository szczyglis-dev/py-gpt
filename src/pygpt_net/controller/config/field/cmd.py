#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.15 12:00:00                  #
# ================================================== #

from typing import Dict, Any


class Cmd:
    def __init__(self, window=None):
        """Tool config field handler."""
        self.window = window

    def apply(
            self,
            parent_id: str,
            key: str,
            option: Dict[str, Any]
    ):
        """
        Apply only the editable tool state. Instruction and parameter schema
        remain immutable metadata supplied by the plugin.
        """
        value = option.get("value")
        enabled = False
        if isinstance(value, dict):
            enabled = bool(value.get("enabled", False))
        elif isinstance(value, bool):
            enabled = value

        cfg = self.window.ui.config[parent_id][key]
        cfg.enabled.box.setChecked(enabled)

    def apply_row(
            self,
            parent_id: str,
            key: str,
            values: Dict[str, Any],
            idx: int
    ):
        """Compatibility no-op: tool parameter definitions are read-only."""
        return

    def get_value(
            self,
            parent_id: str,
            key: str,
            option: Dict[str, Any]
    ) -> bool:
        """Return the only user-editable tool value: enabled state."""
        cfg = self.window.ui.config[parent_id][key]
        return cfg.enabled.box.isChecked()

    def to_options(
            self,
            parent_id: str,
            option: Dict[str, Any]
    ) -> dict:
        """
        Convert dictionary items option to options. Command parameter schemas
        are no longer registered as editable dictionary fields.
        """
        ty = option.get("type")

        if ty == "dict":
            keys_map = option.get("keys")
            if not keys_map:
                return {}
            opts = {}
            prefix = f"{parent_id}."
            for k, item in keys_map.items():
                if isinstance(item, str):
                    opts[k] = {"label": f"{prefix}{k}", "type": item}
                else:
                    opts[k] = item
                    if "label" not in item:
                        item["label"] = f"{prefix}{k}"
            return opts

        return {}
