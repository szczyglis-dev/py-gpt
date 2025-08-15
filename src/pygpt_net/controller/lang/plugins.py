#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.15 23:00:00                  #
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

        plugins_dict = self.window.core.plugins.plugins
        plugin_ids = tuple(plugins_dict.keys())
        win = self.window
        ui = win.ui
        ui_nodes = ui.nodes
        ui_tabs = ui.tabs
        settings_tab = ui_tabs['plugin.settings']
        ui_menu_plugins = ui.menu.get('plugins', {})
        ui_config = ui.config
        ctrl_plugins = win.controller.plugins

        for plugin_id in plugin_ids:
            plugin = plugins_dict[plugin_id]
            if not plugin.use_locale:
                continue
            domain = f'plugin.{plugin_id}'
            trans('', True, domain)

        for plugin_id in plugin_ids:
            plugin = plugins_dict[plugin_id]
            if not plugin.use_locale:
                continue
            domain = f'plugin.{plugin_id}'

            name_txt = trans('plugin.name', False, domain)

            plugin_settings_desc_key = f'plugin.settings.{plugin_id}.desc'
            if plugin_settings_desc_key in ui_nodes:
                desc_txt = trans('plugin.description', False, domain)
                ui_nodes[plugin_settings_desc_key].setText(desc_txt)

            tab_idx = ctrl_plugins.get_tab_idx(plugin_id)
            if tab_idx is not None:
                settings_tab.setTabText(tab_idx, name_txt)

            if plugin_id in ui_menu_plugins:
                ui_menu_plugins[plugin_id].setText(name_txt)

            options = plugin.setup()
            if not options:
                continue

            cfg_domain = ui_config.get(domain)
            for option_id, option in options.items():
                label_key = f'plugin.{plugin_id}.{option_id}.label'
                desc_key = f'plugin.{plugin_id}.{option_id}.desc'

                is_bool = option.get('type') == 'bool'
                need_label = (label_key in ui_nodes) or (is_bool and cfg_domain and option_id in cfg_domain)
                need_desc = desc_key in ui_nodes

                label_str = None
                if need_label:
                    label_str = trans(f'{option_id}.label', False, domain)

                if need_desc:
                    desc_str = trans(f'{option_id}.description', False, domain)
                    tooltip_str = trans(f'{option_id}.tooltip', False, domain)
                    if tooltip_str == f'{option_id}.tooltip':
                        tooltip_str = desc_str
                    ui_nodes[desc_key].setText(desc_str)
                    ui_nodes[desc_key].setToolTip(tooltip_str)

                if label_key in ui_nodes and label_str is not None:
                    ui_nodes[label_key].setText(label_str)

                if is_bool and cfg_domain and option_id in cfg_domain and label_str is not None:
                    widget = cfg_domain[option_id]
                    if hasattr(widget, 'setText'):
                        widget.setText(label_str)
                    box = getattr(widget, 'box', None)
                    if box and hasattr(box, 'setText'):
                        box.setText(label_str)

        idx = settings_tab.currentIndex()
        win.plugin_settings.update_list('plugin.list', plugins_dict)
        ctrl_plugins.set_by_tab(idx)