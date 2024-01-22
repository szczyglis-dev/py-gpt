#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.22 10:00:00                  #
# ================================================== #

from pygpt_net.utils import trans


class Settings:
    def __init__(self, window=None):
        """
        Settings locale controller

        :param window: Window instance
        """
        self.window = window

    def apply(self):
        """Apply locale to settings dialog"""
        # load settings options if not loaded yet
        if not self.window.controller.settings.editor.initialized:
            self.window.controller.settings.editor.load_config_options(False)

        # update settings options labels
        for id in self.window.controller.settings.editor.options:
            option = self.window.controller.settings.editor.options[id]
            option_label = 'settings.{}.label'.format(id)  # TODO: check
            option_desc = 'settings.{}.desc'.format(id)  # TODO: check
            trans_key = '{}'.format(option['label'])

            # label
            if option['type'] == 'bool':
                if id in self.window.ui.config['config']:
                    self.window.ui.config['config'][id].box.setText(trans(trans_key))
            else:
                if option_label in self.window.ui.nodes:
                    self.window.ui.nodes[option_label].setText(trans(trans_key))

            # description
            if option_desc in self.window.ui.nodes:
                if 'description' in option \
                        and option['description'] is not None \
                        and option['description'].strip() != "":
                    trans_desc_key = '{}'.format(option['description'])
                    self.window.ui.nodes[option_desc].setText(trans(trans_desc_key))

        # update sections tabs
        sections = self.window.core.settings.get_sections()
        i = 0
        for section_id in sections.keys():
            key = 'settings.section.' + section_id.replace("-", "_")
            self.window.ui.tabs['settings.section'].setTabText(i, trans(key))
            i += 1

        # update sections list
        idx = self.window.ui.tabs['settings.section'].currentIndex()
        self.window.settings.refresh_list()
        self.window.controller.settings.set_by_tab(idx)
