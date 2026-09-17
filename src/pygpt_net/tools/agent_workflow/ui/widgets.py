#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.17 18:05:00                  #
# ================================================== #

from __future__ import annotations

import json
import os

from PySide6.QtCore import QTimer
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QVBoxLayout, QPushButton, QWidget

from pygpt_net.utils import trans


class WorkflowView(QWebEngineView):
    def __init__(self, window=None):
        super().__init__(window)
        self.window = window
        self._loaded = False
        self._pending_snapshot = None
        self.loadFinished.connect(self._on_loaded)
        self.build()

    def _labels(self) -> dict:
        return {
            "empty": trans("agent_workflow.empty"),
            "details": trans("agent_workflow.details"),
            "hide": trans("agent_workflow.hide_details"),
            "system_prompt": trans("agent_workflow.system_prompt"),
            "input": trans("agent_workflow.input"),
            "instruction": trans("agent_workflow.instruction"),
            "task": trans("agent_workflow.task"),
            "language": trans("agent_workflow.language"),
            "model": trans("agent_workflow.model"),
            "provider": trans("agent_workflow.provider"),
            "preset": trans("agent_workflow.preset"),
            "mode": trans("agent_workflow.mode"),
            "running_task": trans("agent_workflow.event.running_task"),
            "creating_agent": trans("agent_workflow.event.creating_agent"),
            "agent_created": trans("agent_workflow.event.agent_created"),
            "status": trans("agent_workflow.event.status"),
            "running_tool": trans("agent_workflow.event.running_tool"),
            "completed": trans("agent_workflow.event.completed"),
            "failed": trans("agent_workflow.event.failed"),
            "stopped": trans("agent_workflow.event.stopped"),
            "removed": trans("agent_workflow.event.removed"),
            "finalizing": trans("agent_workflow.event.finalizing"),
            "tool_input": trans("agent_workflow.tool.input"),
            "tool_output": trans("agent_workflow.tool.output"),
            "state_created": trans("agent_workflow.state.created"),
            "state_running": trans("agent_workflow.state.running"),
            "state_stopping": trans("agent_workflow.state.stopping"),
            "state_completed": trans("agent_workflow.state.completed"),
            "state_failed": trans("agent_workflow.state.failed"),
            "state_stopped": trans("agent_workflow.state.stopped"),
            "state_removed": trans("agent_workflow.state.removed"),
            "state_cancelled": trans("agent_workflow.state.cancelled"),
            "state_provider": trans("agent_workflow.state.provider"),
        }

    def _css(self) -> str:
        fonts_path = os.path.join(self.window.core.config.get_app_path(), "data", "fonts").replace("\\", "/")
        base = self.window.controller.theme.markdown.get_web_css().replace("%fonts%", fonts_path)
        path = os.path.join(self.window.core.config.get_app_path(), "data", "css", "agent_workflow.css")
        custom = ""
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    custom = fh.read()
            except OSError:
                custom = ""
        theme = self.window.controller.theme.common.normalize_theme(
            self.window.core.config.get("theme")
        )
        return base + "\n" + custom.replace("%theme%", str(theme or "dark"))

    def _html(self) -> str:
        labels = json.dumps(self._labels(), ensure_ascii=False).replace("</", "<\\/")
        css = self._css()
        return f"""<!doctype html>
<html>
<head>
<meta charset=\"utf-8\">
<style>{css}</style>
</head>
<body class=\"agent-workflow theme-%theme%\">
<div id=\"workflow\"></div>
<script>
const WF_LABELS = {labels};
let WF_LAST = null;

function wfEl(tag, cls, text) {{
    const el = document.createElement(tag);
    if (cls) el.className = cls;
    if (text !== undefined && text !== null) el.textContent = String(text);
    return el;
}}
function wfHas(value) {{
    if (value === null || value === undefined) return false;
    return String(value).trim() !== '';
}}
function wfNearBottom() {{
    const d = document.documentElement;
    return (window.innerHeight + window.scrollY) >= (Math.max(d.scrollHeight, document.body.scrollHeight) - 100);
}}
function wfScrollBottom() {{
    const h = Math.max(document.documentElement.scrollHeight, document.body.scrollHeight);
    window.scrollTo(0, h);
}}
function wfOpenSet(selector, attr) {{
    return new Set(Array.from(document.querySelectorAll(selector)).filter(x => !x.hidden).map(x => x.getAttribute(attr)));
}}
function wfToggle(button, panel) {{
    panel.hidden = !panel.hidden;
    button.textContent = panel.hidden ? WF_LABELS.details : WF_LABELS.hide;
}}
function wfSetAgentCollapsed(card, collapsed) {{
    if (!card) return;
    card.classList.toggle('agent-collapsed', Boolean(collapsed));
    const title = card.querySelector(':scope > .agent-header > .agent-title');
    const toggle = title ? title.querySelector('.agent-collapse-toggle') : null;
    if (title) title.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
    if (toggle) toggle.textContent = collapsed ? '▸' : '▾';
}}
function wfToggleAgent(card) {{
    wfSetAgentCollapsed(card, !card.classList.contains('agent-collapsed'));
}}
function wfState(value) {{
    const key = 'state_' + String(value || '').toLowerCase();
    return WF_LABELS[key] || String(value || '');
}}
function wfDuration(ms) {{
    let total = Math.max(0, Math.floor(Number(ms || 0) / 1000));
    const hours = Math.floor(total / 3600);
    total -= hours * 3600;
    const minutes = Math.floor(total / 60);
    const seconds = total - minutes * 60;
    const parts = [];
    if (hours > 0) parts.push(hours + 'h');
    if (minutes > 0) parts.push(minutes + 'm');
    if (seconds > 0 || parts.length === 0) parts.push(seconds + 's');
    return parts.join(' ');
}}
function wfTimerElapsed(timer, now) {{
    const base = Math.max(0, Number(timer.getAttribute('data-elapsed-ms') || 0));
    const activeSince = Number(timer.getAttribute('data-active-since-ms') || 0);
    if (!activeSince) return base;
    return base + Math.max(0, Number(now || Date.now()) - activeSince);
}}
function wfUpdateTimer(timer, now) {{
    if (!timer) return;
    timer.textContent = wfDuration(wfTimerElapsed(timer, now));
}}
function wfUpdateTimers() {{
    const now = Date.now();
    document.querySelectorAll('.agent-elapsed').forEach(timer => wfUpdateTimer(timer, now));
}}
function wfTryParseJson(value) {{
    if (typeof value !== 'string') return {{ok: false, value: value}};
    const text = value.trim();
    if (text.length < 2) return {{ok: false, value: value}};
    const first = text[0];
    const last = text[text.length - 1];
    if (!((first === '{{' && last === '}}') || (first === '[' && last === ']'))) {{
        return {{ok: false, value: value}};
    }}
    try {{
        return {{ok: true, value: JSON.parse(text)}};
    }} catch (e) {{
        return {{ok: false, value: value}};
    }}
}}
function wfNormalizeStructured(value, depth) {{
    const level = depth || 0;
    if (level > 10) return value;
    if (typeof value === 'string') {{
        const parsed = wfTryParseJson(value);
        return parsed.ok ? wfNormalizeStructured(parsed.value, level + 1) : value;
    }}
    if (Array.isArray(value)) {{
        return value.map(item => wfNormalizeStructured(item, level + 1));
    }}
    if (value && typeof value === 'object') {{
        const normalized = {{}};
        Object.entries(value).forEach(([key, item]) => {{
            normalized[key] = wfNormalizeStructured(item, level + 1);
        }});
        return normalized;
    }}
    return value;
}}
function wfFormatToolValue(value) {{
    if (value === null || value === undefined) return '';
    const normalized = wfNormalizeStructured(value, 0);
    if (normalized && typeof normalized === 'object') {{
        try {{
            return JSON.stringify(normalized, null, 2);
        }} catch (e) {{}}
    }}
    return String(normalized);
}}
function wfDetailRow(label, value) {{
    if (!wfHas(value)) return null;
    const row = wfEl('div', 'detail-row');
    row.appendChild(wfEl('div', 'detail-label', label));
    row.appendChild(wfEl('pre', 'detail-value', value));
    return row;
}}
function wfAgentDetails(agent, snapshot) {{
    const box = wfEl('div', 'agent-details');
    box.hidden = true;
    const d = agent.details || {{}};
    const rows = [];
    if (agent.id === snapshot.root_id) {{
        rows.push(wfDetailRow(WF_LABELS.mode, snapshot.mode));
        rows.push(wfDetailRow(WF_LABELS.model, snapshot.model));
        rows.push(wfDetailRow(WF_LABELS.provider, snapshot.provider));
        rows.push(wfDetailRow(WF_LABELS.preset, snapshot.preset));
    }}
    rows.push(wfDetailRow(WF_LABELS.instruction, d.instruction));
    rows.push(wfDetailRow(WF_LABELS.task, d.task));
    rows.push(wfDetailRow(WF_LABELS.language, d.language));
    rows.push(wfDetailRow(WF_LABELS.input, d.input));
    rows.push(wfDetailRow(WF_LABELS.system_prompt, d.system_prompt));
    rows.filter(Boolean).forEach(row => box.appendChild(row));
    return box;
}}
function wfToolDetails(event) {{
    const panel = wfEl('div', 'tool-details');
    panel.hidden = true;
    const input = wfDetailRow(WF_LABELS.tool_input, wfFormatToolValue(event.tool_input));
    const output = wfDetailRow(WF_LABELS.tool_output, wfFormatToolValue(event.tool_output));
    if (input) panel.appendChild(input);
    if (output) panel.appendChild(output);
    return panel;
}}
function wfEventRow(event) {{
    const wrap = wfEl('div', 'event-wrap event-' + (event.kind || 'event'));
    const row = wfEl('div', 'event-row');
    row.appendChild(wfEl('span', 'turn', '#' + String(event.turn || 1)));
    row.appendChild(wfEl('span', 'time', event.time || ''));

    let message = event.message || '';
    if (event.kind === 'running') message = WF_LABELS.running_task;
    else if (event.kind === 'status') message = WF_LABELS.status + ': ' + message;
    else if (event.kind === 'agent_create') message = WF_LABELS.creating_agent + ': ' + (event.agent_name || message);
    else if (event.kind === 'created') message = WF_LABELS.agent_created;
    else if (event.kind === 'tool') message = WF_LABELS.running_tool + ': ' + (event.tool || message) + '...';
    else if (event.kind === 'finalizing') message = WF_LABELS.finalizing;
    else if (event.kind === 'completed') message = WF_LABELS.completed;
    else if (event.kind === 'failed' && !message) message = WF_LABELS.failed;
    else if (event.kind === 'stopped' && message === 'removed') message = WF_LABELS.removed;
    else if (event.kind === 'stopped' && !message) message = WF_LABELS.stopped;

    row.appendChild(wfEl('span', 'event-message', message));
    if (event.kind === 'tool') {{
        const state = event.tool_state || 'running';
        row.appendChild(wfEl('span', 'tool-state tool-state-' + state, wfState(state)));
        if (wfHas(event.tool_input) || wfHas(event.tool_output)) {{
            const button = wfEl('button', 'details-button tool-details-button', WF_LABELS.details);
            button.type = 'button';
            row.appendChild(button);
            const panel = wfToolDetails(event);
            panel.setAttribute('data-tool-event', String(event.id));
            button.addEventListener('click', () => wfToggle(button, panel));
            wrap.appendChild(row);
            wrap.appendChild(panel);
            return wrap;
        }}
    }} else if (event.kind === 'agent_create' && (wfHas(event.instruction) || wfHas(event.system_prompt) || wfHas(event.task))) {{
        const button = wfEl('button', 'details-button create-details-button', WF_LABELS.details);
        button.type = 'button';
        row.appendChild(button);
        const panel = wfEl('div', 'tool-details create-details');
        panel.hidden = true;
        const a = wfDetailRow(WF_LABELS.instruction, event.instruction);
        const b = wfDetailRow(WF_LABELS.task, event.task);
        const c = wfDetailRow(WF_LABELS.system_prompt, event.system_prompt);
        [a,b,c].filter(Boolean).forEach(x => panel.appendChild(x));
        panel.setAttribute('data-create-event', String(event.id));
        button.addEventListener('click', () => wfToggle(button, panel));
        wrap.appendChild(row);
        wrap.appendChild(panel);
        return wrap;
    }}
    wrap.appendChild(row);
    return wrap;
}}
function wfRenderAgent(snapshot, id, openAgents, openTools, openCreates, collapsedAgents) {{
    const agent = (snapshot.agents || {{}})[id];
    if (!agent) return null;
    const card = wfEl('section', 'agent-card agent-role-' + (agent.role || 'worker'));
    card.setAttribute('data-agent', id);

    const header = wfEl('div', 'agent-header');
    const title = wfEl('div', 'agent-title');
    title.setAttribute('role', 'button');
    title.setAttribute('tabindex', '0');
    title.setAttribute('aria-expanded', 'true');
    title.setAttribute('title', agent.name || id);
    title.appendChild(wfEl('span', 'agent-collapse-toggle', '▾'));
    const displayName = agent.name || id;
    title.appendChild(wfEl('span', 'agent-name', '[' + displayName + ']'));
    if (id !== snapshot.root_id && id && id !== displayName) {{
        title.appendChild(wfEl('span', 'agent-id', '(' + id + ')'));
    }}
    if (agent.status) title.appendChild(wfEl('span', 'agent-status agent-status-' + agent.status, wfState(agent.status)));
    const elapsedMs = Math.max(0, Number(agent.elapsed_ms || 0));
    const activeSinceMs = Math.max(0, Number(agent.active_since_ms || 0));
    if (elapsedMs > 0 || activeSinceMs > 0) {{
        const timer = wfEl('span', 'agent-elapsed');
        timer.setAttribute('data-elapsed-ms', String(elapsedMs));
        timer.setAttribute('data-active-since-ms', String(activeSinceMs));
        wfUpdateTimer(timer, Date.now());
        title.appendChild(timer);
    }}
    header.appendChild(title);
    title.addEventListener('click', () => wfToggleAgent(card));
    title.addEventListener('keydown', (event) => {{
        if (event.key === 'Enter' || event.key === ' ') {{
            event.preventDefault();
            wfToggleAgent(card);
        }}
    }});

    const details = wfAgentDetails(agent, snapshot);
    if (details.childElementCount > 0) {{
        const button = wfEl('button', 'details-button agent-details-button', WF_LABELS.details);
        button.type = 'button';
        header.appendChild(button);
        button.addEventListener('click', (event) => {{
            event.stopPropagation();
            if (card.classList.contains('agent-collapsed')) {{
                wfSetAgentCollapsed(card, false);
                details.hidden = false;
                button.textContent = WF_LABELS.hide;
                return;
            }}
            wfToggle(button, details);
        }});
        if (openAgents.has(id)) {{ details.hidden = false; button.textContent = WF_LABELS.hide; }}
    }}
    card.appendChild(header);
    if (details.childElementCount > 0) card.appendChild(details);

    const timeline = wfEl('div', 'timeline');
    (agent.events || []).forEach(event => {{
        const row = wfEventRow(event);
        timeline.appendChild(row);
        const toolPanel = row.querySelector('[data-tool-event]');
        if (toolPanel && openTools.has(toolPanel.getAttribute('data-tool-event'))) {{
            toolPanel.hidden = false;
            const b = row.querySelector('.tool-details-button');
            if (b) b.textContent = WF_LABELS.hide;
        }}
        const createPanel = row.querySelector('[data-create-event]');
        if (createPanel && openCreates.has(createPanel.getAttribute('data-create-event'))) {{
            createPanel.hidden = false;
            const b = row.querySelector('.create-details-button');
            if (b) b.textContent = WF_LABELS.hide;
        }}
    }});
    card.appendChild(timeline);

    const children = (snapshot.order || []).filter(childId => {{
        const child = (snapshot.agents || {{}})[childId];
        return child && child.parent_id === id;
    }});
    if (children.length) {{
        const childBox = wfEl('div', 'agent-children');
        children.forEach(childId => {{
            const child = wfRenderAgent(snapshot, childId, openAgents, openTools, openCreates, collapsedAgents);
            if (child) childBox.appendChild(child);
        }});
        card.appendChild(childBox);
    }}
    if (collapsedAgents && collapsedAgents.has(id)) wfSetAgentCollapsed(card, true);
    return card;
}}
function renderWorkflow(snapshot) {{
    WF_LAST = snapshot || {{}};
    const follow = wfNearBottom();
    const openAgents = wfOpenSet('.agent-details:not([hidden])', 'data-agent-detail');
    const collapsedAgents = new Set();
    // Preserve expanded Details panels and collapsed agent subtrees across live re-renders.
    document.querySelectorAll('.agent-card').forEach(card => {{
        const p = card.querySelector(':scope > .agent-details');
        if (p && !p.hidden) openAgents.add(card.getAttribute('data-agent'));
        if (card.classList.contains('agent-collapsed')) collapsedAgents.add(card.getAttribute('data-agent'));
    }});
    const openTools = wfOpenSet('[data-tool-event]:not([hidden])', 'data-tool-event');
    const openCreates = wfOpenSet('[data-create-event]:not([hidden])', 'data-create-event');
    const root = document.getElementById('workflow');
    root.replaceChildren();
    const agents = snapshot && snapshot.agents ? snapshot.agents : {{}};
    const rootId = snapshot ? snapshot.root_id : null;
    if (!rootId || !agents[rootId]) {{
        root.appendChild(wfEl('div', 'workflow-empty', WF_LABELS.empty));
        return;
    }}
    const tree = wfRenderAgent(snapshot, rootId, openAgents, openTools, openCreates, collapsedAgents);
    if (tree) root.appendChild(tree);
    wfUpdateTimers();
    if (follow) requestAnimationFrame(wfScrollBottom);
}}
setInterval(wfUpdateTimers, 1000);
</script>
</body>
</html>""".replace("%theme%", str(self.window.controller.theme.common.normalize_theme(self.window.core.config.get("theme")) or "dark"))

    def build(self):
        self._loaded = False
        self.setHtml(self._html(), baseUrl="file://")

    def _on_loaded(self, ok: bool):
        self._loaded = bool(ok)
        snapshot = self._pending_snapshot
        if snapshot is None:
            snapshot = self.window.core.agent_workflow.snapshot()
        self.render(snapshot)

    def render(self, snapshot: dict):
        self._pending_snapshot = snapshot
        if not self._loaded or self.page() is None:
            return
        payload = json.dumps(snapshot or {}, ensure_ascii=False, default=str).replace("</", "<\\/")
        self.page().runJavaScript(f"renderWorkflow({payload});")

    def reload_content(self):
        snapshot = self.window.core.agent_workflow.snapshot()
        self._pending_snapshot = snapshot
        self.build()

    def on_delete(self):
        try:
            self.loadFinished.disconnect(self._on_loaded)
        except Exception:
            pass
        try:
            self.setHtml("<html><body></body></html>")
        except Exception:
            pass


class WorkflowWidget(QWidget):
    def __init__(self, window=None, tool=None, parent=None):
        super().__init__(parent)
        self.window = window
        self.tool = tool
        self.tab = None
        self.view = WorkflowView(window)
        self.btn_clear = QPushButton(trans("agent_workflow.btn.clear"))
        self.btn_clear.clicked.connect(self.window.controller.agent_workflow.clear)

        layout = QVBoxLayout()
        layout.addWidget(self.view, stretch=1)
        layout.addWidget(self.btn_clear, stretch=0)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        signals = self.window.controller.agent_workflow.signals
        signals.changed.connect(self._on_changed)
        signals.reload.connect(self.reload)
        QTimer.singleShot(0, lambda: self._on_changed(self.window.core.agent_workflow.snapshot()))

    def set_tab(self, tab):
        self.tab = tab

    def _on_changed(self, snapshot: dict):
        self.view.render(snapshot)

    def reload(self):
        self.btn_clear.setText(trans("agent_workflow.btn.clear"))
        self.view.reload_content()

    def on_delete(self):
        signals = self.window.controller.agent_workflow.signals
        try:
            signals.changed.disconnect(self._on_changed)
        except Exception:
            pass
        try:
            signals.reload.disconnect(self.reload)
        except Exception:
            pass
        if self.view is not None:
            self.view.on_delete()
