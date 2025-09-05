#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.05 18:00:00                  #
# ================================================== #

import re
from typing import Optional, List, Dict

from PySide6.QtCore import QTimer
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QTextEdit

from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_ASSISTANT,
    MODE_CHAT,
    MODE_EXPERT,
    MODE_AGENT_OPENAI,
)
from pygpt_net.controller.presets.editor import Editor
from pygpt_net.core.events import AppEvent
from pygpt_net.item.preset import PresetItem
from pygpt_net.utils import trans


_FILENAME_SANITIZE_RE = re.compile(r'[^a-zA-Z0-9_\-\.]')
_VALIDATE_FILENAME_RE = re.compile(r'[^\w\s\-\.]')


class Presets:
    def __init__(self, window=None):
        """
        Presets controller

        :param window: Window instance
        """
        self.window = window
        self.editor = Editor(window)
        self.locked = False
        self.selected = []

    def setup(self):
        """Setup presets"""
        self.editor.setup()

    def on_changed(self):
        """Handle change event"""
        pass

    def is_bot(self) -> bool:
        """
        Check if current preset is bot

        :return: True if bot
        """
        w = self.window
        cfg = w.core.config
        if cfg.get('mode') != MODE_AGENT_OPENAI:
            return False
        preset_id = cfg.get('preset')
        if not preset_id or preset_id == "*":
            return False
        preset_data = w.core.presets.get_by_id(MODE_AGENT_OPENAI, preset_id)
        return bool(
            preset_data
            and preset_data.agent_openai
            and preset_data.agent_provider_openai
            and preset_data.agent_provider_openai.startswith("openai_agent_bot")
        )

    def select(self, idx: int):
        """
        Select preset

        :param idx: value of the list (row idx)
        """
        if self.preset_change_locked():
            return
        w = self.window
        mode = w.core.config.get('mode')
        self.set_by_idx(mode, idx)
        preset_id = w.core.config.get('preset')
        w.controller.ui.update()
        w.controller.model.select_current()
        w.dispatch(AppEvent(AppEvent.PRESET_SELECTED))
        self.set_selected(idx)
        editor_ctrl = w.controller.presets.editor
        if editor_ctrl.opened and editor_ctrl.current != preset_id:
            self.editor.init(preset_id)

    def get_current(self) -> Optional[PresetItem]:
        """
        Get current preset

        :return: preset item
        """
        w = self.window
        cfg = w.core.config
        preset_id = cfg.get('preset')
        mode = cfg.get('mode')
        if preset_id and w.core.presets.has(mode, preset_id):
            return w.core.presets.get_by_id(mode, preset_id)
        return None

    def next(self):
        """Select next preset"""
        nodes = self.window.ui.nodes
        models = self.window.ui.models
        count = models['preset.presets'].rowCount()
        if count <= 0:
            return
        idx = (nodes['preset.presets'].currentIndex().row() + 1) % count
        self.select(idx)

    def prev(self):
        """Select previous preset"""
        nodes = self.window.ui.nodes
        models = self.window.ui.models
        count = models['preset.presets'].rowCount()
        if count <= 0:
            return
        idx = (nodes['preset.presets'].currentIndex().row() - 1) % count
        self.select(idx)

    def use(self):
        """Copy preset prompt to input"""
        w = self.window
        w.controller.chat.common.append_to_input(
            w.ui.nodes['preset.prompt'].toPlainText()
        )

    def paste_prompt(
            self,
            idx: int,
            parent: str = "global"
    ):
        """
        Paste prompt from template

        :param idx: prompt index
        :param parent: parent name
        """
        w = self.window
        template = w.core.prompt.template.get_by_id(idx)
        if template is None:
            return
        target = None
        if parent == "global":
            target = w.ui.nodes['preset.prompt']
        elif parent == "input":
            target = w.ui.nodes['input']
        elif parent == "editor":
            target = w.ui.config["preset"]["prompt"]
        if target is not None:
            self.paste_to_textarea(target, template['prompt'])

    def paste_custom_prompt(
            self,
            idx: int,
            parent: str = "global"
    ):
        """
        Paste prompt from custom template

        :param idx: prompt index
        :param parent: parent name
        """
        w = self.window
        template = w.core.prompt.custom.get_by_id(idx)
        if template is None:
            return
        target = None
        if parent == "global":
            target = w.ui.nodes['preset.prompt']
        elif parent == "input":
            target = w.ui.nodes['input']
        elif parent == "editor":
            target = w.ui.config["preset"]["prompt"]
        if target is not None:
            self.paste_to_textarea(target, template.content)

    def save_prompt(
            self,
            name: str = "",
            force: bool = False
    ):
        """
        Save prompt to file

        :param name: prompt name
        :param force: force save
        """
        w = self.window
        content = w.ui.nodes['input'].toPlainText()
        if content.strip() == "":
            w.update_status("Prompt is empty!")
            return
        if not force:
            dlg = w.ui.dialog['rename']
            dlg.id = 'prompt.custom.new'
            dlg.input.setText(content[:40] + "...")
            dlg.current = ""
            dlg.show()
            return
        w.ui.dialog['rename'].close()
        w.core.prompt.custom.new(name, content)
        w.update_status("Prompt saved")

    def rename_prompt(
            self,
            uuid: str,
            name: str = "",
            force: bool = False
    ):
        """
        Rename prompt

        :param uuid: prompt ID
        :param name: new name
        :param force: force rename
        """
        w = self.window
        item = w.core.prompt.custom.get_by_id(uuid)
        if item is None:
            return
        if not force:
            dlg = w.ui.dialog['rename']
            dlg.id = 'prompt.custom.rename'
            dlg.input.setText(item.name)
            dlg.current = uuid
            dlg.show()
            return
        w.ui.dialog['rename'].close()
        item.name = name
        w.core.prompt.custom.save()
        w.update_status("Prompt renamed")

    def delete_prompt(
            self,
            uuid: str,
            force: bool = False
    ):
        """
        Delete prompt

        :param uuid: prompt ID
        :param force: force delete
        """
        w = self.window
        item = w.core.prompt.custom.get_by_id(uuid)
        if item is None:
            return
        if not force:
            dlg = w.ui.dialog['confirm']
            dlg.type = 'prompt.custom.delete'
            dlg.id = uuid
            dlg.message = "Are you sure you want to delete this prompt?"
            dlg.show()
            return
        w.ui.dialog['confirm'].close()
        w.core.prompt.custom.delete(uuid)
        w.update_status("Prompt deleted")

    def paste_to_textarea(
            self,
            textarea: QTextEdit,
            text: str
    ):
        """
        Paste text to textarea

        :param textarea: textarea widget
        :param text: text to paste
        """
        prev_text = textarea.toPlainText()
        cur = textarea.textCursor()
        cur.beginEditBlock()
        cur.movePosition(QTextCursor.End)
        txt = str(text).strip()
        if prev_text.strip() != "":
            cur.insertText("\n")
        if txt:
            cur.insertText(txt)
        cur.endEditBlock()
        textarea.setTextCursor(cur)
        textarea.setFocus()

    def set(
            self,
            mode: str,
            preset_id: str
    ):
        """
        Set preset

        :param mode: mode name
        :param preset_id: preset ID
        """
        w = self.window
        if not w.core.presets.has(mode, preset_id):
            return False
        w.core.config.data['preset'] = preset_id
        if 'current_preset' not in w.core.config.data:
            w.core.config.data['current_preset'] = {}
        w.core.config.data['current_preset'][mode] = preset_id

    def set_by_idx(
            self,
            mode: str,
            idx: int
    ):
        """
        Set preset by index

        :param mode: mode name
        :param idx: preset index
        """
        w = self.window
        preset_id = w.core.presets.get_by_idx(idx, mode)
        w.core.config.set("preset", preset_id)
        if 'current_preset' not in w.core.config.data:
            w.core.config.data['current_preset'] = {}
        w.core.config.data['current_preset'][mode] = preset_id
        self.select_model()

    def select_current(self, no_scroll: bool = False):
        """
        Select preset by current

        :param no_scroll: do not scroll to current preset
        """
        w = self.window
        cfg = w.core.config
        mode = cfg.get('mode')
        preset_id = cfg.get('preset')
        if not preset_id:
            return
        idx = w.core.presets.get_idx_by_id(mode, preset_id)
        if idx is None or idx < 0:
            return
        if no_scroll:
            w.ui.nodes['preset.presets'].store_scroll_position()
        w.ui.nodes['preset.presets'].select_by_idx(idx)
        if no_scroll:
            w.ui.nodes['preset.presets'].restore_scroll_position()
        editor_ctrl = w.controller.presets.editor
        if editor_ctrl.opened and editor_ctrl.current != preset_id:
            self.editor.init(preset_id)

    def select_default(self):
        """Set default preset"""
        w = self.window
        cfg = w.core.config
        preset_id = cfg.get('preset')
        if not preset_id:
            mode = cfg.get('mode')
            current = cfg.get('current_preset')
            if mode in current and current[mode] and current[mode] in w.core.presets.get_by_mode(mode):
                cfg.set('preset', current[mode])
            else:
                cfg.set('preset', w.core.presets.get_default(mode))
            new_id = cfg.get('preset')
            editor_ctrl = w.controller.presets.editor
            if editor_ctrl.opened and editor_ctrl.current != new_id:
                self.editor.init(new_id)

    def update_data(self):
        """Update preset data"""
        w = self.window
        cfg = w.core.config
        preset_id = cfg.get('preset')
        if not preset_id:
            self.reset()
            w.controller.mode.reset_current()
            return
        if preset_id not in w.core.presets.items:
            cfg.set('preset', "")
            self.reset()
            w.controller.mode.reset_current()
            return
        preset = w.core.presets.items[preset_id]
        w.ui.nodes['preset.prompt'].setPlainText(preset.prompt)
        w.core.config.set('prompt', preset.prompt)
        w.core.config.set('ai_name', preset.ai_name)
        w.core.config.set('user_name', preset.user_name)
        w.core.config.set('agent.llama.provider', preset.agent_provider)
        w.core.config.set('agent.openai.provider', preset.agent_provider_openai)
        w.core.config.set('agent.llama.idx', preset.idx)

    def update_current(self):
        """Update current mode, model and preset"""
        w = self.window
        cfg = w.core.config
        mode = cfg.get('mode')
        preset_id = cfg.get('preset')
        if preset_id and preset_id in w.core.presets.items:
            preset = w.core.presets.items[preset_id]
            cfg.set('user_name', preset.user_name)
            cfg.set('ai_name', preset.ai_name)
            cfg.set('prompt', preset.prompt)
            cfg.set('temperature', preset.temperature)
            cfg.set('agent.llama.provider', preset.agent_provider)
            cfg.set('agent.openai.provider', preset.agent_provider_openai)
            cfg.set('agent.llama.idx', preset.idx)
            return
        cfg.set('user_name', None)
        cfg.set('ai_name', None)
        cfg.set('temperature', 1.0)
        if mode == MODE_CHAT:
            cfg.set('prompt', w.core.prompt.get('default'))
        else:
            cfg.set('prompt', None)

    def get_current_functions(self) -> Optional[List[Dict]]:
        """
        Get current preset functions

        :return: list of functions
        """
        w = self.window
        preset_id = w.core.config.get('preset')
        if preset_id and preset_id in w.core.presets.items:
            preset = w.core.presets.items[preset_id]
            if preset.has_functions():
                return preset.get_functions()
        return None

    def from_global(self):
        """Update current preset from global prompt"""
        if self.locked:
            return
        w = self.window
        preset_id = w.core.config.get('preset')
        if preset_id and preset_id in w.core.presets.items:
            preset = w.core.presets.items[preset_id]
            preset.prompt = w.core.config.get('prompt')
            w.core.presets.save(preset_id)

    def select_model(self):
        """Select model by current preset"""
        w = self.window
        cfg = w.core.config
        mode = cfg.get('mode')
        preset_id = cfg.get('preset')
        if not preset_id or preset_id not in w.core.presets.items:
            return
        preset = w.core.presets.items[preset_id]
        model = preset.model
        if not model or model == "_":
            return
        models = w.core.models
        if models.has(model) and models.is_allowed(model, mode):
            if cfg.get('model') == model:
                return
            cfg.set('model', model)
            w.controller.model.set(mode, model)
            w.controller.model.init_list()
            w.controller.model.select_current()

    def refresh(self, no_scroll: bool = False):
        """
        Refresh presets

        :param no_scroll: do not scroll to current
        """
        w = self.window
        if w.core.config.get('mode') == MODE_ASSISTANT:
            return
        if no_scroll:
            w.ui.nodes['preset.presets'].store_scroll_position()
        self.select_default()
        self.update_current()
        self.update_data()
        w.controller.mode.update_temperature()
        self.update_list()
        self.select_current()
        if no_scroll:
            w.ui.nodes['preset.presets'].restore_scroll_position()
        self.on_changed()

    def update_list(self):
        """Update presets list"""
        w = self.window
        mode = w.core.config.get('mode')
        items = w.core.presets.get_by_mode(mode)
        w.ui.toolbox.presets.update_presets(items)
        self.clear_selected()

    def reset(self):
        """Reset preset data"""
        self.window.ui.nodes['preset.prompt'].setPlainText("")

    def make_filename(self, name: str) -> str:
        """
        Make preset filename from name

        :param name: preset name
        :return: preset filename
        """
        return _FILENAME_SANITIZE_RE.sub('_', name.lower())

    def duplicate(self, idx: Optional[int] = None):
        """
        Duplicate preset

        :param idx: preset index (row index)
        """
        if idx is not None:
            w = self.window
            mode = w.core.config.get('mode')
            preset = w.core.presets.get_by_idx(idx, mode)
            if preset:
                if preset in w.core.presets.items:
                    new_id = w.core.presets.duplicate(preset)
                    self.update_list()
                    self.refresh(no_scroll=True)
                    idx = w.core.presets.get_idx_by_id(mode, new_id)
                    self.editor.edit(idx)
                    self.select(idx) # switch to the new preset
                    w.update_status(trans('status.preset.duplicated'))

    def enable(self, idx: Optional[int] = None):
        """
        Enable preset

        :param idx: preset index (row index)
        """
        if idx is not None:
            w = self.window
            mode = w.core.config.get('mode')
            preset_id = w.core.presets.get_by_idx(idx, mode)
            if preset_id and preset_id in w.core.presets.items:
                w.core.presets.enable(preset_id)
                QTimer.singleShot(100, self.refresh)

    def disable(self, idx: Optional[int] = None):
        """
        Disable preset

        :param idx: preset index (row index)
        """
        if idx is not None:
            w = self.window
            mode = w.core.config.get('mode')
            preset_id = w.core.presets.get_by_idx(idx, mode)
            if preset_id and preset_id in w.core.presets.items:
                w.core.presets.disable(preset_id)
                QTimer.singleShot(100, self.refresh)

    def clear(self, force: bool = False):
        """
        Clear preset data

        :param force: force clear data
        """
        w = self.window
        preset = w.core.config.get('preset')
        if not force:
            w.ui.dialogs.confirm(
                type='preset_clear',
                id='',
                msg=trans('confirm.preset.clear'),
            )
            return
        w.core.config.set('prompt', "")
        w.core.config.set('ai_name', "")
        w.core.config.set('user_name', "")
        w.core.config.set('temperature', 1.0)
        if preset and preset in w.core.presets.items:
            p = w.core.presets.items[preset]
            p.ai_name = ""
            p.user_name = ""
            p.prompt = ""
            p.temperature = 1.0
            self.refresh()
        w.update_status(trans('status.preset.cleared'))
        mode = w.core.config.get('mode')
        if mode == MODE_ASSISTANT:
            w.core.assistants.load()

    def delete(
            self,
            idx: Optional[int] = None,
            force: bool = False
    ):
        """
        Delete preset

        :param idx: preset index (row index)
        :param force: force delete without confirmation
        """
        if idx is not None:
            w = self.window
            mode = w.core.config.get('mode')
            preset_id = w.core.presets.get_by_idx(idx, mode)
            if preset_id and preset_id in w.core.presets.items:
                if not force:
                    w.ui.dialogs.confirm(
                        type='preset_delete',
                        id=idx,
                        msg=trans('confirm.preset.delete'),
                    )
                    return
                if preset_id == w.core.config.get('preset'):
                    w.core.config.set('preset', None)
                    w.ui.nodes['preset.prompt'].setPlainText("")
                w.core.presets.remove(preset_id, True)
                self.refresh(no_scroll=True)
                w.update_status(trans('status.preset.deleted'))

    def restore(self, force: bool = False):
        """
        Restore preset data

        :param force: force restore data
        """
        w = self.window
        if not force:
            w.ui.dialogs.confirm(
                type='preset_restore',
                id='',
                msg=trans('confirm.preset.restore'),
            )
            return
        mode = w.core.config.get('mode')
        if mode == MODE_AGENT:
            mode = MODE_EXPERT
        w.core.presets.restore(mode)
        self.refresh()

    def is_current(self, idx: Optional[int] = None) -> bool:
        """
        Check if preset is current

        :param idx: preset index (row index)
        :return: True if current
        """
        if idx is not None:
            w = self.window
            mode = w.core.config.get('mode')
            if mode == MODE_AGENT:
                mode = MODE_EXPERT
            preset_id = w.core.presets.get_by_idx(idx, mode)
            if preset_id:
                if preset_id == "current." + mode:
                    return True
        return False

    def validate_filename(self, value: str) -> str:
        """
        Validate filename

        :param value: filename
        :return: sanitized filename
        """
        return _VALIDATE_FILENAME_RE.sub('', value)

    def preset_change_locked(self) -> bool:
        """
        Check if preset change is locked

        :return: True if locked
        """
        return self.window.core.config.get('mode') == MODE_ASSISTANT

    def reload(self):
        """Reload presets"""
        self.locked = True
        self.window.core.presets.load()
        self.refresh()
        self.locked = False

    def add_selected(self, id: int):
        """
        Add selection ID to selected list

        :param id: preset ID
        """
        if id not in self.selected:
            self.selected.append(id)

    def remove_selected(self, id: int):
        """
        Remove selection ID from selected list

        :param id: preset ID
        """
        if id in self.selected:
            self.selected.remove(id)

    def set_selected(self, id: int):
        """
        Set selected ID in selected list

        :param id: preset ID
        """
        self.selected = [id] if id is not None else []
        self.on_changed()

    def clear_selected(self):
        """Clear selected list"""
        self.selected = []