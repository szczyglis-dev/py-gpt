#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.19 00:00:00                  #
# ================================================== #

from datetime import datetime
from typing import Dict

from PySide6 import QtCore
from PySide6.QtGui import QAction, QIcon

from pygpt_net.tools.base import BaseTool
from pygpt_net.utils import trans

from .ui.dialogs import Builder

class AgentBuilder(BaseTool):
    def __init__(self, *args, **kwargs):
        """
        Agent builder (nodes editor)

        :param window: Window instance
        """
        super(AgentBuilder, self).__init__(*args, **kwargs)
        self.id = "agent_builder"
        self.opened = False
        self.dialog = None  # dialog
        self.initialized = False
        self.current_agent = None  # current agent ID

    def setup(self):
        """Setup controller"""
        pass

    def update(self):
        """Update"""
        pass

    def save(self):
        """Save layout to file"""
        if "agent.builder" not in self.window.ui.editor:
            return
        custom = self.window.core.agents.custom
        layout = self.window.ui.editor["agent.builder"].save_layout()
        custom.update_layout(layout)
        if self.current_agent:
            custom.update_agent_layout(self.current_agent, layout)
        custom.save()
        self.window.update_status(f"Saved at: {datetime.now().strftime('%H:%M:%S')}")

    def load(self):
        """Load layout from file"""
        self.restore()

    def open(self):
        """Open dialog"""
        if not self.initialized:
            self.dialog = Builder(self.window, tool=self)
            self.dialog.setup()
            self.restore()
            self.initialized = True
        self.window.ui.dialogs.open('agent.builder', width=900, height=600)
        self.opened = True
        self.update()

    def close(self):
        """Close dialog"""
        self.window.ui.dialogs.close('agent.builder')
        self.opened = False

    def toggle(self):
        """Toggle dialog window"""
        if self.opened:
            self.close()
        else:
            self.open()

    def store_current(self):
        """Store current to file"""
        self.save()

    def restore(self):
        """Restore layout and agents from file"""
        layout = self.window.core.agents.custom.get_layout()
        if layout:
            data = layout.data
            if data:
                self.window.ui.editor["agent.builder"].load_layout(data)
                self.window.update_status(f"Loaded layout at: {datetime.now().strftime('%H:%M:%S')}")

        self.update_list()

        # select first agent on list
        agents = self.window.core.agents.custom.get_agents()
        if agents and len(agents) > 0:
            first_agent_id = list(agents.keys())[0]
            self.edit_agent(first_agent_id)

    def show_hide(self, show: bool = True):
        """
        Show/hide dialog window

        :param show: show/hide
        """
        if show:
            self.open()
        else:
            self.close()

    def on_close(self):
        """On window close"""
        self.opened = False
        self.update()

    def on_exit(self):
        """On exit"""
        self.store_current()

    def clear(self, force: bool = False):
        """
        Clear layout

        :param force: force clear
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='agent.builder.agent.clear',
                id=0,
                msg=trans('agent.builder.confirm.clear.msg'),
            )
            return
        if self.window.ui.editor["agent.builder"].clear(ask_user=False):
            self.save()

    def add_agent(self, name: str = None):
        """Add new agent"""
        if name is None:
            self.window.ui.dialog['create'].id = 'agent.builder.agent'
            self.window.ui.dialog['create'].input.setText("")
            self.window.ui.dialog['create'].current = ""
            self.window.ui.dialog['create'].show()
            self.window.ui.dialog['create'].input.setFocus()
            return
        uuid = self.window.core.agents.custom.new_agent(name)
        if uuid:
            self.update_list()
            self.window.ui.editor["agent.builder"].clear(ask_user=False)
            self.window.ui.dialogs.close('create')
            self.edit_agent(uuid)

    def rename_agent(self, agent_id: str, name: str = None):
        """
        Rename agent

        :param agent_id: agent ID
        :param name: new name
        """
        agent = self.window.core.agents.custom.get_agent(agent_id)
        if not agent:
            print("Agent not found:", agent_id)
            return
        current_name = agent.name
        if name is None:
            self.window.ui.dialog['rename'].id = 'agent.builder.agent'
            self.window.ui.dialog['rename'].input.setText(current_name)
            self.window.ui.dialog['rename'].current =agent_id
            self.window.ui.dialog['rename'].show()
            self.window.ui.dialog['rename'].input.setFocus()
            return
        if agent:
            agent.name = name
            self.window.core.agents.custom.save()
            self.update_list()
            self.window.ui.dialogs.close('rename')

    def edit_agent(self, agent_id: str):
        """
        Edit agent

        :param agent_id: agent ID
        """
        self.save()
        self.current_agent = agent_id
        agent = self.window.core.agents.custom.get_agent(agent_id)
        if agent:
            layout = agent.layout
            if layout:
                self.window.ui.editor["agent.builder"].load_layout(layout)
            else:
                self.window.ui.editor["agent.builder"].clear(ask_user=False)
            self.select_on_list(agent_id)

    def duplicate_agent(self, agent_id: str):
        """
        Duplicate agent

        :param agent_id: agent ID
        """
        agent = self.window.core.agents.custom.get_agent(agent_id)
        if agent:
            new_name = f"{agent.name} (copy)"
            self.window.core.agents.custom.duplicate_agent(agent_id, new_name)
            self.update_list()

    def delete_agent(self, agent_id: str, force: bool = False):
        """
        Delete agent

        :param agent_id: agent ID
        :param force: force delete without confirmation
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='agent.builder.agent.delete',
                id=agent_id,
                msg=trans('agent.builder.confirm.delete.msg'),
            )
            return
        self.window.core.agents.custom.delete_agent(agent_id)
        self.update_list()
        if self.current_agent == agent_id:
            self.current_agent = None
            self.window.ui.editor["agent.builder"].clear(ask_user=False)

    def update_list(self):
        """Update agents list"""
        data = self.window.core.agents.custom.get_agents()
        self.window.ui.nodes["agent.builder.list"].update_list(data)

    def select_on_list(self, agent_id: str):
        """
        Select agent on list

        :param agent_id: agent ID
        """
        nodes = self.window.ui.nodes
        models = self.window.ui.models

        agents_list = nodes["agent.builder.list"].list
        model = models.get("agent.builder.list")

        if model is None:
            return
        for row in range(model.rowCount()):
            idx = model.index(row, 0)
            if str(model.data(idx, QtCore.Qt.UserRole)) == str(agent_id):
                agents_list.setCurrentIndex(idx)
                sm = agents_list.selectionModel()
                if sm:
                    sm.select(idx, QtCore.QItemSelectionModel.ClearAndSelect)
                agents_list.scrollTo(idx)
                break

    def setup_menu(self) -> Dict[str, QAction]:
        """
        Setup main menu

        :return dict with menu actions
        """
        actions = {}
        actions["agent.builder"] = QAction(
            QIcon(":/icons/robot.svg"),
            trans("menu.tools.agent.builder"),
            self.window,
            checkable=False,
        )
        actions["agent.builder"].triggered.connect(
            lambda: self.toggle()
        )
        return actions

    def setup_dialogs(self):
        """Setup dialogs (static)"""
        pass

    def get_lang_mappings(self) -> Dict[str, Dict]:
        """
        Get language mappings

        :return: dict with language mappings
        """
        return {
            'menu.text': {
                'tools.agent.builder': 'menu.tools.agent.builder',
            }
        }