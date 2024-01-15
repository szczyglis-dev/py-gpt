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


class Plugins:
    def __init__(self, window=None):
        """
        Plugins locale controller

        :param window: Window instance
        """
        self.window = window

    def apply(self):
        """Apply locale to plugins"""

        # plugins: info
        self.window.controller.plugins.update_info()

        # reload all domains (plugin locale files)
        ids = self.window.core.plugins.plugins.keys()
        for id in ids:
            plugin = self.window.core.plugins.plugins[id]
            if not plugin.use_locale:
                continue
            domain = 'plugin.{}'.format(id)
            trans('', True, domain)

        # apply to plugin settings
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

            options = plugin.setup()
            option_ids = options.keys()
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

                if options[option_id]['type'] == 'bool':
                    # update checkbox label
                    if domain in self.window.ui.config and option_id in self.window.ui.config[domain]:
                        try:
                            self.window.ui.config[domain][option_id].box.setText(label_str)
                        except Exception as e:
                            pass

        # update settings dialog list
        idx = self.window.ui.tabs['plugin.settings'].currentIndex()
        self.window.plugin_settings.update_list('plugin.list', self.window.core.plugins.plugins)
        self.window.controller.plugins.set_by_tab(idx)
