#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.17 03:00:00                  #
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
            if k in self.window.ui.nodes:
                self.window.ui.nodes[k].setText(trans(self.mapping['nodes'][k]))

        # menu title
        for k in self.mapping['menu.title']:
            if k in self.window.ui.menu:
                self.window.ui.menu[k].setTitle(trans(self.mapping['menu.title'][k]))

        # menu text
        for k in self.mapping['menu.text']:
            if k in self.window.ui.menu:
                self.window.ui.menu[k].setText(trans(self.mapping['menu.text'][k]))

        # menu tooltip
        for k in self.mapping['menu.tooltip']:
            if k in self.window.ui.menu:
                self.window.ui.menu[k].setToolTip(trans(self.mapping['menu.tooltip'][k]))

        # dialog title
        for k in self.mapping['dialog.title']:
            if k in self.window.ui.dialog:
                self.window.ui.dialog[k].setWindowTitle(trans(self.mapping['dialog.title'][k]))

        # tooltip
        for k in self.mapping['tooltip']:
            if k in self.window.ui.nodes:
                self.window.ui.nodes[k].setToolTip(trans(self.mapping['tooltip'][k]))

        # placeholder
        for k in self.mapping['placeholder']:
            if k in self.window.ui.nodes:
                self.window.ui.nodes[k].setPlaceholderText(trans(self.mapping['placeholder'][k]))

        # menu tab tools
        for k in self.window.controller.tools.get_tab_tools():
            if k in self.window.ui.menu:
                self.window.ui.menu[k].setText(trans("output.tab." + self.window.controller.tools.get_tab_tools()[k][0]))

    def get_mapping(self) -> dict:
        """
        Get nodes => locale keys mapping

        :return: dict of nodes mapping
        """
        nodes = {}

        # output
        nodes['output.timestamp'] = 'output.timestamp'
        nodes['output.edit'] = 'output.edit'

        # painter
        nodes['painter.btn.brush'] = 'painter.mode.paint'
        nodes['painter.btn.erase'] = 'painter.mode.erase'
        nodes['painter.btn.capture'] = 'painter.btn.capture'
        nodes['painter.btn.camera.capture'] = 'painter.btn.camera.capture'
        nodes['painter.btn.clear'] = 'painter.btn.clear'

        # calendar
        nodes['filter.ctx.label.colors'] = 'filter.ctx.label.colors'
        nodes['filter.ctx.label'] = 'filter.ctx.label'
        nodes['filter.ctx.radio.all'] = 'filter.ctx.radio.all'
        nodes['filter.ctx.radio.pinned'] = 'filter.ctx.radio.pinned'
        nodes['filter.ctx.radio.indexed'] = 'filter.ctx.radio.indexed'
        nodes['filter.ctx.counters.all'] = 'filter.ctx.counters.all'

        # context
        nodes['ctx.label'] = 'ctx.list.label'
        nodes['ctx.new'] = 'ctx.new'

        # toolbox
        nodes['prompt.mode.label'] = 'toolbox.mode.label'
        nodes['prompt.model.label'] = 'toolbox.model.label'
        nodes['preset.presets.label'] = 'toolbox.presets.label'
        nodes['preset.agents.label'] = 'toolbox.agents.label'
        nodes['preset.experts.label'] = 'toolbox.experts.label'
        # nodes['preset.presets.new'] = 'preset.new'
        # nodes['preset.clear'] = 'preset.clear'
        nodes['preset.use'] = 'preset.use'
        nodes['cmd.enabled'] = 'cmd.enabled'
        nodes['toolbox.prompt.label'] = 'toolbox.prompt'
        nodes["indexes.label"] = "toolbox.indexes.label"
        nodes["llama_index.mode.label"] = "toolbox.llama_index.mode.label"
        nodes["agent.llama.loop.score.label"] = "toolbox.agent.llama.loop.score.label"
        nodes["agent.llama.loop.label"] = "toolbox.agent.llama.loop.label"
        nodes["agent.llama.loop.enabled"] = "toolbox.agent.llama.loop.enabled.label"
        nodes["agent.iterations.label"] = "toolbox.agent.iterations.label"
        nodes["agent.auto_stop"] = "toolbox.agent.auto_stop.label"
        nodes["agent.continue"] = "toolbox.agent.continue.label"
        # nodes["indexes.new"] = "idx.new"

        # input
        nodes['input.label'] = 'input.label'
        nodes['input.send_enter'] = 'input.radio.enter'
        nodes['input.send_shift_enter'] = 'input.radio.enter_shift'
        nodes['input.send_none'] = 'input.radio.none'
        nodes['input.send_clear'] = 'input.send_clear'
        nodes['input.send_btn'] = 'input.btn.send'
        nodes['input.update_btn'] = 'input.btn.update'
        nodes['input.cancel_btn'] = 'input.btn.cancel'
        nodes['input.stop_btn'] = 'input.btn.stop'
        nodes['input.stream'] = 'input.stream'
        nodes['inline.vision'] = 'inline.vision'

        # interpreter
        nodes['interpreter.all'] = 'interpreter.all'
        nodes['interpreter.auto_clear'] = 'interpreter.auto_clear'
        nodes['interpreter.output_label'] = 'interpreter.edit_label.output'
        nodes['interpreter.edit_label'] = 'interpreter.edit_label.edit'
        nodes['interpreter.btn.clear'] = 'dialog.logger.btn.clear'
        nodes['interpreter.btn.send'] = 'interpreter.btn.send'

        # assistants
        nodes['assistants.label'] = 'toolbox.assistants.label'
        # nodes['assistants.new'] = 'assistant.new'
        nodes['assistants.import'] = 'assistant.import'
        nodes['assistant.btn.save'] = 'dialog.assistant.btn.save'
        nodes['assistant.btn.close'] = 'dialog.assistant.btn.close'
        nodes['assistant.name.label'] = 'assistant.name'
        nodes['assistant.id.label'] = 'assistant.id'
        nodes['assistant.instructions.label'] = 'assistant.instructions'
        nodes['assistant.model.label'] = 'assistant.model'
        nodes['assistant.description.label'] = 'assistant.description'
        nodes['assistant.tool.function.label'] = 'assistant.functions.label'

        # assistants: vector store
        nodes['assistant.store.btn.new'] = 'dialog.assistant.store.btn.new'
        nodes['assistant.store.btn.save'] = 'dialog.assistant.store.btn.save'
        nodes['assistant.store.btn.upload.files'] = 'dialog.assistant.store.btn.upload.files'
        nodes['assistant.store.btn.upload.dir'] = 'dialog.assistant.store.btn.upload.dir'
        nodes['assistant.store.btn.close'] = 'dialog.assistant.store.btn.close'
        nodes['assistant.store.hide_thread'] = 'assistant.store.hide_threads'

        # nodes['assistant.id_tip'] = 'assistant.new.id_tip'
        # nodes['assistant.api.tip'] = 'assistant.api.tip'

        # vision
        # nodes['vision.capture.enable'] = 'vision.capture.enable'
        # nodes['vision.capture.auto'] = 'vision.capture.auto'
        # nodes['vision.capture.label'] = 'vision.capture.options.title'
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
        nodes['preset.idx.label'] = 'preset.idx'
        nodes['preset.agent_provider.label'] = 'preset.agent_provider'
        nodes['preset.assistant_id.label'] = 'preset.assistant_id'
        nodes['preset.tool.function.label.all'] = 'preset.tool.function.tip.all'
        nodes['preset.tool.function.label.assistant'] = 'preset.tool.function.tip.assistant'
        nodes['preset.tool.function.label.agent_llama'] = 'preset.tool.function.tip.agent_llama'
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

        # dialog: workdir change
        nodes['workdir.change.update.btn'] = 'dialog.workdir.update.btn'
        nodes['workdir.change.reset.btn'] = 'dialog.workdir.reset.btn'

        # extra settings
        nodes["idx.api.warning"] = "settings.llama.extra.api.warning"
        nodes["idx.db.settings.legend"] = "settings.llama.extra.btn.idx_head"

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

        # dialog: license
        nodes['dialog.license.label'] = 'dialog.license.label'
        nodes['dialog.license.accept'] = 'dialog.license.accept'

        # dialog: about
        nodes['dialog.about.btn.website'] = 'about.btn.website'
        nodes['dialog.about.btn.github'] = 'about.btn.github'
        nodes['dialog.about.btn.support'] = 'about.btn.support'
        nodes['dialog.about.thanks'] = 'about.thanks'
        nodes['dialog.about.thanks.contributors'] = 'about.thanks.contributors'
        nodes['dialog.about.thanks.supporters'] = 'about.thanks.supporters'
        nodes['dialog.about.thanks.sponsors'] = 'about.thanks.sponsors'

        # dialog: find
        nodes['dialog.find.btn.clear'] = 'dialog.find.btn.clear'
        nodes['dialog.find.btn.find_prev'] = 'dialog.find.btn.find_prev'
        nodes['dialog.find.btn.find_next'] = 'dialog.find.btn.find_next'
        nodes['dialog.find.btn.find_prev'] = 'dialog.find.btn.find_prev'

        # dialog: profile
        nodes['dialog.profile.item.btn.dismiss'] = 'dialog.profile.item.btn.dismiss'
        nodes['dialog.profile.name.label'] = 'dialog.profile.name.label'
        nodes['dialog.profile.workdir.label'] = 'dialog.profile.workdir.label'
        nodes['dialog.profile.checkbox.db'] = 'dialog.profile.checkbox.include_db'
        nodes['dialog.profile.checkbox.data'] = 'dialog.profile.checkbox.include_datadir'
        nodes['dialog.profile.checkbox.switch'] = 'dialog.profile.checkbox.switch'
        nodes['profile.editor.btn.new'] = 'dialog.profile.new'
        nodes['profile.editor.tip'] = 'dialog.profile.tip'

        # dialog: confirm
        nodes['dialog.confirm.btn.yes'] = 'dialog.confirm.yes'
        nodes['dialog.confirm.btn.no'] = 'dialog.confirm.no'

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
        # nodes['tip.toolbox.indexes'] = 'tip.toolbox.indexes'
        nodes['tip.toolbox.ctx'] = 'tip.toolbox.ctx'
        nodes['tip.toolbox.mode'] = 'tip.toolbox.mode'
        nodes['plugin.settings.cmd.footer'] = 'cmd.tip'  # plugin settings cmd footer

        # tool: indexer
        nodes['tool.indexer.idx.label'] = 'tool.indexer.idx'
        nodes['tool.indexer.btn.idx'] = 'tool.indexer.idx.btn.add'
        nodes['tool.indexer.status.label'] = 'tool.indexer.status'
        nodes['tool.indexer.ctx.last_auto.label'] = 'tool.indexer.tab.ctx.last_auto'
        nodes['tool.indexer.ctx.auto_enabled.label'] = 'tool.indexer.tab.ctx.auto_enabled'
        nodes['tool.indexer.ctx.last_meta_id.label'] = 'tool.indexer.tab.ctx.last_meta_id'
        nodes['tool.indexer.ctx.last_meta_ts.label'] = 'tool.indexer.tab.ctx.last_meta_ts'
        nodes['tool.indexer.ctx.btn.idx_all'] = 'settings.llama.extra.btn.idx_db_all'
        nodes['tool.indexer.ctx.btn.idx_update'] = 'settings.llama.extra.btn.idx_db_update'
        nodes['tool.indexer.ctx.idx.tip'] = 'tool.indexer.tab.ctx.idx.tip'
        nodes['tool.indexer.file.path_file.label'] = 'tool.indexer.tab.files.path.files'
        nodes['tool.indexer.file.path_dir.label'] = 'tool.indexer.tab.files.path.dir'
        nodes['tool.indexer.file.options.recursive'] = 'tool.indexer.option.recursive'
        nodes['tool.indexer.file.options.replace'] = 'tool.indexer.option.replace'
        nodes['tool.indexer.web.loader.label'] = 'tool.indexer.tab.web.loader'
        nodes['tool.indexer.web.options.label'] = 'tool.indexer.tab.web.source'
        nodes['tool.indexer.web.config.label'] = 'tool.indexer.tab.web.cfg'
        nodes['tool.indexer.web.options.replace'] = 'tool.indexer.option.replace'
        nodes['tool.indexer.file.header.tip'] = 'tool.indexer.tab.files.tip'
        nodes['tool.indexer.web.header.tip'] = 'tool.indexer.tab.web.tip'
        nodes['tool.indexer.ctx.header.tip'] = 'tool.indexer.tab.ctx.tip'
        nodes['tool.indexer.browse.header.tip'] = 'tool.indexer.tab.browse.tip'

        # menu title
        menu_title = {}
        menu_title['menu.app'] = 'menu.file'
        menu_title['menu.config'] = 'menu.config'
        menu_title['config.edit.css'] = 'menu.config.edit.css'
        menu_title['config.edit.json'] = 'menu.config.edit.json'
        menu_title['config.profile'] = 'menu.config.profile'
        menu_title['menu.lang'] = 'menu.lang'
        menu_title['menu.debug'] = 'menu.debug'
        menu_title['menu.theme'] = 'menu.theme'
        menu_title['theme.dark'] = 'menu.theme.dark'
        menu_title['theme.light'] = 'menu.theme.light'
        menu_title['theme.syntax'] = 'menu.theme.syntax'
        menu_title['theme.density'] = 'menu.theme.density'
        menu_title['menu.plugins'] = 'menu.plugins'
        menu_title['menu.plugins.presets'] = 'menu.plugins.presets'
        menu_title['menu.about'] = 'menu.info'
        menu_title['menu.audio'] = 'menu.audio'
        menu_title['menu.video'] = 'menu.video'
        menu_title['menu.tools'] = 'menu.tools'

        # menu text
        menu_text = {}
        menu_text['app.ctx.new'] = 'menu.file.new'
        menu_text['app.ctx.group.new'] = 'menu.file.group.new'
        menu_text['app.ctx.current'] = 'menu.file.current'
        menu_text['app.clear_history'] = 'menu.file_clear_history'
        menu_text['app.clear_history_groups'] = 'menu.file_clear_history_groups'
        menu_text['app.exit'] = 'menu.file.exit'
        menu_text['config.settings'] = 'menu.config.settings'
        menu_text['config.models'] = 'menu.config.models'
        menu_text['config.access'] = 'menu.config.access'
        menu_text['config.open_dir'] = 'menu.config.open_dir'
        menu_text['config.change_dir'] = 'menu.config.change_dir'
        menu_text['config.edit.css.restore'] = 'menu.config.edit.css.restore'
        menu_text['config.profile.edit'] = 'menu.config.profile.edit'
        menu_text['config.profile.new'] = 'menu.config.profile.new'
        menu_text['config.save'] = 'menu.config.save'
        menu_text['theme.tooltips'] = 'menu.theme.tooltips'
        menu_text['theme.blocks'] = 'menu.theme.blocks'
        menu_text['theme.settings'] = 'menu.theme.settings'
        menu_text['plugins.presets.new'] = 'menu.plugins.presets.new'
        menu_text['plugins.presets.edit'] = 'menu.plugins.presets.edit'
        menu_text['plugins.settings'] = 'menu.plugins.settings'
        menu_text['info.about'] = 'menu.info.about'
        menu_text['info.changelog'] = 'menu.info.changelog'
        menu_text['info.updates'] = 'menu.info.updates'
        menu_text['info.docs'] = 'menu.info.docs'
        menu_text['info.pypi'] = 'menu.info.pypi'
        menu_text['info.snap'] = 'menu.info.snap'
        menu_text['info.donate'] = 'menu.info.donate'
        menu_text['info.website'] = 'menu.info.website'
        menu_text['info.github'] = 'menu.info.github'
        menu_text['audio.output'] = 'menu.audio.output'
        menu_text['audio.input'] = 'menu.audio.input'
        menu_text['audio.control.plugin'] = 'menu.audio.control.plugin'
        menu_text['audio.control.global'] = 'menu.audio.control.global'
        menu_text['audio.cache.clear'] = 'menu.audio.cache.clear'
        menu_text['video.capture'] = 'menu.video.capture'
        menu_text['video.capture.auto'] = 'menu.video.capture.auto'

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
            menu_text['debug.agent'] = 'menu.debug.agent'
            menu_text['debug.events'] = 'menu.debug.events'
            menu_text['debug.db'] = 'menu.debug.db'
            menu_text['debug.logger'] = 'menu.debug.logger'
            menu_text['debug.app.log'] = 'menu.debug.app.log'

        # dialog titles
        dialog_title = {}
        dialog_title['info.about'] = 'dialog.about.title'
        dialog_title['info.changelog'] = 'dialog.changelog.title'
        dialog_title['info.license'] = 'dialog.license.title'
        dialog_title['config.editor'] = 'dialog.editor.title'
        dialog_title['config.settings'] = 'dialog.settings'
        dialog_title['editor.assistants'] = 'dialog.assistant'
        dialog_title['assistant.store'] = 'dialog.assistant.store'
        dialog_title['editor.preset.presets'] = 'dialog.preset'
        dialog_title['image'] = 'dialog.image.title'
        dialog_title['interpreter'] = 'dialog.interpreter.title'
        dialog_title['confirm'] = 'dialog.confirm.title'
        dialog_title['rename'] = 'dialog.rename.title'
        dialog_title['update'] = 'update.title'
        dialog_title['workdir.change'] = 'dialog.workdir.title'
        dialog_title['find'] = 'dialog.find.title'
        dialog_title['profile.editor'] = 'dialog.profile.editor'
        dialog_title['profile.item'] = 'dialog.profile.item.editor'
        dialog_title['tool.indexer'] = 'tool.indexer.title'

        # tooltips
        tooltips = {}
        tooltips['prompt.context'] = 'tip.tokens.ctx'
        tooltips['input.counter'] = 'tip.tokens.input'
        tooltips['inline.vision'] = 'vision.checkbox.tooltip'
        # tooltips['vision.capture.enable'] = 'vision.capture.enable.tooltip'
        # tooltips['vision.capture.auto'] = 'vision.capture.auto.tooltip'
        tooltips['cmd.enabled'] = 'cmd.tip'
        tooltips['icon.video.capture'] = 'icon.video.capture'
        tooltips['icon.audio.output'] = 'icon.audio.output'
        tooltips['icon.audio.input'] = 'icon.audio.input'
        tooltips['assistant.store.btn.refresh_status'] = 'dialog.assistant.store.btn.refresh_status'
        tooltips['inline.vision'] = 'vision.checkbox.tooltip'
        tooltips['agent.llama.loop.score'] = 'toolbox.agent.llama.loop.score.tooltip'

        # menu tooltips
        menu_tooltips = {}
        menu_tooltips['video.capture'] = 'vision.capture.enable.tooltip'
        menu_tooltips['video.capture.auto'] = 'vision.capture.auto.tooltip'

        # placeholders
        placeholders = {}
        placeholders['ctx.search'] = 'ctx.list.search.placeholder'
        placeholders['interpreter.input'] = 'interpreter.input.placeholder'

        # mapping
        mapping = {}
        mapping['nodes'] = nodes
        mapping['menu.title'] = menu_title
        mapping['menu.text'] = menu_text
        mapping['menu.tooltip'] = menu_tooltips
        mapping['dialog.title'] = dialog_title
        mapping['tooltip'] = tooltips
        mapping['placeholder'] = placeholders

        # tools
        tool_mappings = self.window.tools.get_lang_mappings()
        for type in tool_mappings:
            for k in tool_mappings[type]:
                mapping[type][k] = tool_mappings[type][k]

        return mapping
