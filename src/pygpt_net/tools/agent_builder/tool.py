#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.24 00:00:00                  #
# ================================================== #

import copy
from datetime import datetime
from typing import Dict

from PySide6 import QtCore
from PySide6.QtGui import QAction, QIcon

from pygpt_net.tools.base import BaseTool
from pygpt_net.utils import trans

from pygpt_net.core.node_editor.types import (
    NodeTypeRegistry,
    PropertySpec,
    NodeTypeSpec
)

from .ui.dialogs import Builder


class AgentBuilder(BaseTool):
    def __init__(self, *args, **kwargs):
        super(AgentBuilder, self).__init__(*args, **kwargs)
        self.id = "agent_builder"
        self.opened = False
        self.dialog = None  # dialog
        self.initialized = False
        self.current_agent = None  # current agent ID
        # Reentrancy/teardown guards
        self._restoring = False    # True while restore/load is in progress
        self._closing = False      # True while dialog is being closed

    def setup(self):
        """Setup controller"""
        pass

    def update(self):
        """Update"""
        pass

    def save(self, force: bool = False):
        """Save layout to file"""
        # Never save during restore or teardown
        if not self.opened or self._closing or self._restoring:
            if not force:
                return
        if "agent.builder" not in self.window.ui.editor:
            return

        builder = self.window.ui.editor["agent.builder"]
        # Ensure the editor is alive (not closing)
        if not getattr(builder, "_alive", True) or getattr(builder, "_closing", False):
            return

        data = builder.save_layout()
        if not isinstance(data, dict):
            return  # skip invalid snapshots

        schema_list = builder.export_schema(as_list=True)
        try:
            # Deep copy for safety (JSON-only types expected)
            layout = copy.deepcopy(data)
            schema = copy.deepcopy(schema_list)
        except Exception:
            # As a fallback, store raw references (still pure dict/list)
            layout = data
            schema = schema_list

        custom = self.window.core.agents.custom
        custom.update_layout(layout)
        if self.current_agent:
            custom.update_agent(self.current_agent, layout, schema)
        custom.save()
        self.window.update_status(f"Saved at: {datetime.now().strftime('%H:%M:%S')}")
        self.update_presets()

    def load(self):
        """Load layout from file"""
        self.restore()

    def open(self):
        """Open dialog"""
        self.dialog = Builder(self.window, tool=self)
        self.dialog.setup()
        # Defer restore to allow previous deleteLater() to be processed
        QtCore.QTimer.singleShot(0, self.restore)
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

    def store_current(self, force: bool = False):
        """Store current to file"""
        if self.opened and not self._restoring and (not self._closing or force):
            self.save(force=force)

    def restore(self):
        """Restore layout and agents from file"""
        if self._closing:
            return
        self._restoring = True
        try:
            layout = self.window.core.agents.custom.get_layout()
            if layout and "agent.builder" in self.window.ui.editor:
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
        finally:
            self._restoring = False

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
        """On dialog window close (before destroy)"""
        self._closing = True
        try:
            self.store_current(force=True)
        finally:
            self.opened = False
            self._closing = False

    def on_exit(self):
        """On app exit"""
        if self.opened:
            self.on_close()

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
        if "agent.builder" in self.window.ui.editor:
            if self.window.ui.editor["agent.builder"].clear(ask_user=False):
                self.save()

    def add_agent(self, name: str = None):
        """Add new agent"""
        if name is None:
            dialog = self.window.ui.dialog['create']
            dialog.id = 'agent.builder.agent'
            dialog.input.setText("")
            dialog.current = ""
            dialog.show()
            dialog.input.setFocus()
            return

        if self.current_agent:
            self.save()  # save current before creating new

        self.current_agent = None # prevent overwriting current agent
        uuid = self.window.core.agents.custom.new_agent(name)
        if uuid:
            self.update_list()
            if "agent.builder" in self.window.ui.editor:
                self.window.ui.editor["agent.builder"].clear(ask_user=False)
            self.window.ui.dialogs.close('create')
            self.edit_agent(uuid)
            self.update_presets()

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
            dialog = self.window.ui.dialog['rename']
            dialog.id = 'agent.builder.agent'
            dialog.input.setText(current_name)
            dialog.current =agent_id
            dialog.show()
            dialog.input.setFocus()
            return
        if agent:
            agent.name = name
            self.window.core.agents.custom.save()
            self.update_list()
            self.window.ui.dialogs.close('rename')
            self.update_presets()

    def edit_agent(self, agent_id: str):
        """
        Edit agent

        :param agent_id: agent ID
        """
        # Save current agent only when switching and UI is stable
        if (
            self.current_agent
            and self.current_agent != agent_id
            and self.opened
            and not self._restoring
            and not self._closing
            and "agent.builder" in self.window.ui.editor
        ):
            builder = self.window.ui.editor["agent.builder"]
            if getattr(builder, "_alive", True) and not getattr(builder, "_closing", False):
                self.save()

        self.current_agent = agent_id

        if "agent.builder" not in self.window.ui.editor:
            return

        agent = self.window.core.agents.custom.get_agent(agent_id)
        if agent:
            editor = self.window.ui.editor["agent.builder"]
            layout = agent.layout
            if layout:
                editor.load_layout(layout)
            else:
                editor.clear(ask_user=False)

            # Select on list only when the list exists (dialog open)
            if "agent.builder.list" in self.window.ui.nodes:
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

        # if deleted current, clear editor
        if self.current_agent == agent_id:
            self.current_agent = None
            if "agent.builder" in self.window.ui.editor:
                self.window.ui.editor["agent.builder"].clear(ask_user=False)

            # select current selected on list if any after deletion (only if UI is open)
            if self.opened and "agent.builder.list" in self.window.ui.nodes:
                agents = self.window.core.agents.custom.get_agents()
                if agents and len(agents) > 0:
                    idx = self.window.ui.nodes["agent.builder.list"].list.currentIndex()
                    if idx.isValid():
                        next_id = idx.data(QtCore.Qt.UserRole)
                        self.edit_agent(next_id)

    def editing_allowed(self) -> bool:
        """
        Check if editing is enabled (dialog is open and not closing/restoring)

        :return: True if editing is enabled
        """
        return self.opened and not self._closing and not self._restoring and self.current_agent is not None

    def update_presets(self):
        """Update presets in the tools"""
        self.window.controller.presets.editor.reload_all(all=True)

    def update_list(self):
        """Update agents list"""
        # Guard: dialog may not be open; do nothing if widget is not present
        if "agent.builder.list" not in self.window.ui.nodes:
            return
        data = self.window.core.agents.custom.get_agents()
        self.window.ui.nodes["agent.builder.list"].update_list(data)

    def select_on_list(self, agent_id: str):
        """
        Select agent on list

        :param agent_id: agent ID
        """
        if "agent.builder.list" not in self.window.ui.nodes:
            return

        nodes = self.window.ui.nodes
        models = self.window.ui.models

        agents_list = nodes["agent.builder.list"].list
        model = models.get("agent.builder.list")

        if model is None or agents_list is None:
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

    def get_registry(self) -> NodeTypeRegistry:
        """
        Get node type registry

        :return: NodeTypeRegistry
        """
        registry = NodeTypeRegistry(empty=True)
        # Tip: to allow multiple connections to an input or output, set allowed_inputs/allowed_outputs to -1.

        # Start
        registry.register(NodeTypeSpec(
            type_name="Flow/Start",
            title="Start",
            base_id="start",
            export_kind="start",
            bg_color="#2D5A27",
            properties=[
                PropertySpec(id="output", type="flow", name="Output", editable=False, allowed_inputs=0,
                             allowed_outputs=1),
                PropertySpec(id="memory", type="memory", name="Memory", editable=False, allowed_inputs=0,
                             allowed_outputs=-1),
                # base_id will be auto-injected as read-only property at creation
            ],
        ))
        # Agent
        registry.register(NodeTypeSpec(
            type_name="Flow/Agent",
            title="Agent",
            base_id="agent",
            export_kind="agent",
            bg_color="#304A6E",
            properties=[
                PropertySpec(id="name", type="str", name="Name", editable=True, value=""),
                PropertySpec(id="instruction", type="text", name="Instruction", editable=True, value=""),
                PropertySpec(id="remote_tools", type="bool", name="Remote tools", editable=True, value=True),
                PropertySpec(id="local_tools", type="bool", name="Local tools", editable=True, value=True),
                PropertySpec(id="input", type="flow", name="Input", editable=False, allowed_inputs=-1,
                             allowed_outputs=0),
                PropertySpec(id="output", type="flow", name="Output", editable=False, allowed_inputs=0,
                             allowed_outputs=-1),
                PropertySpec(id="memory", type="memory", name="Memory", editable=False, allowed_inputs=0,
                             allowed_outputs=1),
            ],
        ))
        # Memory
        registry.register(NodeTypeSpec(
            type_name="Flow/Memory",
            title="Memory (Context)",
            base_id="mem",
            export_kind="memory",
            bg_color="#593E78",
            properties=[
                PropertySpec(id="name", type="str", name="Name", editable=True, value=""),
                PropertySpec(id="input", type="memory", name="Agent", editable=False, allowed_inputs=-1,
                             allowed_outputs=0),
            ],
        ))
        # End
        registry.register(NodeTypeSpec(
            type_name="Flow/End",
            title="End",
            base_id="end",
            export_kind="end",
            bg_color="#6B2E2E",
            properties=[
                PropertySpec(id="input", type="flow", name="Input", editable=False, allowed_inputs=-1,
                             allowed_outputs=0),
            ],
        ))
        return registry

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