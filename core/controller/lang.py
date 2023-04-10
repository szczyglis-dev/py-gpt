#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Created Date: 2023.04.09 20:00:00                  #
# ================================================== #

from PySide6.QtGui import QAction

from core.utils import trans


class Lang:
    def __init__(self, window=None):
        """
        Language change controller

        :param window: main UI window object
        """
        self.window = window

    def setup(self):
        """Setups language handler"""
        # get files from lang folder
        langs = self.window.config.get_available_langs()
        for lang in langs:
            self.window.menu['lang'][lang] = QAction(lang.upper(), self.window, checkable=True)
            self.window.menu['lang'][lang].triggered.connect(
                lambda checked=None, lang=lang: self.window.controller.lang.toggle(lang))
            self.window.menu['menu.lang'].addAction(self.window.menu['lang'][lang])

        self.update()

    def update(self):
        """Updates language menu"""
        for lang in self.window.menu['lang']:
            self.window.menu['lang'][lang].setChecked(False)

        if self.window.config.data['lang'] in self.window.menu['lang']:
            self.window.menu['lang'][self.window.config.data['lang']].setChecked(True)

    def toggle(self, id):
        """
        Toggles language

        :param id: language to toggle
        """
        self.window.config.data['lang'] = id
        self.window.config.save()
        trans('', True)

        self.update()

        # output
        self.window.data['chat.label'].setText(trans("chatbox.label"))
        self.window.data['output.timestamp'].setText(trans('output.timestamp'))

        # context
        self.window.data['contexts.label'].setText(trans("ctx.contexts.label"))
        self.window.data['contexts.new'].setText(trans('context.new'))

        # toolbox
        self.window.data['prompt.mode.label'].setText(trans("toolbox.mode.label"))
        self.window.data['prompt.model.label'].setText(trans("toolbox.model.label"))
        self.window.data['preset.presets.label'].setText(trans("toolbox.presets.label"))
        self.window.data['preset.presets.new'].setText(trans('preset.new'))
        self.window.data['preset.clear'].setText(trans('preset.clear'))
        self.window.data['preset.use'].setText(trans('preset.use'))
        self.window.data['toolbox.preset.ai_name.label'].setText(trans('toolbox.name.ai'))
        self.window.data['toolbox.preset.user_name.label'].setText(trans('toolbox.name.user'))
        self.window.data['toolbox.prompt.label'].setText(trans("toolbox.prompt"))
        self.window.data['temperature.label'].setText(trans("toolbox.temperature.label"))

        # input
        self.window.data['input.label'].setText(trans("input.label"))
        self.window.data['input.send_enter'].setText(trans("input.radio.enter"))
        self.window.data['input.send_shift_enter'].setText(trans("input.radio.enter_shift"))
        self.window.data['input.send_clear'].setText(trans('input.send_clear'))
        self.window.data['input.send_btn'].setText(trans("input.btn.send"))

        # settings dialog
        self.window.data['settings.temperature.label'].setText(trans("settings.temperature"))
        self.window.data['settings.top_p.label'].setText(trans("settings.top_p"))
        self.window.data['settings.frequency_penalty.label'].setText(trans("settings.frequency_penalty"))
        self.window.data['settings.presence_penalty.label'].setText(trans("settings.presence_penalty"))
        self.window.config_option['use_context'].box.setText(trans("settings.use_context"))
        self.window.config_option['store_history'].box.setText(trans("settings.store_history"))
        self.window.config_option['store_history_time'].box.setText(trans("settings.store_history_time"))
        self.window.data['settings.context_threshold.label'].setText(trans("settings.context_threshold"))
        self.window.data['settings.max_output_tokens.label'].setText(trans("settings.max_output_tokens"))
        self.window.data['settings.max_total_tokens.label'].setText(trans("settings.max_total_tokens"))
        self.window.data['settings.img_resolution.label'].setText(trans("settings.img_resolution"))
        self.window.data['settings.api_key.label'].setText(trans("settings.api_key"))
        self.window.data['settings.organization_key.label'].setText(trans("settings.organization_key"))
        self.window.dialog['config.settings'].setWindowTitle(trans('dialog.settings'))

        # buttons
        self.window.data['settings.btn.defaults'].setText(trans("dialog.settings.btn.defaults"))
        self.window.data['settings.btn.save'].setText(trans("dialog.settings.btn.save"))

        # preset dialog
        self.window.data['preset.filename.label'].setText(trans("preset.filename"))
        self.window.data['preset.name.label'].setText(trans("preset.name"))
        self.window.data['preset.ai_name.label'].setText(trans("preset.ai_name"))
        self.window.data['preset.user_name.label'].setText(trans("preset.user_name"))
        self.window.config_option['preset.chat'].box.setText(trans("preset.chat"))
        self.window.config_option['preset.completion'].box.setText(trans("preset.completion"))
        self.window.config_option['preset.img'].box.setText(trans("preset.img"))
        self.window.data['preset.temperature.label'].setText(trans("preset.temperature"))
        self.window.data['preset.prompt.label'].setText(trans("preset.prompt"))
        self.window.dialog['editor.preset.presets'].setWindowTitle(trans('dialog.preset'))

        # buttons
        self.window.data['preset.btn.current'].setText(trans("dialog.preset.btn.current"))
        self.window.data['preset.btn.save'].setText(trans("dialog.preset.btn.save"))

        # editor dialog
        self.window.data['dialog.editor.label'].setText(trans('dialog.editor.label'))
        self.window.data['editor.btn.default'].setText(trans("dialog.editor.btn.defaults"))
        self.window.data['editor.btn.save'].setText(trans("dialog.editor.btn.save"))
        self.window.dialog['config.editor'].setWindowTitle(trans('dialog.editor.title'))

        # ctx rename dialog
        self.window.dialog['ctx.rename'].setWindowTitle(trans("dialog.ctx.rename.title"))
        self.window.data['dialog.ctx_rename.label'].setText(trans("dialog.ctx.rename.title"))
        self.window.data['dialog.ctx_rename.btn.update'].setText(trans("dialog.ctx.rename.update"))
        self.window.data['dialog.ctx_rename.btn.dismiss'].setText(trans("dialog.ctx.rename.dismiss"))

        # changelog dialog
        self.window.data['dialog.changelog.label'].setText(trans("dialog.changelog.title"))
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
                               self.window.version,
                               trans("dialog.about.build"),
                               self.window.build,

                               trans("dialog.about.website"),
                               self.window.website,
                               trans("dialog.about.github"),
                               self.window.github,
                               self.window.author,
                               self.window.email)
        self.window.data['dialog.about.content'].setText(string)
        self.window.dialog['info.about'].setWindowTitle(trans("dialog.about.title"))

        # menu
        self.window.menu['menu.app'].setTitle(trans("menu.file"))
        self.window.menu['app.exit'].setText(trans("menu.file.exit"))
        self.window.menu['app.clear_history'].setText(trans("menu.file_clear_history"))

        self.window.menu['menu.plugins'].setTitle(trans("menu.plugins"))
        self.window.menu['plugins.empty'].setText(trans("coming_soon"))

        self.window.menu['menu.audio'].setTitle(trans("menu.audio"))
        self.window.menu['audio.empty'].setText(trans("coming_soon"))

        self.window.menu['menu.config'].setTitle(trans("menu.config"))
        self.window.menu['config.settings'].setText(trans("menu.config.settings"))
        self.window.menu['config.edit.config'].setText(trans("menu.config.edit.config"))
        self.window.menu['config.edit.models'].setText(trans("menu.config.edit.models"))
        self.window.menu['config.open_dir'].setText(trans("menu.config.open_dir"))
        self.window.menu['config.save'].setText(trans("menu.config.save"))

        self.window.menu['menu.lang'].setTitle(trans("menu.lang"))

        if 'menu.debug' in self.window.menu:
            self.window.menu['menu.debug'].setTitle(trans("menu.debug"))
            self.window.menu['debug.config'].setText(trans("menu.debug.config"))
            self.window.menu['debug.context'].setText(trans("menu.debug.context"))
            self.window.menu['debug.presets'].setText(trans("menu.debug.presets"))
            self.window.menu['debug.models'].setText(trans("menu.debug.models"))

        self.window.menu['menu.about'].setTitle(trans("menu.info"))
        self.window.menu['info.about'].setText(trans("menu.info.about"))
        self.window.menu['info.changelog'].setText(trans("menu.info.changelog"))
        self.window.menu['info.website'].setText(trans("menu.info.website"))
        self.window.menu['info.github'].setText(trans("menu.info.github"))

        self.window.controller.model.update()
        self.window.set_status('')
