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

from html import escape
from typing import Any, Dict, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from pygpt_net.utils import trans


class ToolInfo(QWidget):
    """Read-only tool definition shown in plugin settings."""

    def __init__(self, window=None, option: Dict[str, Any] = None):
        super(ToolInfo, self).__init__(window)
        self.window = window
        self.option = option or {}

        self.label = QLabel(self)
        self.label.setTextFormat(Qt.RichText)
        self.label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)
        self.setLayout(layout)

        self.update_locale()

    def update_locale(self):
        """Refresh translated section labels."""
        value = self.option.get("value")
        if not isinstance(value, dict):
            value = {}

        instruction = str(value.get("instruction") or "")
        params = value.get("params")
        if not isinstance(params, (list, tuple)):
            params = []

        instruction_label = trans("settings.cmd.field.instruction")
        required_label = trans("settings.cmd.field.params.required")
        optional_label = trans("settings.cmd.field.params.optional")
        none_label = trans("settings.cmd.field.params.none")

        required: List[Dict[str, Any]] = []
        optional: List[Dict[str, Any]] = []
        for item in params:
            if not isinstance(item, dict):
                continue
            if bool(item.get("required", False)):
                required.append(item)
            else:
                optional.append(item)

        parts = [
            f"<b>{escape(instruction_label)}:</b>",
            f"<div style='margin: 2px 0 8px 0'>{escape(instruction).replace(chr(10), '<br>') if instruction else '—'}</div>",
        ]

        if not required and not optional:
            parts.append(f"<div style='margin: 2px 0 0 0'>{escape(none_label)}</div>")
        else:
            if required:
                parts.append(self._render_params_group(required_label, required))
            if optional:
                parts.append(self._render_params_group(optional_label, optional))

        self.label.setText("".join(parts))

    @staticmethod
    def _render_params_group(title: str, params: List[Dict[str, Any]]) -> str:
        """Render one parameter group as compact rich text."""
        rows = []
        for item in params:
            name = escape(str(item.get("name") or ""))
            description = escape(str(item.get("description") or "")).replace(chr(10), '<br>')
            param_type = escape(str(item.get("type") or ""))

            text = f"<b>{name}:</b>"
            if description:
                text += f" {description}"
            if param_type:
                text += f" <span style='white-space: nowrap'>({param_type})</span>"
            rows.append(f"<li>{text}</li>")

        return (
            f"<div style='margin-top: 6px'><b>{escape(title)}:</b></div>"
            "<ul style='margin-top: 2px; margin-bottom: 2px'>"
            + "".join(rows)
            + "</ul>"
        )
