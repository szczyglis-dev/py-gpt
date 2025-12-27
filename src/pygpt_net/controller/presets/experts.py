#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.12.27 21:00:00                  #
# ================================================== #

from PySide6 import QtCore

from pygpt_net.core.types import (
    MODE_EXPERT,
)
from pygpt_net.utils import trans


class Experts:
    def __init__(self, window=None):
        """
        Experts controller

        :param window: Window instance
        """
        self.window = window
        self.selected_available_uuids = []  # multi-selected available experts
        self.selected_selected_uuids = []   # multi-selected selected experts

    def refresh(self):
        """Refresh presets"""
        pass

    def get_current_agent_id(self) -> str:
        """
        Get current agent UUID

        :return: agent UUID
        """
        return self.window.controller.presets.editor.current

    def is_active(self, uuid: str) -> bool:
        """
        Check if expert is active in current agent

        :param uuid: expert uuid
        :return: bool
        """
        agent_uuid = self.get_current_agent_id()
        if agent_uuid is None:
            return False
        agent = self.window.core.presets.get_by_uuid(agent_uuid)
        if agent is None:
            return False
        return uuid in agent.experts

    def update_list(self):
        """Update presets list"""
        items = self.window.core.presets.get_by_mode(MODE_EXPERT)
        items_data = {}
        for item in items:
            if item.startswith("current.") or self.is_active(items[item].uuid):
                continue
            items_data[item] = items[item]
        self.window.ui.nodes['preset.editor.experts'].update_available(items_data)  # update available
        current_agent = self.get_current_agent_id()
        if current_agent is not None:
            agent = self.window.core.presets.get_by_uuid(current_agent)
            if agent is None:
                return
            experts = {}
            for expert_uuid in agent.experts:
                expert = self.window.core.presets.get_by_uuid(expert_uuid)
                if expert is None:
                    continue
                experts[expert_uuid] = expert
            self.window.ui.nodes['preset.editor.experts'].update_selected(experts)  # update selected
        else:
            # clear selected list if no agent is selected
            self.window.ui.nodes['preset.editor.experts'].update_selected({})

        self.update_tab()

    def _selected_uuids_from_view(self, node_id: str, fallback_idx_resolver) -> list[str]:
        """
        Resolve selected expert UUIDs from a given list view using stored tooltip role,
        falling back to idx -> uuid resolver when needed.

        :param node_id: ui node id
        :param fallback_idx_resolver: callable that maps row index -> uuid
        :return: list of selected uuids
        """
        uuids = []
        try:
            view = self.window.ui.nodes[node_id]
            sel_model = view.selectionModel()
            rows = sel_model.selectedRows() if sel_model else []
            for ix in rows:
                uuid = ix.data(QtCore.Qt.ToolTipRole)
                if not uuid:
                    uuid = fallback_idx_resolver(ix.row())
                if uuid and uuid not in uuids:
                    uuids.append(uuid)
        except Exception:
            pass
        return uuids

    def change_available(self):
        """Change selected expert(s) in available list"""
        self.selected_available_uuids = self._selected_uuids_from_view(
            "preset.experts.available",
            self.get_available_by_idx
        )

    def change_selected(self):
        """Change selected expert(s) in selected list"""
        self.selected_selected_uuids = self._selected_uuids_from_view(
            "preset.experts.selected",
            self.get_selected_by_idx
        )

    def get_current_available(self) -> str:
        """
        Get current available expert

        :return: expert uuid
        """
        val = self.window.ui.nodes["preset.experts.available"].selectionModel().currentIndex()
        idx = val.row()
        return self.get_available_by_idx(idx)

    def get_current_selected(self) -> str:
        """
        Get current selected expert

        :return: expert uuid
        """
        val = self.window.ui.nodes["preset.experts.selected"].selectionModel().currentIndex()
        idx = val.row()
        return self.get_selected_by_idx(idx)

    def get_available_by_idx(self, idx):
        """
        Get available expert by index

        :param idx: index
        """
        presets = self.window.core.presets.get_by_mode(MODE_EXPERT)
        i = 0
        for preset in presets:
            if preset.startswith("current.") or self.is_active(presets[preset].uuid):
                continue
            if i == idx:
                return presets[preset].uuid
            i += 1

    def get_selected_by_idx(self, idx):
        """
        Get selected expert by index

        :param idx: index
        """
        agent_uuid = self.get_current_agent_id()
        agent = self.window.core.presets.get_by_uuid(agent_uuid)
        if agent is None:
            return None
        i = 0
        for expert_uuid in agent.experts:
            if i == idx:
                return expert_uuid
            i += 1

    def add_expert(self):
        """Add expert(s)"""
        agent_uuid = self.get_current_agent_id()
        if agent_uuid is None or not self.window.core.presets.exists_uuid(agent_uuid):
            self.window.controller.presets.editor.save(close=False)
            return

        uuids = self.selected_available_uuids[:]
        if not uuids:
            one = self.get_current_available()
            if one:
                uuids = [one]

        if not uuids:
            return

        for expert_uuid in uuids:
            if expert_uuid and not self.is_active(expert_uuid):
                self.window.core.presets.add_expert(agent_uuid, expert_uuid)

        self.update_list()

    def remove_expert(self):
        """Remove expert(s)"""
        agent_uuid = self.get_current_agent_id()
        if agent_uuid is None or not self.window.core.presets.exists_uuid(agent_uuid):
            self.window.controller.presets.editor.save(close=False)
            return

        uuids = self.selected_selected_uuids[:]
        if not uuids:
            one = self.get_current_selected()
            if one:
                uuids = [one]

        if not uuids:
            return

        for expert_uuid in uuids:
            if expert_uuid and self.is_active(expert_uuid):
                self.window.core.presets.remove_expert(agent_uuid, expert_uuid)

        self.update_list()

    def update_tab(self):
        """Update experts tab label with number of experts"""
        num = 0
        agent_uuid = self.get_current_agent_id()
        if agent_uuid:
            agent = self.window.core.presets.get_by_uuid(agent_uuid)
            if agent:
                num = len(agent.experts)
        tabs = self.window.ui.tabs['preset.editor.tabs']
        idx = self.window.controller.presets.editor.TAB_IDX["experts"]
        if num == 0:
            tabs.setTabText(idx, trans("preset.tab.experts"))
        else:
            tabs.setTabText(idx, trans("preset.tab.experts") + f" ({num})")