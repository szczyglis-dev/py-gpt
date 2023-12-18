#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.18 14:00:00                  #
# ================================================== #

from PySide6.QtGui import QAction, Qt

from ..utils import trans


class Lang:
    def __init__(self, window=None):
        """
        Language change controller

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup language handler"""
        # get files from lang folder
        langs = self.window.config.get_available_langs()
        for lang in langs:
            self.window.menu['lang'][lang] = QAction(lang.upper(), self.window, checkable=True)
            self.window.menu['lang'][lang].triggered.connect(
                lambda checked=None, lang=lang: self.window.controller.lang.toggle(lang))
            self.window.menu['menu.lang'].addAction(self.window.menu['lang'][lang])

        self.update()

    def update(self):
        """Update language menu"""
        for lang in self.window.menu['lang']:
            self.window.menu['lang'][lang].setChecked(False)

        lang = self.window.config.get('lang')
        if lang in self.window.menu['lang']:
            self.window.menu['lang'][lang].setChecked(True)

    def toggle(self, id):
        """
        Toggle language

        :param id: language to toggle
        """
        self.window.config.set('lang', id)
        self.window.config.save()
        trans('', True)

        self.update()

        # output
        self.window.ui.nodes['output.timestamp'].setText(trans('output.timestamp'))

        self.window.ui.tabs['output'].setTabText(0, trans('output.tab.chat'))
        self.window.ui.tabs['output'].setTabText(1, trans('output.tab.files'))
        self.window.ui.tabs['output'].setTabText(2, trans('output.tab.notepad') + " 1")
        self.window.ui.tabs['output'].setTabText(3, trans('output.tab.notepad') + " 2")
        self.window.ui.tabs['output'].setTabText(4, trans('output.tab.notepad') + " 3")
        self.window.ui.tabs['output'].setTabText(5, trans('output.tab.notepad') + " 4")
        self.window.ui.tabs['output'].setTabText(6, trans('output.tab.notepad') + " 5")

        # context
        self.window.ui.nodes['contexts.label'].setText(trans("ctx.contexts.label"))
        self.window.ui.nodes['contexts.new'].setText(trans('context.new'))

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

        self.window.ui.models['attachments'].setHeaderData(0, Qt.Horizontal, trans('attachments.header.name'))
        self.window.ui.models['attachments'].setHeaderData(1, Qt.Horizontal, trans('attachments.header.path'))
        self.window.ui.models['attachments_uploaded'].setHeaderData(0, Qt.Horizontal, trans('attachments.header.name'))
        self.window.ui.models['attachments_uploaded'].setHeaderData(1, Qt.Horizontal, trans('attachments.header.path'))

        # audio
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
        self.window.ui.config_option['assistant.tool.code_interpreter'].box.setText(trans('assistant.tool.code_interpreter'))

        # settings dialog
        self.update_settings_dialogs()
        self.window.dialog['config.settings'].setWindowTitle(trans('dialog.settings'))
        self.window.ui.nodes['settings.btn.defaults.user'].setText(trans("dialog.settings.btn.defaults.user"))
        self.window.ui.nodes['settings.btn.defaults.app'].setText(trans("dialog.settings.btn.defaults.app"))
        self.window.ui.nodes['settings.btn.save'].setText(trans("dialog.settings.btn.save"))

        # plugin settings dialog
        self.window.ui.nodes['plugin.settings.btn.defaults.user'].setText(trans("dialog.plugin.settings.btn.defaults.user"))
        self.window.ui.nodes['plugin.settings.btn.defaults.app'].setText(trans("dialog.plugin.settings.btn.defaults.app"))
        self.window.ui.nodes['plugin.settings.btn.save'].setText(trans("dialog.plugin.settings.btn.save"))

        # preset dialog
        self.window.dialog['editor.preset.presets'].setWindowTitle(trans('dialog.preset'))
        self.window.ui.nodes['preset.filename.label'].setText(trans("preset.filename"))
        self.window.ui.nodes['preset.name.label'].setText(trans("preset.name"))
        self.window.ui.nodes['preset.ai_name.label'].setText(trans("preset.ai_name"))
        self.window.ui.nodes['preset.user_name.label'].setText(trans("preset.user_name"))
        self.window.ui.nodes['preset.temperature.label'].setText(trans("preset.temperature"))
        self.window.ui.nodes['preset.prompt.label'].setText(trans("preset.prompt"))
        self.window.ui.nodes['cmd.enabled'].setText(trans('cmd.enabled'))
        self.window.ui.config_option['preset.chat'].box.setText(trans("preset.chat"))
        self.window.ui.config_option['preset.completion'].box.setText(trans("preset.completion"))
        self.window.ui.config_option['preset.img'].box.setText(trans("preset.img"))
        self.window.ui.config_option['img_raw'].setText(trans("img.raw"))

        # vision
        self.window.ui.nodes['vision.capture.enable'].setText(trans("vision.capture.enable"))
        self.window.ui.nodes['vision.capture.enable'].setToolTip(trans("vision.capture.enable.tooltip"))
        self.window.ui.nodes['vision.capture.auto'].setText(trans("vision.capture.auto"))
        self.window.ui.nodes['vision.capture.auto'].setToolTip(trans('vision.capture.auto.tooltip'))
        self.window.ui.nodes['vision.capture.label'].setText(trans('vision.capture.options.title'))

        # capture label
        if not self.window.config.get('vision.capture.auto'):
            self.window.ui.nodes['video.preview'].label.setText(trans("vision.capture.label"))
        else:
            self.window.ui.nodes['video.preview'].label.setText(trans("vision.capture.auto.label"))

        # buttons
        self.window.ui.nodes['preset.btn.current'].setText(trans("dialog.preset.btn.current"))
        self.window.ui.nodes['preset.btn.save'].setText(trans("dialog.preset.btn.save"))

        # editor dialog
        self.window.ui.nodes['dialog.editor.label'].setText(trans('dialog.editor.label'))
        self.window.ui.nodes['editor.btn.default'].setText(trans("dialog.editor.btn.defaults"))
        self.window.ui.nodes['editor.btn.save'].setText(trans("dialog.editor.btn.save"))
        self.window.dialog['config.editor'].setWindowTitle(trans('dialog.editor.title'))

        # rename dialog
        self.window.dialog['rename'].setWindowTitle(trans("dialog.rename.title"))
        self.window.ui.nodes['dialog.rename.label'].setText(trans("dialog.rename.title"))
        self.window.ui.nodes['dialog.rename.btn.update'].setText(trans("dialog.rename.update"))
        self.window.ui.nodes['dialog.rename.btn.dismiss'].setText(trans("dialog.rename.dismiss"))

        # changelog dialog
        self.window.ui.nodes['dialog.changelog.label'].setText(trans("dialog.changelog.title"))
        self.window.dialog['info.changelog'].setWindowTitle(trans("dialog.changelog.title"))

        # about dialog
        string = "PY-GPT\n" \
                 "-------------\n" \
                 "{}: {}\n" \
                 "{}: {}\n" \
                 "{}: {}\n" \
                 "{}: {}\n\n" \
                 "(c) 2023 {}\n" \
                 "{}\n".format(trans("dialog.about.version"),
                               self.window.meta['version'],
                               trans("dialog.about.build"),
                               self.window.meta['build'],

                               trans("dialog.about.website"),
                               self.window.meta['website'],
                               trans("dialog.about.github"),
                               self.window.meta['github'],
                               self.window.meta['author'],
                               self.window.meta['email'])
        self.window.ui.nodes['dialog.about.content'].setText(string)
        self.window.dialog['info.about'].setWindowTitle(trans("dialog.about.title"))
        self.window.dialog['editor.assistants'].setWindowTitle(trans('dialog.assistant'))

        # menu
        self.window.menu['menu.app'].setTitle(trans("menu.file"))
        self.window.menu['app.exit'].setText(trans("menu.file.exit"))
        self.window.menu['app.clear_history'].setText(trans("menu.file_clear_history"))

        self.window.menu['menu.plugins'].setTitle(trans("menu.plugins"))
        self.window.menu['menu.audio'].setTitle(trans("menu.audio"))

        self.window.menu['menu.config'].setTitle(trans("menu.config"))
        self.window.menu['config.settings'].setText(trans("menu.config.settings"))
        self.window.menu['config.edit.config'].setText(trans("menu.config.edit.config"))
        self.window.menu['config.edit.models'].setText(trans("menu.config.edit.models"))
        self.window.menu['config.open_dir'].setText(trans("menu.config.open_dir"))
        self.window.menu['config.save'].setText(trans("menu.config.save"))

        self.window.menu['menu.lang'].setTitle(trans("menu.lang"))
        self.window.menu['menu.theme'].setTitle(trans("menu.theme"))

        # debug menu
        if 'menu.debug' in self.window.menu:
            self.window.menu['menu.debug'].setTitle(trans("menu.debug"))
            self.window.menu['debug.config'].setText(trans("menu.debug.config"))
            self.window.menu['debug.context'].setText(trans("menu.debug.context"))
            self.window.menu['debug.presets'].setText(trans("menu.debug.presets"))
            self.window.menu['debug.models'].setText(trans("menu.debug.models"))

        self.window.menu['menu.about'].setTitle(trans("menu.info"))
        self.window.menu['info.about'].setText(trans("menu.info.about"))
        self.window.menu['info.changelog'].setText(trans("menu.info.changelog"))
        self.window.menu['info.docs'].setText(trans("menu.info.docs"))
        self.window.menu['info.pypi'].setText(trans("menu.info.pypi"))
        self.window.menu['info.website'].setText(trans("menu.info.website"))
        self.window.menu['info.github'].setText(trans("menu.info.github"))

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

        # plugins info
        self.window.controller.plugins.update_info()

        # tabs
        mode = self.window.config.get('mode')
        self.window.controller.attachment.update_tab_label(mode)
        self.window.controller.assistant_files.update_tab_label()
        self.window.ui.tabs['input'].setTabText(0, trans('input.tab'))

        # theme menu
        for theme in self.window.menu['theme']:
            name = self.window.controller.theme.trans_theme(theme)
            self.window.menu['theme'][theme].setText(name)

        self.window.controller.ui.update()  # update all (toolbox, etc.)
        self.window.set_status('')

    def update_settings_dialogs(self):
        """
        Update settings dialogs
        """
        # load settings options if not loaded yet
        if not self.window.controller.settings.initialized:
            self.window.controller.settings.load_config_options(False)

        # update settings options labels
        for id in self.window.controller.settings.options:
            option = self.window.controller.settings.options[id]
            option_label = 'settings.{}.label'.format(id)
            trans_key = 'settings.{}'.format(option['label'])
            if option['type'] == 'bool':
                if id in self.window.ui.config_option:
                    self.window.ui.config_option[id].box.setText(trans(trans_key))
            else:
                if option_label in self.window.ui.nodes:
                    self.window.ui.nodes[option_label].setText(trans(trans_key))
