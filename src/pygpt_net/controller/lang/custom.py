#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.24 12:31:00
# ================================================== #

from PySide6.QtCore import Qt

from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_AGENT_LLAMA,
    MODE_AUDIO,
    MODE_CHAT,
    MODE_COMPLETION,
    MODE_EXPERT,
    MODE_IMAGE,
    MODE_LANGCHAIN,
    MODE_VISION,
    MODE_RESEARCH,
    MODE_AGENT_OPENAI,
    MODE_AGENT_V2,
    MODE_COMPUTER,
)
from pygpt_net.utils import trans


class Custom:
    def __init__(self, window=None):
        """
        Custom locale controller

        :param window: Window instance
        """
        self.window = window

    def apply(self):
        """Apply custom mappings"""
        
        # Runtime model selector tooltip is not covered by the generic text mapping.
        model_selector = self.window.ui.nodes.get("prompt.model")
        if model_selector is not None:
            model_selector.setToolTip(trans("input.model.tooltip"))

        # tool: indexer
        self.window.ui.tabs['tool.indexer'].setTabText(0, trans('tool.indexer.tab.files'))
        self.window.ui.tabs['tool.indexer'].setTabText(1, trans('tool.indexer.tab.web'))
        self.window.ui.tabs['tool.indexer'].setTabText(2, trans('tool.indexer.tab.ctx'))
        self.window.ui.tabs['tool.indexer'].setTabText(3, trans('tool.indexer.tab.browser'))

        # checkboxes
        self.window.ui.plugin_addon['audio.input'].btn_toggle.setText(trans('audio.speak.btn'))
        self.window.ui.plugin_addon['audio.input.btn'].continuous.setText(trans('audio.speak.btn.continuous'))
        self.window.ui.config['assistant']['tool.file_search'].box.setText(trans('assistant.tool.file_search'))
        self.window.ui.config['assistant']['tool.code_interpreter'].box.setText(
            trans('assistant.tool.code_interpreter')
        )

        # preset editor
        self.window.ui.config['preset'][MODE_CHAT].setText(trans("preset.chat"))
        self.window.ui.config['preset'][MODE_COMPLETION].setText(trans("preset.completion"))
        self.window.ui.config['preset'][MODE_IMAGE].setText(trans("preset.img"))
        # self.window.ui.config['preset'][MODE_VISION].setText(trans("preset.vision"))
        # self.window.ui.config['preset'][MODE_LANGCHAIN].setText(trans("preset.langchain"))
        self.window.ui.config['preset'][MODE_AGENT].setText(trans("preset.agent"))
        self.window.ui.config['preset'][MODE_AGENT_LLAMA].setText(trans("preset.agent_llama"))
        self.window.ui.config['preset'][MODE_AGENT_OPENAI].setText(trans("preset.agent_openai"))
        self.window.ui.config['preset'][MODE_AGENT_V2].setText(trans("preset.agent_v2"))
        self.window.ui.config['preset'][MODE_EXPERT].setText(trans("preset.expert"))
        self.window.ui.config['preset'][MODE_AUDIO].setText(trans("preset.audio"))
        self.window.ui.config['preset'][MODE_RESEARCH].setText(trans("preset.research"))
        self.window.ui.config['preset'][MODE_COMPUTER].setText(trans("preset.computer"))
        self.window.ui.config['preset']["ai_personalize"].setText(trans("preset.ai_personalize"))
        self.window.ui.config['preset']["mcp_use"].setText(trans("preset.use_list"))
        self.window.ui.config['preset']["agent_skills_use"].setText(trans("preset.use_list"))

        # Preset tabs are physically removed/reinserted when the app mode
        # changes, so their runtime indexes are not fixed. Retranslate by page
        # identity instead of using build-time numeric positions.
        self.window.controller.presets.editor.retranslate_tabs()
        presets_tabs = self.window.ui.nodes.get('presets.tabs')
        if presets_tabs is not None:
            presets_tabs.setTabText(0, trans("toolbox.agents.label"))
            presets_tabs.setTabText(1, trans("preset.tab.skills"))

        # Shared preset prompt tab and the Autonomous-mode hint are not part of
        # the generic option-label mapping, so update them explicitly when the
        # application language changes.
        self.window.ui.nodes['preset.prompt.agent.desc'].setText(trans("preset.prompt.agent.desc"))
        preset_extra = self.window.ui.tabs['preset.editor.extra']
        preset_mode = self.window.core.config.get('mode')
        if preset_mode == MODE_AGENT:
            preset_extra.setTabText(0, trans("preset.prompt.agent"))
        elif preset_mode == MODE_AGENT_V2:
            preset_extra.setTabText(0, trans("preset.prompt.agent_v2"))
        elif preset_mode in (MODE_AGENT_LLAMA, MODE_AGENT_OPENAI):
            preset_extra.setTabText(0, trans("preset.prompt.agent_llama"))
        else:
            preset_extra.setTabText(0, trans("preset.prompt"))


        self.window.ui.config['global']['img_raw'].setText(trans("img.raw"))

        # Models editor/importer contain dynamic option labels and combo entries
        # which are translated when the dialogs are built. Refresh them in-place
        # so an already open dialog follows a runtime language switch.
        try:
            self.window.model_settings.retranslate()
        except (AttributeError, KeyError, RuntimeError):
            pass
        try:
            self.window.model_importer.retranslate()
        except (AttributeError, KeyError, RuntimeError):
            pass

        # Agent Skills dialog. Tabs and QTreeWidget headers are created with
        # translated strings and are not covered by the generic node mapping.
        # Refresh them explicitly so an already open dialog follows a runtime
        # language switch, including its persisted status line.
        try:
            tabs = self.window.ui.nodes.get("skills.tabs")
            if tabs is not None:
                tabs.setTabText(0, trans("skills.tab.installed"))
                tabs.setTabText(1, trans("skills.tab.explore"))

            installed = self.window.ui.nodes.get("skills.installed.list")
            if installed is not None:
                header = installed.headerItem()
                for column, key in enumerate((
                    "skills.column.enabled",
                    "skills.column.name",
                    "skills.column.description",
                    "skills.column.standard",
                    "skills.column.source",
                )):
                    header.setText(column, trans(key))

            explore = self.window.ui.nodes.get("skills.explore.list")
            if explore is not None:
                header = explore.headerItem()
                for column, key in enumerate((
                    None,
                    "skills.column.name",
                    "skills.column.description",
                    "skills.column.author",
                    "skills.column.standard",
                )):
                    header.setText(column, "" if key is None else trans(key))

            self.window.controller.skills.retranslate_status()
        except (AttributeError, KeyError, RuntimeError):
            pass

        # External extensions dialog.
        try:
            tabs = self.window.ui.nodes.get("extensions.tabs")
            if tabs is not None:
                tabs.setTabText(0, trans("extensions.tab.installed"))
                tabs.setTabText(1, trans("extensions.tab.explore"))
            dialog = self.window.ui.dialog.get("extensions")
            if dialog is not None:
                dialog.setWindowTitle(f'{trans("extensions.title")} (beta)')

            installed = self.window.ui.nodes.get("extensions.installed.list")
            if installed is not None:
                header = installed.headerItem()
                for column, key in enumerate((
                    "extensions.column.name", "extensions.column.description",
                    "extensions.column.author", "extensions.column.version",
                    "extensions.column.type", "extensions.column.trusted",
                    "extensions.column.official",
                )):
                    header.setText(column, trans(key))

            explore = self.window.ui.nodes.get("extensions.explore.list")
            if explore is not None:
                header = explore.headerItem()
                for column, key in enumerate((
                    None, "extensions.column.name", "extensions.column.description",
                    "extensions.column.author", "extensions.column.version",
                    "extensions.column.type", "extensions.column.trusted",
                    "extensions.column.official", "extensions.column.source",
                )):
                    header.setText(column, "" if key is None else trans(key))
            self.window.controller.extensions.refresh_installed()
            self.window.controller.extensions._render_registry(self.window.controller.extensions._catalog)
        except (AttributeError, KeyError, RuntimeError):
            pass

        # MCP Connectors dialog uses the same dynamic tab/header pattern as
        # Agent Skills, so keep its open view synchronized with the locale too.
        try:
            tabs = self.window.ui.nodes.get("connectors.tabs")
            if tabs is not None:
                tabs.setTabText(0, trans("connectors.tab.installed"))
                tabs.setTabText(1, trans("connectors.tab.explore"))

            installed = self.window.ui.nodes.get("connectors.installed.list")
            if installed is not None:
                header = installed.headerItem()
                for column, key in enumerate((
                    "connectors.column.active",
                    "connectors.column.name",
                    "connectors.column.transport",
                    "connectors.column.address",
                    "connectors.column.source",
                )):
                    header.setText(column, trans(key))

            explore = self.window.ui.nodes.get("connectors.explore.list")
            if explore is not None:
                header = explore.headerItem()
                for column, key in enumerate((
                    None,
                    "connectors.column.name",
                    "connectors.column.description",
                    "connectors.column.publisher",
                    "connectors.column.source",
                )):
                    header.setText(column, "" if key is None else trans(key))

            self.window.controller.connectors.retranslate_status()
        except (AttributeError, KeyError, RuntimeError):
            pass

        # Chat with Agents runtime mode selector. QComboBox item texts are not
        # covered by the generic node mapping, so retranslate them in-place
        # while keeping their stable machine-readable itemData values.
        combo = self.window.ui.nodes.get('agent.v2.mode')
        if combo is not None:
            mode_keys = {
                'chat': 'agent.v2.mode.chat',
                'orchestrator': 'agent.v2.mode.orchestrator',
                'swarm': 'agent.v2.mode.swarm',
            }
            for i in range(combo.count()):
                key = mode_keys.get(str(combo.itemData(i) or ''))
                if key:
                    combo.setItemText(i, trans(key))
            combo.setToolTip(trans('agent.v2.mode.tooltip'))

        # Autonomous toolbox tabs are created dynamically and need their
        # tab captions refreshed explicitly on a runtime language change.
        agent_tabs = self.window.ui.nodes.get('agent.options.tabs')
        if agent_tabs is not None:
            agent_tabs.setTabText(0, trans('toolbox.agent.tab.flow'))
            agent_tabs.setTabText(1, trans('toolbox.agent.tab.steps'))

        manage_agents = self.window.ui.nodes.get('agent.v2.manage')
        if manage_agents is not None:
            manage_agents.setToolTip(trans('toolbox.agent.v2.manage.tooltip'))
        try:
            self.window.agents_v2_editor.retranslate()
        except (AttributeError, KeyError, RuntimeError):
            pass

        # painter drawing modes (combo + RMB submenu)
        try:
            self.window.controller.painter.common.retranslate_draw_modes()
        except (AttributeError, KeyError):
            pass

        # camera capture
        if not self.window.core.config.get('vision.capture.auto'):
            self.window.ui.nodes['video.preview'].video.setToolTip(trans("vision.capture.label"))
        else:
            self.window.ui.nodes['video.preview'].video.setToolTip(trans("vision.capture.auto.label"))

        # files / indexes
        self.window.ui.nodes['output_files'].btn_upload.setText(trans('files.local.upload'))
        self.window.ui.nodes['output_files'].btn_idx.setText(trans('idx.btn.index_all'))
        self.window.ui.nodes['output_files'].btn_clear.setText(trans('idx.btn.clear'))

        # input: tabs
        input_tabs = self.window.ui.tabs['input']
        # Keep the main Input tab icon-only. Language/profile reloads call this
        # mapping again, so restoring the translated label here would undo the
        # compact tab presentation created by the input layout.
        input_tabs.set_compact_tab_count(0, 0)
        input_tabs.retranslate_compact_tabs()
        mode = self.window.core.config.get('mode')
        self.window.controller.attachment.update_tab(mode)
        self.window.controller.assistant.files.update_tab()
        # Context-uploaded files use tab 3 outside Assistant mode and keep the
        # same compact icon + optional numeric count contract.
        self.window.controller.chat.attachment.update_tab(self.window.core.ctx.get_current_meta())
        try:
            input_node = self.window.ui.nodes['input']
            # Send/Stop are icon-only controls, so locale changes update their
            # tooltips instead of restoring translated text labels.
            send_btn = self.window.ui.nodes.get('input.send_btn')
            stop_btn = self.window.ui.nodes.get('input.stop_btn')
            if send_btn is not None:
                send_btn.setToolTip(trans('input.btn.send'))
            if stop_btn is not None:
                stop_btn.setToolTip(trans('input.btn.stop'))
            input_node.update_reasoning_effort()
            input_node.refresh_right_bar()
        except (AttributeError, KeyError):
            pass

        # input: attachments
        self.window.ui.models['attachments'].setHeaderData(0, Qt.Horizontal, trans('attachments.header.name'))
        self.window.ui.models['attachments'].setHeaderData(1, Qt.Horizontal, trans('attachments.header.path'))
        self.window.ui.models['attachments_uploaded'].setHeaderData(0, Qt.Horizontal, trans('attachments.header.name'))
        self.window.ui.models['attachments_uploaded'].setHeaderData(1, Qt.Horizontal, trans('attachments.header.path'))
        self.window.ui.models['attachments_ctx'].setHeaderData(0, Qt.Horizontal, trans('attachments.header.active'))
        self.window.ui.models['attachments_ctx'].setHeaderData(1, Qt.Horizontal, trans('attachments.header.name'))
        self.window.ui.models['attachments_ctx'].setHeaderData(2, Qt.Horizontal, trans('attachments.header.path'))
        self.window.ui.models['attachments_ctx'].setHeaderData(3, Qt.Horizontal, trans('attachments.header.size'))
        self.window.ui.models['attachments_ctx'].setHeaderData(4, Qt.Horizontal, trans('attachments.header.length'))
        self.window.ui.models['attachments_ctx'].setHeaderData(5, Qt.Horizontal, trans('attachments.header.idx'))

        # dialog: changelog update notice contains a runtime version placeholder,
        # so it cannot use the generic static node mapping.
        changelog_updated = self.window.ui.nodes.get('dialog.changelog.updated')
        if changelog_updated is not None:
            changelog_updated.setText(
                trans("dialog.changelog.updated").format(version=self.window.meta["version"])
            )

        # dialog: about
        self.window.ui.nodes['dialog.about.content'].setText(trans(self.window.ui.dialogs.about.prepare_content()))

        # settings: llama-idx
        self.window.controller.idx.settings.update_text_last_updated()
        self.window.controller.idx.settings.update_text_loaders()

        # mode
        self.window.controller.mode.init_list()

        # theme menu
        self.window.ui.menu['menu.theme'].setTitle(trans("menu.theme"))
        for theme in self.window.ui.menu['theme']:
            name = self.window.controller.theme.common.translate(theme)
            self.window.ui.menu['theme'][theme].setText(name)

        # dialog: profile
        if self.window.ui.dialog['profile.item'].mode == 'create':
            self.window.ui.nodes['dialog.profile.item.btn.update'].setText(trans('dialog.profile.item.btn.create'))
        elif self.window.ui.dialog['profile.item'].mode == 'edit':
            self.window.ui.nodes['dialog.profile.item.btn.update'].setText(trans("dialog.profile.item.btn.update"))
        elif self.window.ui.dialog['profile.item'].mode == 'duplicate':
            self.window.ui.nodes['dialog.profile.item.btn.update'].setText(trans("dialog.profile.item.btn.duplicate"))

        # audio input
        self.window.ui.nodes['voice.control.btn'].btn_toggle.setText(trans('audio.control.btn'))
        self.window.ui.plugin_addon['audio.input.btn'].btn_toggle.setText(trans('audio.speak.btn'))

        # llama index model
