#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczyglinski                  #
# Updated Date: 2026.09.18 10:02:00                  #
# ================================================== #

from __future__ import annotations

from typing import Any, Dict, Optional

from PySide6.QtCore import Qt

from pygpt_net.core.agents_v2.mode import (
    AGENT_MODE_CONFIG_DEFAULT,
    AGENT_MODE_CONFIG_KEY,
    AgentMode,
)
from pygpt_net.utils import trans


class Editor:
    """Controller for the Chat with Agents profile editor."""

    def __init__(self, window=None):
        self.window = window
        self.dialog = False
        self.current: Optional[str] = None
        # Unsaved editor state is kept per workflow. Switching the list must not
        # write to config, nor should it discard text already entered by user.
        self.drafts: Dict[str, Dict[str, str]] = {}
        self._force_close = False
        self.width = 980
        self.height = 760

    def setup(self):
        if getattr(self.window, "agents_v2_editor", None) is not None:
            self.window.agents_v2_editor.setup()
        self.refresh_toolbox()

    def reload(self):
        if self.dialog:
            self._capture_current()
        self.refresh_toolbox()
        if self.dialog:
            self.reload_items(select_id=self.current)

    def toggle_editor(self):
        if self.dialog:
            self.close()
        else:
            self.open()

    def open(self):
        if "agents.v2.editor" not in self.window.ui.dialog:
            self.setup()
        # Drafts are scoped to one visible editor session only.
        self.drafts.clear()
        self.reload_items(select_id=self.current)
        self.window.ui.dialogs.open(
            "agents.v2.editor",
            width=self.width,
            height=self.height,
        )
        self.dialog = True

    def close(self, force: bool = False) -> bool:
        """Close the editor, asking before discarding real unsaved changes."""
        if not self.dialog:
            return True
        if not force and self.has_unsaved_changes():
            self._confirm_close()
            return False

        self._force_close = True
        try:
            self.window.ui.dialogs.close("agents.v2.editor")
        finally:
            self._force_close = False
        return True

    def allow_close_event(self) -> bool:
        """Handle ESC/window-manager close before QDialog accepts the event."""
        if self._force_close:
            self._finish_close()
            return True
        if self.has_unsaved_changes():
            self._confirm_close()
            return False
        self._finish_close()
        return True

    def _finish_close(self):
        """Discard session drafts after the dialog is actually being closed."""
        self.drafts.clear()
        self.dialog = False

    def _confirm_close(self):
        self.window.ui.dialogs.confirm(
            type="agents_v2.editor.close",
            id=None,
            msg=trans("agents.editor.close.confirm"),
            modal=True,
        )

    def has_unsaved_changes(self) -> bool:
        """Return True only when draft/form values differ from persisted config."""
        self._capture_current()
        for agent_id, draft in self.drafts.items():
            row = self.window.core.agents_v2.editor.editable_values(agent_id)
            if row is None:
                continue

            if str(draft.get("system_prompt") or "") != str(row.get("system_prompt") or ""):
                return True

            if row.get("built_in"):
                continue

            if str(draft.get("name") or "").strip() != str(row.get("name") or "").strip():
                return True
            draft_runtime = self.window.core.agents_v2.editor.normalize_runtime(
                draft.get("runtime")
            )
            saved_runtime = self.window.core.agents_v2.editor.normalize_runtime(
                row.get("runtime")
            )
            if draft_runtime != saved_runtime:
                return True
        return False

    def _capture_current(self):
        """Keep current form values in memory without touching persisted config."""
        if not self.current:
            return
        row = self.window.core.agents_v2.editor.get(self.current)
        if row is None:
            return
        name_node = self.window.ui.nodes.get("agents.v2.editor.name")
        prompt_node = self.window.ui.nodes.get("agents.v2.editor.prompt")
        self.drafts[self.current] = {
            "name": str(name_node.text() if name_node is not None else ""),
            "system_prompt": str(prompt_node.toPlainText() if prompt_node is not None else ""),
            "runtime": self._selected_runtime().value,
        }

    def _runtime_buttons(self) -> Dict[AgentMode, Any]:
        nodes = self.window.ui.nodes
        return {
            AgentMode.PRIMARY_AGENT: nodes.get("agents.v2.editor.runtime.primary"),
            AgentMode.ORCHESTRATOR: nodes.get("agents.v2.editor.runtime.orchestrator"),
            AgentMode.SWARM: nodes.get("agents.v2.editor.runtime.swarm"),
        }

    def _selected_runtime(self) -> AgentMode:
        for mode, button in self._runtime_buttons().items():
            if button is not None and button.isChecked():
                return mode
        return AgentMode.ORCHESTRATOR

    def _set_runtime(self, runtime: Any, enabled: bool):
        mode = self.window.core.agents_v2.editor.normalize_runtime(runtime)
        for candidate, button in self._runtime_buttons().items():
            if button is None:
                continue
            blocked = button.blockSignals(True)
            button.setChecked(candidate == mode)
            button.setEnabled(bool(enabled))
            button.blockSignals(blocked)

    def runtime_changed(self, runtime: Any, checked: bool = True):
        """Store a custom workflow runtime change in the in-memory draft."""
        if not checked or not self.current:
            return
        row = self.window.core.agents_v2.editor.get(self.current)
        if row is None or row.get("built_in"):
            return
        self._capture_current()

    def _editable_values(self, agent_id: Any) -> Optional[dict]:
        """Return draft values first, falling back to the persisted editor state."""
        row = self.window.core.agents_v2.editor.editable_values(agent_id)
        if row is None:
            return None
        agent_id = str(row["id"])
        draft = self.drafts.get(agent_id)
        if draft is not None:
            row.update(draft)
        return row

    def _display_name(self, row: dict) -> str:
        if row.get("built_in"):
            key = str(row.get("label_key") or "")
            return trans(key) if key else str(row.get("name") or "")
        return str(row.get("name") or row.get("id") or "")

    def refresh_toolbox(self):
        combo = self.window.ui.nodes.get("agent.v2.mode")
        if combo is None:
            return
        configured = str(
            self.window.core.config.get(AGENT_MODE_CONFIG_KEY, AGENT_MODE_CONFIG_DEFAULT)
            or AGENT_MODE_CONFIG_DEFAULT
        ).strip()
        selected_id, _, _ = self.window.core.agents_v2.editor.resolve_selection(configured)
        blocked = combo.blockSignals(True)
        combo.clear()
        for row in self.window.core.agents_v2.editor.get_agents():
            combo.addItem(self._display_name(row), row["id"])
        idx = combo.findData(selected_id)
        if idx < 0:
            idx = combo.findData(AGENT_MODE_CONFIG_DEFAULT)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        combo.blockSignals(blocked)

    def reload_items(self, select_id: Optional[str] = None):
        widget = self.window.ui.nodes.get("agents.v2.editor.list")
        if widget is None:
            return
        target = select_id or self.current
        widget.blockSignals(True)
        widget.clear()
        selected_item = None
        first_item = None
        for row in self.window.core.agents_v2.editor.get_agents():
            item = widget.make_item(
                agent_id=row["id"],
                name=self._display_name(row),
                built_in=bool(row.get("built_in")),
            )
            widget.addItem(item)
            if first_item is None:
                first_item = item
            if row["id"] == target:
                selected_item = item
        widget.blockSignals(False)
        item = selected_item or first_item
        if item is not None:
            widget.setCurrentItem(item)
            self.select(str(item.data(Qt.UserRole) or ""))
        else:
            self.current = None
            self._clear_fields()

    def select(self, agent_id: Any):
        wanted = str(agent_id or "").strip()
        if self.current and wanted != self.current:
            self._capture_current()
        row = self._editable_values(wanted)
        if row is None:
            return
        self.current = str(row["id"])
        name = self.window.ui.nodes.get("agents.v2.editor.name")
        prompt = self.window.ui.nodes.get("agents.v2.editor.prompt")
        if name is not None:
            name.setText(self._display_name(row) if row.get("built_in") else str(row.get("name") or ""))
            name.setReadOnly(bool(row.get("built_in")))
        if prompt is not None:
            prompt.setPlainText(str(row.get("system_prompt") or ""))
            prompt.setPlaceholderText(
                self.window.core.agents_v2.editor.get_default_main_prompt(self.current)
                if row.get("built_in")
                else ""
            )
        self._set_runtime(
            row.get("runtime_mode") if row.get("built_in") else row.get("runtime"),
            enabled=not bool(row.get("built_in")),
        )
        self._update_info(row)

    def _clear_fields(self):
        for key in ("agents.v2.editor.name", "agents.v2.editor.prompt"):
            node = self.window.ui.nodes.get(key)
            if node is not None and hasattr(node, "clear"):
                node.clear()
        prompt = self.window.ui.nodes.get("agents.v2.editor.prompt")
        if prompt is not None:
            prompt.setPlaceholderText("")
        self._set_runtime(AgentMode.ORCHESTRATOR, enabled=False)

    def _update_info(self, row: dict):
        info = self.window.ui.nodes.get("agents.v2.editor.info")
        prompt_desc = self.window.ui.nodes.get("agents.v2.editor.prompt.desc")
        if row.get("built_in"):
            if info is not None:
                info.setText(trans("agents.editor.builtin.info"))
            if prompt_desc is not None:
                key = str(row.get("description_key") or "")
                prompt_desc.setText(trans(key) if key else "")
        else:
            if info is not None:
                info.setText(trans("agents.editor.custom.info"))
            if prompt_desc is not None:
                prompt_desc.setText(trans("agents.editor.custom.prompt.desc"))

    def new(self):
        self._capture_current()
        agent_id = self.window.core.agents_v2.editor.create(trans("agents.editor.new.name"))
        self.window.core.config.save()
        self.current = agent_id
        self.reload_items(select_id=agent_id)
        self.refresh_toolbox()
        name = self.window.ui.nodes.get("agents.v2.editor.name")
        if name is not None:
            name.setFocus()
            name.selectAll()

    def save(self) -> bool:
        if not self.current:
            return False

        self._capture_current()
        if not self.drafts:
            return False

        # Validate everything before mutating config, so one invalid custom name
        # cannot leave the in-memory config only partially updated.
        for agent_id, draft in self.drafts.items():
            row = self.window.core.agents_v2.editor.get(agent_id)
            if row is None:
                continue
            if not row.get("built_in") and not str(draft.get("name") or "").strip():
                self.select(agent_id)
                self.window.ui.dialogs.alert(trans("agents.editor.name.required"))
                return False

        for agent_id, draft in list(self.drafts.items()):
            row = self.window.core.agents_v2.editor.get(agent_id)
            if row is None:
                continue
            ok = self.window.core.agents_v2.editor.save(
                agent_id,
                name=str(draft.get("name") or "").strip(),
                system_prompt=str(draft.get("system_prompt") or ""),
                runtime=str(draft.get("runtime") or AgentMode.ORCHESTRATOR.value),
            )
            if not ok:
                return False

        self.window.core.config.save()
        self.drafts.clear()
        self.reload_items(select_id=self.current)
        self.refresh_toolbox()
        self.window.update_status(trans("status.saved"))
        return True

    def delete(self, agent_id: Any = None, force: bool = False):
        wanted = str(agent_id or self.current or "").strip()
        row = self.window.core.agents_v2.editor.get(wanted)
        if row is None or row.get("built_in"):
            return
        if not force:
            self.window.ui.dialogs.confirm(
                type="agents_v2.editor.delete",
                id=wanted,
                msg=trans("agents.editor.delete.confirm"),
            )
            return
        previous = self.current
        if previous and previous != wanted:
            self._capture_current()
        if not self.window.core.agents_v2.editor.delete(wanted):
            return
        self.drafts.pop(wanted, None)
        configured = str(self.window.core.config.get(AGENT_MODE_CONFIG_KEY, "") or "")
        if configured == wanted:
            self.window.core.config.set(AGENT_MODE_CONFIG_KEY, AGENT_MODE_CONFIG_DEFAULT)
        self.window.core.config.save()
        self.current = None if previous == wanted else previous
        self.reload_items(select_id=self.current)
        self.refresh_toolbox()

    def load_defaults(self, force: bool = False, agent_id: Any = None):
        wanted = str(agent_id or self.current or "").strip()
        if not wanted:
            return
        if wanted != self.current:
            self.select(wanted)
        if not self.current:
            return
        prompt = self.window.ui.nodes.get("agents.v2.editor.prompt")
        has_text = bool(prompt is not None and prompt.toPlainText().strip())
        if has_text and not force:
            self.window.ui.dialogs.confirm(
                type="agents_v2.editor.defaults",
                id=self.current,
                msg=trans("agents.editor.defaults.confirm"),
            )
            return
        if prompt is not None:
            # Defaults are now one complete prompt: role + execution/step-by-step
            # rules + security/runtime policy. Custom profiles receive no hidden
            # workflow policy injection after this text is copied.
            prompt.setPlainText(
                self.window.core.agents_v2.editor.get_default_main_prompt(
                    self.current,
                    runtime=self._selected_runtime(),
                )
            )


class AgentsV2:
    def __init__(self, window=None):
        self.window = window
        self.editor = Editor(window)

    def setup(self):
        self.editor.setup()

    def reload(self):
        self.editor.reload()
