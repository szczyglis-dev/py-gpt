#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.15 12:00:00                  #
# ================================================== #

from pygpt_net.utils import trans


class Mapping:
    def __init__(self, window=None):
        """
        Locale mapping controller

        :param window: Window instance
        """
        self.window = window
        self.mapping = {}

    def apply(self):
        """Apply mapped keys"""

        # load locale mapping
        if len(self.mapping) == 0:
            self.mapping = self.get_mapping()

        # nodes labels
        for k in self.mapping['nodes']:
            self.window.ui.nodes[k].setText(trans(self.mapping['nodes'][k]))

        # menu title
        for k in self.mapping['menu.title']:
            self.window.ui.menu[k].setTitle(trans(self.mapping['menu.title'][k]))

        # menu text
        for k in self.mapping['menu.text']:
            self.window.ui.menu[k].setText(trans(self.mapping['menu.text'][k]))

        # dialog title
        for k in self.mapping['dialog.title']:
            self.window.ui.dialog[k].setWindowTitle(trans(self.mapping['dialog.title'][k]))

        # tooltip
        for k in self.mapping['tooltip']:
            self.window.ui.nodes[k].setToolTip(trans(self.mapping['tooltip'][k]))

        # placeholder
        for k in self.mapping['placeholder']:
            self.window.ui.nodes[k].setPlaceholderText(trans(self.mapping['placeholder'][k]))

    def get_mapping(self) -> dict:
        """
        Get nodes => locale keys mapping

        :return: dict of nodes mapping
        """
        nodes = {}

        # output
        nodes['output.timestamp'] = 'output.timestamp'

        # painter
        nodes['painter.btn.brush'] = 'painter.mode.paint'
        nodes['painter.btn.erase'] = 'painter.mode.erase'
        nodes['painter.btn.capture'] = 'painter.btn.capture'
        nodes['painter.btn.camera.capture'] = 'painter.btn.camera.capture'
        nodes['painter.btn.clear'] = 'painter.btn.clear'

        # context
        nodes['ctx.label'] = 'ctx.list.label'
        nodes['ctx.new'] = 'ctx.new'

        # toolbox
        nodes['prompt.mode.label'] = 'toolbox.mode.label'
        nodes['prompt.model.label'] = 'toolbox.model.label'
        nodes['preset.presets.label'] = 'toolbox.presets.label'
        nodes['preset.presets.new'] = 'preset.new'
        nodes['preset.clear'] = 'preset.clear'
        nodes['preset.use'] = 'preset.use'
        nodes['cmd.enabled'] = 'cmd.enabled'
        nodes['toolbox.prompt.label'] = 'toolbox.prompt'

        # input
        nodes['input.label'] = 'input.label'
        nodes['input.send_enter'] = 'input.radio.enter'
        nodes['input.send_shift_enter'] = 'input.radio.enter_shift'
        nodes['input.send_none'] = 'input.radio.none'
        nodes['input.send_clear'] = 'input.send_clear'
        nodes['input.send_btn'] = 'input.btn.send'
        nodes['input.stop_btn'] = 'input.btn.stop'
        nodes['input.stream'] = 'input.stream'

        # assistants
        nodes['assistants.label'] = 'toolbox.assistants.label'
        nodes['assistants.new'] = 'assistant.new'
        nodes['assistants.import'] = 'assistant.import'
        nodes['assistant.btn.save'] = 'dialog.assistant.btn.save'
        nodes['assistant.name.label'] = 'assistant.name'
        nodes['assistant.id.label'] = 'assistant.id'
        nodes['assistant.instructions.label'] = 'assistant.instructions'
        nodes['assistant.model.label'] = 'assistant.model'
        nodes['assistant.description.label'] = 'assistant.description'
        nodes['assistant.tool.function.label'] = 'assistant.functions.label'
        nodes['assistant.id_tip'] = 'assistant.new.id_tip'
        nodes['assistant.api.tip'] = 'assistant.api.tip'

        # vision
        nodes['vision.capture.enable'] = 'vision.capture.enable'
        nodes['vision.capture.auto'] = 'vision.capture.auto'
        nodes['vision.capture.label'] = 'vision.capture.options.title'
        nodes['inline.vision'] = 'inline.vision'

        # dialog: plugin settings
        nodes['plugin.settings.btn.defaults.user'] = 'dialog.plugin.settings.btn.defaults.user'
        nodes['plugin.settings.btn.defaults.app'] = 'dialog.plugin.settings.btn.defaults.app'
        nodes['plugin.settings.btn.save'] = 'dialog.plugin.settings.btn.save'

        # dialog: editor
        nodes['dialog.editor.label'] = 'dialog.editor.label'
        nodes['editor.btn.default'] = 'dialog.editor.btn.defaults'
        nodes['editor.btn.save'] = 'dialog.editor.btn.save'

        # dialog: preset
        nodes['preset.filename.label'] = 'preset.filename'
        nodes['preset.name.label'] = 'preset.name'
        nodes['preset.ai_name.label'] = 'preset.ai_name'
        nodes['preset.user_name.label'] = 'preset.user_name'
        nodes['preset.temperature.label'] = 'preset.temperature'
        nodes['preset.prompt.label'] = 'preset.prompt'
        nodes['preset.btn.current'] = 'dialog.preset.btn.current'
        nodes['preset.btn.save'] = 'dialog.preset.btn.save'

        # dialog: rename
        nodes['dialog.rename.label'] = 'dialog.rename.title'
        nodes['dialog.rename.btn.update'] = 'dialog.rename.update'
        nodes['dialog.rename.btn.dismiss'] = 'dialog.rename.dismiss'

        # dialog: settings
        nodes['settings.btn.defaults.user'] = 'dialog.settings.btn.defaults.user'
        nodes['settings.btn.defaults.app'] = 'dialog.settings.btn.defaults.app'
        nodes['settings.btn.save'] = 'dialog.settings.btn.save'

        # start
        nodes['start.title'] = 'dialog.start.title.text'
        nodes['start.settings'] = 'dialog.start.settings.text'
        nodes['start.btn'] = 'dialog.start.btn'

        # input tabs
        nodes['attachments.btn.add'] = 'attachments.btn.add'
        nodes['attachments.btn.clear'] = 'attachments.btn.clear'
        nodes['attachments.send_clear'] = 'attachments.send_clear'
        nodes['attachments_uploaded.btn.sync'] = 'attachments_uploaded.btn.sync'
        nodes['attachments_uploaded.btn.clear'] = 'attachments_uploaded.btn.clear'
        nodes['attachments_uploaded.sync.tip'] = 'attachments_uploaded.sync.tip'

        # filesystem
        nodes['idx.btn.db.index_all'] = 'settings.llama.extra.btn.idx_db_all'
        nodes['idx.btn.db.index_update'] = 'settings.llama.extra.btn.idx_db_update'
        nodes['idx.btn.db.index_files'] = 'settings.llama.extra.btn.idx_files_all'
        nodes['idx.db.settings.legend'] = 'settings.llama.extra.legend'
        nodes['idx.db.settings.legend.head'] = 'settings.llama.extra.btn.idx_head'

        # dialog: changelog
        nodes['dialog.changelog.label'] = 'dialog.changelog.title'

        # help tips
        nodes['tip.output.tab.files'] = 'tip.output.tab.files'
        nodes['tip.output.tab.draw'] = 'tip.output.tab.draw'
        nodes['tip.output.tab.calendar'] = 'tip.output.tab.calendar'
        nodes['tip.output.tab.notepad'] = 'tip.output.tab.notepad'
        nodes['tip.input.attachments'] = 'tip.input.attachments'
        nodes['tip.input.attachments.uploaded'] = 'tip.input.attachments.uploaded'
        nodes['tip.toolbox.presets'] = 'tip.toolbox.presets'
        nodes['tip.toolbox.prompt'] = 'tip.toolbox.prompt'
        nodes['tip.toolbox.assistants'] = 'tip.toolbox.assistants'
        nodes['tip.toolbox.indexes'] = 'tip.toolbox.indexes'
        nodes['tip.toolbox.ctx'] = 'tip.toolbox.ctx'
        nodes['tip.toolbox.mode'] = 'tip.toolbox.mode'

        # menu title
        menu_title = {}
        menu_title['menu.app'] = 'menu.file'
        menu_title['menu.config'] = 'menu.config'
        menu_title['menu.lang'] = 'menu.lang'
        menu_title['menu.debug'] = 'menu.debug'
        menu_title['menu.theme'] = 'menu.theme'
        menu_title['theme.dark'] = 'menu.theme.dark'
        menu_title['theme.light'] = 'menu.theme.light'
        menu_title['theme.density'] = 'menu.theme.density'
        menu_title['menu.plugins'] = 'menu.plugins'
        menu_title['menu.about'] = 'menu.info'
        menu_title['menu.audio'] = 'menu.audio'

        # menu text
        menu_text = {}
        menu_text['app.ctx.new'] = 'menu.file.new'
        menu_text['app.clear_history'] = 'menu.file_clear_history'
        menu_text['app.exit'] = 'menu.file.exit'
        menu_text['config.settings'] = 'menu.config.settings'
        menu_text['config.models'] = 'menu.config.models'
        menu_text['config.open_dir'] = 'menu.config.open_dir'
        menu_text['config.save'] = 'menu.config.save'
        menu_text['theme.tooltips'] = 'menu.theme.tooltips'
        menu_text['theme.settings'] = 'menu.theme.settings'
        menu_text['plugins.settings'] = 'menu.plugins.settings'
        menu_text['info.about'] = 'menu.info.about'
        menu_text['info.changelog'] = 'menu.info.changelog'
        menu_text['info.updates'] = 'menu.info.updates'
        menu_text['info.docs'] = 'menu.info.docs'
        menu_text['info.pypi'] = 'menu.info.pypi'
        menu_text['info.snap'] = 'menu.info.snap'
        menu_text['info.website'] = 'menu.info.website'
        menu_text['info.github'] = 'menu.info.github'
        menu_text['audio.output.azure'] = 'menu.audio.output.azure'
        menu_text['audio.output.tts'] = 'menu.audio.output.tts'
        menu_text['audio.input.whisper'] = 'menu.audio.input.whisper'

        # debug menu
        if 'menu.debug' in self.window.ui.menu:
            menu_text['debug.config'] = 'menu.debug.config'
            menu_text['debug.context'] = 'menu.debug.context'
            menu_text['debug.presets'] = 'menu.debug.presets'
            menu_text['debug.plugins'] = 'menu.debug.plugins'
            menu_text['debug.models'] = 'menu.debug.models'
            menu_text['debug.attachments'] = 'menu.debug.attachments'
            menu_text['debug.assistants'] = 'menu.debug.assistants'
            menu_text['debug.ui'] = 'menu.debug.ui'

            # dialog titles
        dialog_title = {}
        dialog_title['info.about'] = 'dialog.about.title'
        dialog_title['info.changelog'] = 'dialog.changelog.title'
        dialog_title['config.editor'] = 'dialog.editor.title'
        dialog_title['config.settings'] = 'dialog.settings'
        dialog_title['editor.assistants'] = 'dialog.assistant'
        dialog_title['editor.preset.presets'] = 'dialog.preset'
        dialog_title['image'] = 'dialog.image.title'
        dialog_title['rename'] = 'dialog.rename.title'
        dialog_title['update'] = 'update.title'

        # tooltips
        tooltips = {}
        tooltips['prompt.context'] = 'tip.tokens.ctx'
        tooltips['input.counter'] = 'tip.tokens.input'
        tooltips['vision.capture.enable'] = 'vision.capture.enable.tooltip'
        tooltips['vision.capture.auto'] = 'vision.capture.auto.tooltip'

        # placeholders
        placeholders = {}
        placeholders['ctx.search'] = 'ctx.list.search.placeholder'

        # mapping
        mapping = {}
        mapping['nodes'] = nodes
        mapping['menu.title'] = menu_title
        mapping['menu.text'] = menu_text
        mapping['dialog.title'] = dialog_title
        mapping['tooltip'] = tooltips
        mapping['placeholder'] = placeholders

        return mapping
