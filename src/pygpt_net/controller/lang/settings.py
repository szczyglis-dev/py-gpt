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


class Settings:
    def __init__(self, window=None):
        """
        Settings locale controller

        :param window: Window instance
        """
        self.window = window

    def apply(self):
        """Apply locale to settings dialog"""
        if not self.window.controller.settings.editor.initialized:
            self.window.controller.settings.editor.load_config_options(False)

        w = self.window
        tr = trans
        ctrl_settings = w.controller.settings
        editor = ctrl_settings.editor
        options = editor.options
        ui = w.ui
        ui_nodes = ui.nodes
        ui_tabs = ui.tabs
        ui_config = ui.config['config']

        for opt_id, option in options.items():
            t_label = tr(option['label'])
            if option.get('type') == 'bool':
                if opt_id in ui_config:
                    widget = ui_config[opt_id]
                    if hasattr(widget, 'setText'):
                        widget.setText(t_label)
                    widget.box.setText(t_label)
            else:
                node_key = f'settings.{opt_id}.label'
                node = ui_nodes.get(node_key)
                if node is not None:
                    node.setText(t_label)

            if 'description' in option and option['description'] is not None and option['description'].strip() != "":
                desc = option['description']
                t_desc = tr(desc)
                node_key1 = f'settings.{opt_id}.desc'
                node1 = ui_nodes.get(node_key1)
                if node1 is not None:
                    node1.setText(t_desc)
                node2 = ui_nodes.get(desc)
                if node2 is not None:
                    node2.setText(t_desc)

        sections = w.core.settings.get_sections()
        tabs = ui_tabs['settings.section']
        for i, section_id in enumerate(sections.keys()):
            tabs.setTabText(i, tr(f'settings.section.{section_id}'))

        idx = tabs.currentIndex()
        w.settings.refresh_list()
        ctrl_settings.set_by_tab(idx)