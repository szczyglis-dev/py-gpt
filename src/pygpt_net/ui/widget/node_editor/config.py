#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.25 11:30:00                  #
# ================================================== #

from __future__ import annotations

try:
    from pygpt_net.utils import trans as _trans
except Exception:
    _trans = None


class EditorConfig:
    """Central place for all user-facing strings used by NodeEditor.

    Each method returns a final string. If a translator (pygpt_net.utils.trans)
    is available, keys are looked up; otherwise English defaults are used.
    """

    def _t(self, key: str, default: str) -> str:
        try:
            if _trans is None:
                return default
            val = _trans(key)
            # Fallback to default when translator returns key or empty
            if not val or val == key:
                return default
            return val
        except Exception:
            return default

    # ----- Commands / Undo text -----

    def cmd_add_node(self, type_name: str) -> str:
        return f"{self._t('node.editor.cmd.add', 'Add')} {type_name}"

    def cmd_move_node(self) -> str:
        return self._t('node.editor.cmd.move_node', 'Move Node')

    def cmd_resize_node(self) -> str:
        return self._t('node.editor.cmd.resize_node', 'Resize Node')

    def cmd_connect(self) -> str:
        return self._t('node.editor.cmd.connect', 'Connect')

    def cmd_rewire_connection(self) -> str:
        return self._t('node.editor.cmd.rewire_connection', 'Rewire Connection')

    def cmd_delete_connection(self) -> str:
        return self._t('node.editor.cmd.delete_connection', 'Delete Connection')

    def cmd_delete_node(self) -> str:
        return self._t('node.editor.cmd.delete_node', 'Delete Node')

    def cmd_clear(self) -> str:
        return self._t('node.editor.cmd.clear', 'Clear')

    def macro_delete_selection(self) -> str:
        return self._t('node.editor.macro.delete_selection', 'Delete selection')

    # ----- Scene / Context menus -----

    def menu_add(self) -> str:
        return self._t('node.editor.menu.add', 'Add')

    def menu_undo(self) -> str:
        return self._t('node.editor.menu.undo', 'Undo')

    def menu_redo(self) -> str:
        return self._t('node.editor.menu.redo', 'Redo')

    def menu_clear(self) -> str:
        return self._t('node.editor.menu.clear', 'Clear')

    def edge_context_delete(self) -> str:
        return self._t('node.editor.edge.delete', 'Delete connection')

    def node_context_rename(self) -> str:
        return self._t('node.editor.node.rename', 'Rename')

    def node_context_delete(self) -> str:
        return self._t('node.editor.node.delete', 'Delete')

    def rename_dialog_title(self) -> str:
        return self._t('node.editor.rename.title', 'Rename Node')

    def rename_dialog_label(self) -> str:
        return self._t('node.editor.rename.label', 'Name:')

    # ----- Overlays / Status -----

    def overlay_grab_tooltip(self) -> str:
        return self._t('node.editor.overlay.grab', 'Grab: toggle global panning with Left Mouse Button')

    def overlay_zoom_in_tooltip(self) -> str:
        return self._t('node.editor.overlay.zoom_in', 'Zoom In')

    def overlay_zoom_out_tooltip(self) -> str:
        return self._t('node.editor.overlay.zoom_out', 'Zoom Out')

    def status_no_nodes(self) -> str:
        return self._t('node.editor.status.no_nodes', 'No nodes')

    def type_unknown(self) -> str:
        return self._t('node.editor.type.unknown', 'Unknown')

    # ----- Labels / Tooltips -----

    def label_id(self) -> str:
        return self._t('node.editor.label.id', 'ID')

    def lbl_node(self) -> str:
        return self._t('node.editor.lbl.node', 'Node:')

    def lbl_port(self) -> str:
        return self._t('node.editor.lbl.port', 'Port:')

    def lbl_allowed_connections(self) -> str:
        return self._t('node.editor.lbl.allowed', 'Allowed connections:')

    def cap_unlimited(self) -> str:
        return self._t('node.editor.cap.unlimited', 'unlimited (∞)')

    def cap_na(self) -> str:
        return self._t('node.editor.cap.na', 'n/a')

    def side_label(self, side: str) -> str:
        if side == "input":
            return self._t('node.editor.side.input', 'Input')
        if side == "output":
            return self._t('node.editor.side.output', 'Output')
        return side

    def hint_click_start(self) -> str:
        return self._t('node.editor.hint.click_start', 'Click: start a new connection')

    def hint_ctrl_click_rewire(self) -> str:
        return self._t('node.editor.hint.ctrl_rewire', 'Ctrl+Click: rewire/detach existing')

    def port_tooltip(self, node_name: str, side_label: str, prop_id: str, cap_str: str) -> str:
        return (
            f"{self.lbl_node()} {node_name}\n"
            f"{self.lbl_port()} {side_label} • {prop_id}\n"
            f"{self.lbl_allowed_connections()} {cap_str}\n\n"
            f"{self.hint_click_start()}\n"
            f"{self.hint_ctrl_click_rewire()}"
        )

    def port_capacity_tooltip(self, cap_text: str) -> str:
        return f"{self.lbl_allowed_connections()} (IN/OUT): {cap_text}"