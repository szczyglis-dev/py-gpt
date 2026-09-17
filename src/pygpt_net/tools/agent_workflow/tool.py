#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.17 14:45:00                  #
# ================================================== #

from typing import Dict

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QWidget

from pygpt_net.core.events import BaseEvent, RenderEvent
from pygpt_net.core.tabs.tab import Tab
from pygpt_net.core.types import MODE_AGENT_V2
from pygpt_net.tools.base import BaseTool
from pygpt_net.utils import trans

from .ui.dialogs import Tool
from .ui.widgets import WorkflowWidget


class AgentWorkflow(BaseTool):
    """Live Agents v2 workflow monitor."""

    ONBOARDING_KEY = "agent.v2.workflow_tool.shown"
    DEFAULT_COLUMN = 1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = "agent_workflow"
        self.has_tab = True
        self.tab_title = "menu.tools.agent_workflow"
        self.tab_icon = ":/icons/router.svg"
        self.opened = False
        self.dialog = None

    def handle(self, event: BaseEvent):
        if event.name == RenderEvent.ON_THEME_CHANGE:
            self.window.controller.agent_workflow.reload()

    def _find_tab(self):
        """Return the first Agent Workflow tab from the runtime tab registry."""
        for tab in self.window.core.tabs.pids.values():
            if tab.type == Tab.TAB_TOOL and tab.tool_id == self.id:
                return tab
        return None

    def show_on_first_agent_run(self) -> bool:
        """Reveal Agent Workflow in column 2 once, when the first Agents v2 run starts."""
        cfg = self.window.core.config
        # RUNTIME INIT is shared by other Agents v2-backed features (e.g. Experts).
        # The onboarding belongs only to the user-facing Chat with Agents mode.
        if cfg.get("mode") != MODE_AGENT_V2:
            return False
        if bool(cfg.get(self.ONBOARDING_KEY, False)):
            return False

        tabs_controller = self.window.controller.ui.tabs
        if not getattr(tabs_controller, "initialized", False):
            return False

        previous_column = tabs_controller.get_current_column_idx()
        tab = self._find_tab()
        if tab is None:
            idx = self.window.core.tabs.get_max_idx_by_column(self.DEFAULT_COLUMN)
            tabs_controller.append(
                type=Tab.TAB_TOOL,
                tool_id=self.id,
                idx=idx,
                column_idx=self.DEFAULT_COLUMN,
            )
            tab = self._find_tab()

        if tab is None:
            return False

        if not tabs_controller.is_split_screen_enabled():
            tabs_controller.enable_split_screen(update_switch=True)

        tabs_controller.switch_tab_by_idx(tab.idx, tab.column_idx)
        if previous_column != tab.column_idx:
            tabs_controller.on_column_focus(previous_column)

        cfg.set(self.ONBOARDING_KEY, True)
        self.window.core.tabs.save()
        return True

    def open(self):
        self.opened = True
        self.window.ui.dialogs.open("agent_workflow", width=900, height=650)
        self.dialog.widget.reload()

    def close(self):
        self.opened = False
        self.window.ui.dialogs.close("agent_workflow")

    def toggle(self):
        if self.opened:
            self.close()
        else:
            self.open()

    def setup_menu(self) -> Dict[str, QAction]:
        action = QAction(
            QIcon(self.tab_icon),
            trans("menu.tools.agent_workflow"),
            self.window,
            checkable=False,
        )
        action.triggered.connect(self.toggle)
        return {"agent_workflow": action}

    def setup_dialogs(self):
        self.dialog = Tool(self.window, self)
        self.dialog.setup()

    def as_tab(self, tab: Tab) -> QWidget:
        widget = WorkflowWidget(self.window, self)
        widget.set_tab(tab)
        return widget

    def on_reload(self):
        self.window.controller.agent_workflow.reload()

    def get_lang_mappings(self) -> Dict[str, Dict]:
        return {
            "menu.text": {
                "tools.agent_workflow": "menu.tools.agent_workflow",
            },
            "dialog.title": {
                "agent_workflow": "dialog.agent_workflow.title",
            },
        }
