#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.25 21:00:00                  #
# ================================================== #

from PySide6.QtGui import QAction, Qt

from pygpt_net.utils import trans


class Lang:
    def __init__(self, window=None):
        """
        Language switch controller

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup language handler"""
        # get files from locale directory
        langs = self.window.core.config.get_available_langs()
        for lang in langs:
            self.window.ui.menu['lang'][lang] = QAction(lang.upper(), self.window, checkable=True)
            self.window.ui.menu['lang'][lang].triggered.connect(
                lambda checked=None, lang=lang: self.window.controller.lang.toggle(lang))
            self.window.ui.menu['menu.lang'].addAction(self.window.ui.menu['lang'][lang])

        self.update()

    def update(self):
        """Update language menu"""
        for lang in self.window.ui.menu['lang']:
            self.window.ui.menu['lang'][lang].setChecked(False)

        lang = self.window.core.config.get('lang')
        if lang in self.window.ui.menu['lang']:
            self.window.ui.menu['lang'][lang].setChecked(True)

    def toggle(self, id):
        """
        Toggle language

        :param id: language to toggle
        """
        self.window.core.config.set('lang', id)
        self.window.core.config.save()
        trans('', True)  # force reload translations

        self.update()

        # output
        self.window.ui.nodes['output.timestamp'].setText(trans('output.timestamp'))
        self.window.ui.nodes['prompt.context'].setToolTip(trans('tip.tokens.ctx'))

        # output: tabs
        self.window.ui.tabs['output'].setTabText(0, trans('output.tab.chat'))
        self.window.ui.tabs['output'].setTabText(1, trans('output.tab.files'))

        # notepads
        num_notepads = self.window.controller.notepad.get_num_notepads()
        if num_notepads > 0:
            for i in range(1, num_notepads + 1):
                tab = i + 2
                self.window.ui.tabs['output'].setTabText(tab, trans('output.tab.notepad') + " " + str(i))

        # context
        self.window.ui.nodes['ctx.label'].setText(trans("ctx.list.label"))
        self.window.ui.nodes['ctx.new'].setText(trans('ctx.new'))
        self.window.ui.nodes['ctx.search'].setPlaceholderText(trans('ctx.list.search.placeholder'))

        # toolbox
        self.window.ui.nodes['prompt.mode.label'].setText(trans("toolbox.mode.label"))
        self.window.ui.nodes['prompt.model.label'].setText(trans("toolbox.model.label"))
        self.window.ui.nodes['preset.presets.label'].setText(trans("toolbox.presets.label"))
        self.window.ui.nodes['preset.presets.new'].setText(trans('preset.new'))
        self.window.ui.nodes['preset.clear'].setText(trans('preset.clear'))
        self.window.ui.nodes['preset.use'].setText(trans('preset.use'))
        self.window.ui.nodes['toolbox.preset.ai_name.label'].setText(trans('toolbox.name.ai'))
        self.window.ui.nodes['toolbox.preset.user_name.label'].setText(trans('toolbox.name.user'))
        self.window.ui.nodes['toolbox.prompt.label'].setText(trans("toolbox.prompt"))
        self.window.ui.nodes['temperature.label'].setText(trans("toolbox.temperature.label"))

        # input
        self.window.ui.nodes['input.label'].setText(trans("input.label"))
        self.window.ui.nodes['input.send_enter'].setText(trans("input.radio.enter"))
        self.window.ui.nodes['input.send_shift_enter'].setText(trans("input.radio.enter_shift"))
        self.window.ui.nodes['input.send_none'].setText(trans("input.radio.none"))
        self.window.ui.nodes['input.send_clear'].setText(trans('input.send_clear'))
        self.window.ui.nodes['input.send_btn'].setText(trans("input.btn.send"))
        self.window.ui.nodes['input.stop_btn'].setText(trans("input.btn.stop"))
        self.window.ui.nodes['input.stream'].setText(trans('input.stream'))
        self.window.ui.nodes['attachments.send_clear'].setText(trans('attachments.send_clear'))
        self.window.ui.nodes['input.counter'].setToolTip(trans('tip.tokens.input'))

        # input: attachments headers
        self.window.ui.models['attachments'].setHeaderData(0, Qt.Horizontal, trans('attachments.header.name'))
        self.window.ui.models['attachments'].setHeaderData(1, Qt.Horizontal, trans('attachments.header.path'))
        self.window.ui.models['attachments_uploaded'].setHeaderData(0, Qt.Horizontal, trans('attachments.header.name'))
        self.window.ui.models['attachments_uploaded'].setHeaderData(1, Qt.Horizontal, trans('attachments.header.path'))

        # audio speak btn
        self.window.ui.plugin_addon['audio.input'].btn_toggle.setText(trans('audio.speak.btn'))

        # assistants
        self.window.ui.nodes['assistants.label'].setText(trans("toolbox.assistants.label"))
        self.window.ui.nodes['assistants.new'].setText(trans('assistant.new'))
        self.window.ui.nodes['assistants.import'].setText(trans('assistant.import'))
        self.window.ui.nodes['assistant.btn.save'].setText(trans("dialog.assistant.btn.save"))
        self.window.ui.nodes['assistant.name.label'].setText(trans("assistant.name"))
        self.window.ui.nodes['assistant.id.label'].setText(trans("assistant.id"))
        self.window.ui.nodes['assistant.instructions.label'].setText(trans("assistant.instructions"))
        self.window.ui.nodes['assistant.model.label'].setText(trans("assistant.model"))
        self.window.ui.nodes['assistant.description.label'].setText(trans("assistant.description"))
        self.window.ui.nodes['assistant.functions.label'].setText(trans('assistant.functions.label'))
        self.window.ui.nodes['assistant.id_tip'].setText(trans("assistant.new.id_tip"))
        self.window.ui.nodes['assistant.api.tip'].setText(trans('assistant.api.tip'))
        self.window.ui.config_option['assistant.tool.retrieval'].box.setText(trans('assistant.tool.retrieval'))
        self.window.ui.config_option['assistant.tool.code_interpreter'].box.setText(
            trans('assistant.tool.code_interpreter'))
        self.window.ui.dialog['editor.assistants'].setWindowTitle(trans('dialog.assistant'))

        # vision
        self.window.ui.nodes['vision.capture.enable'].setText(trans("vision.capture.enable"))
        self.window.ui.nodes['vision.capture.enable'].setToolTip(trans("vision.capture.enable.tooltip"))
        self.window.ui.nodes['vision.capture.auto'].setText(trans("vision.capture.auto"))
        self.window.ui.nodes['vision.capture.auto'].setToolTip(trans('vision.capture.auto.tooltip'))
        self.window.ui.nodes['vision.capture.label'].setText(trans('vision.capture.options.title'))

        # capture label
        if not self.window.core.config.get('vision.capture.auto'):
            self.window.ui.nodes['video.preview'].label.setText(trans("vision.capture.label"))
        else:
            self.window.ui.nodes['video.preview'].label.setText(trans("vision.capture.auto.label"))

        # dialog: about
        self.window.ui.nodes['dialog.about.content'].setText(self.window.ui.dialogs.about.prepare_content())
        self.window.ui.nodes['dialog.about.thanks'].setText(trans('about.thanks') + ":")
        self.window.ui.dialog['info.about'].setWindowTitle(trans("dialog.about.title"))

        # dialog: changelog
        self.window.ui.nodes['dialog.changelog.label'].setText(trans("dialog.changelog.title"))
        self.window.ui.dialog['info.changelog'].setWindowTitle(trans("dialog.changelog.title"))

        # dialog: editor
        self.window.ui.nodes['dialog.editor.label'].setText(trans('dialog.editor.label'))
        self.window.ui.nodes['editor.btn.default'].setText(trans("dialog.editor.btn.defaults"))
        self.window.ui.nodes['editor.btn.save'].setText(trans("dialog.editor.btn.save"))
        self.window.ui.dialog['config.editor'].setWindowTitle(trans('dialog.editor.title'))

        # dialog: plugin settings
        self.window.ui.nodes['plugin.settings.btn.defaults.user'].setText(
            trans("dialog.plugin.settings.btn.defaults.user"))
        self.window.ui.nodes['plugin.settings.btn.defaults.app'].setText(
            trans("dialog.plugin.settings.btn.defaults.app"))
        self.window.ui.nodes['plugin.settings.btn.save'].setText(trans("dialog.plugin.settings.btn.save"))

        # dialog: preset
        self.window.ui.dialog['editor.preset.presets'].setWindowTitle(trans('dialog.preset'))
        self.window.ui.nodes['preset.filename.label'].setText(trans("preset.filename"))
        self.window.ui.nodes['preset.name.label'].setText(trans("preset.name"))
        self.window.ui.nodes['preset.ai_name.label'].setText(trans("preset.ai_name"))
        self.window.ui.nodes['preset.user_name.label'].setText(trans("preset.user_name"))
        self.window.ui.nodes['preset.temperature.label'].setText(trans("preset.temperature"))
        self.window.ui.nodes['preset.prompt.label'].setText(trans("preset.prompt"))
        self.window.ui.nodes['preset.btn.current'].setText(trans("dialog.preset.btn.current"))
        self.window.ui.nodes['preset.btn.save'].setText(trans("dialog.preset.btn.save"))
        self.window.ui.nodes['cmd.enabled'].setText(trans('cmd.enabled'))
        self.window.ui.config_option['preset.chat'].box.setText(trans("preset.chat"))
        self.window.ui.config_option['preset.completion'].box.setText(trans("preset.completion"))
        self.window.ui.config_option['preset.img'].box.setText(trans("preset.img"))
        self.window.ui.config_option['img_raw'].setText(trans("img.raw"))

        # dialog: rename
        self.window.ui.dialog['rename'].setWindowTitle(trans("dialog.rename.title"))
        self.window.ui.nodes['dialog.rename.label'].setText(trans("dialog.rename.title"))
        self.window.ui.nodes['dialog.rename.btn.update'].setText(trans("dialog.rename.update"))
        self.window.ui.nodes['dialog.rename.btn.dismiss'].setText(trans("dialog.rename.dismiss"))

        # dialog: settings
        self.update_settings_dialogs()
        self.window.ui.dialog['config.settings'].setWindowTitle(trans('dialog.settings'))
        self.window.ui.nodes['settings.btn.defaults.user'].setText(trans("dialog.settings.btn.defaults.user"))
        self.window.ui.nodes['settings.btn.defaults.app'].setText(trans("dialog.settings.btn.defaults.app"))
        self.window.ui.nodes['settings.btn.save'].setText(trans("dialog.settings.btn.save"))

        # dialog: updater
        self.window.ui.dialog['update'].download.setText(trans('update.download'))
        self.window.ui.dialog['update'].setWindowTitle(trans('update.title'))

        # menu
        self.window.ui.menu['menu.app'].setTitle(trans("menu.file"))
        self.window.ui.menu['app.ctx.new'].setText(trans("menu.file.new"))
        self.window.ui.menu['app.clear_history'].setText(trans("menu.file_clear_history"))
        self.window.ui.menu['app.exit'].setText(trans("menu.file.exit"))

        self.window.ui.menu['menu.plugins'].setTitle(trans("menu.plugins"))
        self.window.ui.menu['menu.audio'].setTitle(trans("menu.audio"))

        self.window.ui.menu['menu.config'].setTitle(trans("menu.config"))
        self.window.ui.menu['config.settings'].setText(trans("menu.config.settings"))
        self.window.ui.menu['config.edit.config'].setText(trans("menu.config.edit.config"))
        self.window.ui.menu['config.edit.models'].setText(trans("menu.config.edit.models"))
        self.window.ui.menu['config.open_dir'].setText(trans("menu.config.open_dir"))
        self.window.ui.menu['config.save'].setText(trans("menu.config.save"))

        self.window.ui.menu['menu.lang'].setTitle(trans("menu.lang"))
        self.window.ui.menu['menu.theme'].setTitle(trans("menu.theme"))

        # debug menu
        if 'menu.debug' in self.window.ui.menu:
            self.window.ui.menu['menu.debug'].setTitle(trans("menu.debug"))
            self.window.ui.menu['debug.config'].setText(trans("menu.debug.config"))
            self.window.ui.menu['debug.context'].setText(trans("menu.debug.context"))
            self.window.ui.menu['debug.presets'].setText(trans("menu.debug.presets"))
            self.window.ui.menu['debug.plugins'].setText(trans("menu.debug.plugins"))
            self.window.ui.menu['debug.models'].setText(trans("menu.debug.models"))
            self.window.ui.menu['debug.attachments'].setText(trans("menu.debug.attachments"))
            self.window.ui.menu['debug.assistants'].setText(trans("menu.debug.assistants"))
            self.window.ui.menu['debug.ui'].setText(trans("menu.debug.ui"))

        self.window.ui.menu['menu.about'].setTitle(trans("menu.info"))
        self.window.ui.menu['info.about'].setText(trans("menu.info.about"))
        self.window.ui.menu['info.changelog'].setText(trans("menu.info.changelog"))
        self.window.ui.menu['info.updates'].setText(trans("menu.info.updates"))
        self.window.ui.menu['info.docs'].setText(trans("menu.info.docs"))
        self.window.ui.menu['info.pypi'].setText(trans("menu.info.pypi"))
        self.window.ui.menu['info.snap'].setText(trans("menu.info.snap"))
        self.window.ui.menu['info.website'].setText(trans("menu.info.website"))
        self.window.ui.menu['info.github'].setText(trans("menu.info.github"))

        # start
        self.window.ui.nodes['start.title'].setText(trans('dialog.start.title.text'))
        self.window.ui.nodes['start.settings'].setText(trans('dialog.start.settings.text'))
        self.window.ui.nodes['start.btn'].setText(trans('dialog.start.btn'))

        # input tabs
        self.window.ui.tabs['input'].setTabText(0, trans('input.tab'))
        self.window.ui.tabs['input'].setTabText(1, trans('attachments.tab'))
        self.window.ui.nodes['attachments.btn.add'].setText(trans('attachments.btn.add'))
        self.window.ui.nodes['attachments.btn.clear'].setText(trans('attachments.btn.clear'))
        self.window.ui.nodes['attachments_uploaded.btn.sync'].setText(trans('attachments_uploaded.btn.sync'))
        self.window.ui.nodes['attachments_uploaded.btn.clear'].setText(trans('attachments_uploaded.btn.clear'))
        self.window.ui.nodes['attachments_uploaded.sync.tip'].setText(trans('attachments_uploaded.sync.tip'))

        # tabs
        mode = self.window.core.config.get('mode')
        self.window.controller.attachment.update_tab(mode)
        self.window.controller.assistant.files.update_tab()
        self.window.ui.tabs['input'].setTabText(0, trans('input.tab'))

        # theme menu
        for theme in self.window.ui.menu['theme']:
            name = self.window.controller.theme.trans_theme(theme)
            self.window.ui.menu['theme'][theme].setText(name)

        # plugins info
        self.window.controller.plugins.update_info()

        # update plugins settings
        try:
            self.toggle_plugins()
        except Exception as e:
            print("Error updating plugin locales", e)
            self.window.core.debug.log(e)

        self.window.controller.ctx.update(True, False)
        self.window.controller.ui.update()  # update all (toolbox, etc.)
        self.window.set_status('')  # clear status

    def toggle_plugins(self):
        """Toggle plugins locale"""
        # reload all domains (plugin locale files)
        ids = self.window.core.plugins.plugins.keys()
        for id in ids:
            plugin = self.window.core.plugins.plugins[id]
            if not plugin.use_locale:
                continue
            domain = 'plugin.{}'.format(id)
            trans('', True, domain)

        # apply to settings
        for id in ids:
            plugin = self.window.core.plugins.plugins[id]
            if not plugin.use_locale:
                continue
            domain = 'plugin.{}'.format(id)

            # set name, translate if localization is enabled
            name_txt = trans('plugin.name', False, domain)

            # set description, translate if localization is enabled
            desc_key = 'plugin.settings.' + id + '.desc'
            desc_txt = trans('plugin.description', False, domain)
            if desc_key in self.window.ui.nodes:
                self.window.ui.nodes[desc_key].setText(desc_txt)

            # update tab name
            tab_idx = self.window.controller.plugins.get_tab_idx(id)
            # update tab name
            if tab_idx is not None:
                self.window.ui.tabs['plugin.settings'].setTabText(tab_idx, name_txt)

            if id in self.window.ui.menu['plugins']:
                self.window.ui.menu['plugins'][id].setText(name_txt)

            option_ids = plugin.setup().keys()
            for option_id in option_ids:
                # prepare element nodes keys
                label_key = 'plugin.' + id + '.' + option_id + '.label'
                desc_key = 'plugin.' + id + '.' + option_id + '.desc'

                # update options label, description and tooltip
                label_str = trans(option_id + '.label', False, domain)
                desc_str = trans(option_id + '.description', False, domain)
                tooltip_str = trans(option_id + '.tooltip', False, domain)

                if tooltip_str == option_id + '.tooltip':
                    tooltip_str = desc_str
                if label_key in self.window.ui.nodes:
                    self.window.ui.nodes[label_key].setText(label_str)
                if desc_key in self.window.ui.nodes:
                    self.window.ui.nodes[desc_key].setText(desc_str)
                    self.window.ui.nodes[desc_key].setToolTip(tooltip_str)

                # update widget tooltip
                if id in self.window.ui.plugin_option and option_id in self.window.ui.plugin_option[id]:
                    try:
                        self.window.ui.plugin_option[id][option_id].setTooltip(tooltip_str)
                    except Exception as e:
                        pass

        # update settings dialog list
        idx = self.window.ui.tabs['plugin.settings'].currentIndex()
        self.window.plugin_settings.update_list('plugin.list', self.window.core.plugins.plugins)
        self.window.controller.plugins.set_by_tab(idx)

    def update_settings_dialogs(self):
        """Update settings dialogs"""
        # load settings options if not loaded yet
        if not self.window.controller.settings.editor.initialized:
            self.window.controller.settings.editor.load_config_options(False)

        # update settings options labels
        for id in self.window.controller.settings.editor.options:
            option = self.window.controller.settings.editor.options[id]
            option_label = 'settings.{}.label'.format(id)
            trans_key = 'settings.{}'.format(option['label'])
            if option['type'] == 'bool':
                if id in self.window.ui.config_option:
                    self.window.ui.config_option[id].box.setText(trans(trans_key))
            else:
                if option_label in self.window.ui.nodes:
                    self.window.ui.nodes[option_label].setText(trans(trans_key))
