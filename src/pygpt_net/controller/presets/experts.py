#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.21 20:00:00                  #
# ================================================== #

from pygpt_net.core.types import (
    MODE_EXPERT,
)

class Experts:
    def __init__(self, window=None):
        """
        Experts controller

        :param window: Window instance
        """
        self.window = window

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

    def change_available(self):
        """Change selected expert"""
        pass

    def change_selected(self):
        """Change selected expert"""
        pass

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
        """Add expert"""
        agent_uuid = self.get_current_agent_id()
        if agent_uuid is None or not self.window.core.presets.exists_uuid(agent_uuid):
            self.window.controller.presets.editor.save(close=False)
            return
        expert_uuid = self.get_current_available()
        if expert_uuid is None:
            return
        self.window.core.presets.add_expert(agent_uuid, expert_uuid)
        self.update_list()

    def remove_expert(self):
        """Remove expert"""
        agent_uuid = self.get_current_agent_id()
        if agent_uuid is None or not self.window.core.presets.exists_uuid(agent_uuid):
            self.window.controller.presets.editor.save(close=False)
            return
        expert_uuid = self.get_current_selected()
        if expert_uuid is None:
            return
        self.window.core.presets.remove_expert(agent_uuid, expert_uuid)
        self.update_list()

