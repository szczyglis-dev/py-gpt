#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.25 04:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt

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
        # output: tabs
        self.window.ui.tabs['output'].setTabText(0, trans('output.tab.chat'))
        self.window.ui.tabs['output'].setTabText(1, trans('output.tab.files'))
        self.window.ui.tabs['output'].setTabText(2, trans('output.tab.calendar'))
        self.window.ui.tabs['output'].setTabText(3, trans('output.tab.painter'))

        # tool: indexer
        self.window.ui.tabs['tool.indexer'].setTabText(0, trans('tool.indexer.tab.files'))
        self.window.ui.tabs['tool.indexer'].setTabText(1, trans('tool.indexer.tab.web'))
        self.window.ui.tabs['tool.indexer'].setTabText(2, trans('tool.indexer.tab.ctx'))
        self.window.ui.tabs['tool.indexer'].setTabText(3, trans('tool.indexer.tab.browser'))

        # checkboxes
        self.window.ui.plugin_addon['audio.input'].btn_toggle.setText(trans('audio.speak.btn'))
        self.window.ui.config['assistant']['tool.file_search'].box.setText(trans('assistant.tool.file_search'))
        self.window.ui.config['assistant']['tool.code_interpreter'].box.setText(
            trans('assistant.tool.code_interpreter')
        )
        self.window.ui.config['preset']['chat'].box.setText(trans("preset.chat"))
        self.window.ui.config['preset']['completion'].box.setText(trans("preset.completion"))
        self.window.ui.config['preset']['img'].box.setText(trans("preset.img"))
        self.window.ui.config['global']['img_raw'].setText(trans("img.raw"))

        # camera capture
        if not self.window.core.config.get('vision.capture.auto'):
            self.window.ui.nodes['video.preview'].label.setText(trans("vision.capture.label"))
        else:
            self.window.ui.nodes['video.preview'].label.setText(trans("vision.capture.auto.label"))

        # files / indexes
        self.window.ui.nodes['output_files'].btn_upload.setText(trans('files.local.upload'))
        self.window.ui.nodes['output_files'].btn_idx.setText(trans('idx.btn.index_all'))
        self.window.ui.nodes['output_files'].btn_clear.setText(trans('idx.btn.clear'))

        # input: tabs
        self.window.ui.tabs['input'].setTabText(0, trans('input.tab'))
        self.window.ui.tabs['input'].setTabText(1, trans('attachments.tab'))
        mode = self.window.core.config.get('mode')
        self.window.controller.attachment.update_tab(mode)
        self.window.controller.assistant.files.update_tab()
        self.window.ui.tabs['input'].setTabText(0, trans('input.tab'))

        # input: attachments
        self.window.ui.models['attachments'].setHeaderData(0, Qt.Horizontal, trans('attachments.header.name'))
        self.window.ui.models['attachments'].setHeaderData(1, Qt.Horizontal, trans('attachments.header.path'))
        self.window.ui.models['attachments_uploaded'].setHeaderData(0, Qt.Horizontal, trans('attachments.header.name'))
        self.window.ui.models['attachments_uploaded'].setHeaderData(1, Qt.Horizontal, trans('attachments.header.path'))

        # dialog: about
        self.window.ui.nodes['dialog.about.content'].setText(trans(self.window.ui.dialogs.about.prepare_content()))

        # settings: llama-idx
        self.window.controller.idx.settings.update_text_last_updated()
        self.window.controller.idx.settings.update_text_loaders()

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
        self.window.ui.nodes['llama_index.mode.select'].set_keys(self.window.controller.idx.get_modes_keys())
