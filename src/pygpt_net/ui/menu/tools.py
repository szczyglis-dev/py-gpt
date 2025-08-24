#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.24 23:00:00                  #
# ================================================== #

from PySide6.QtGui import QAction, QIcon

from pygpt_net.utils import trans

class Tools:
    def __init__(self, window=None):
        """
        Tools menu setup

        :param window: Window instance
        """
        self.window = window

    def _open_tab_action(self, checked=False):
        action = self.window.sender()
        self.window.controller.tools.open_tab(action.data())

    def _toggle_assistant_store(self, checked=False):
        self.window.controller.assistant.store.toggle_editor()

    def _rebuild_ipython(self, checked=False):
        self.window.core.plugins.get("cmd_code_interpreter").builder.build_and_restart()

    def _rebuild_python_legacy(self, checked=False):
        self.window.core.plugins.get("cmd_code_interpreter").docker.build_and_restart()

    def _rebuild_system(self, checked=False):
        self.window.core.plugins.get("cmd_system").docker.build_and_restart()

    def setup(self):
        """Setup tools menu"""
        window = self.window
        ui_menu = window.ui.menu

        tab_tools = window.controller.tools.get_tab_tools()
        ui_menu['menu.tools'] = window.menuBar().addMenu(trans("menu.tools"))
        menu_tools = ui_menu['menu.tools']

        for key, val in tab_tools.items():
            label_key, icon_name, type_ = val[0], val[1], val[2]
            action = QAction(QIcon(f":/icons/{icon_name}.svg"), trans(f"output.tab.{label_key}"), window)
            action.setCheckable(False)
            action.triggered.connect(lambda checked=False, t=type_: window.controller.tools.open_tab(t))
            ui_menu[key] = action
            menu_tools.addAction(action)

        actions = window.tools.setup_menu_actions()
        if len(actions) == 0:
            return

        menu_tools.addSeparator()

        for key, action in actions.items():
            ui_menu[key] = action
            menu_tools.addAction(action)

        # ------------------------------------------------- #

        menu_tools.addSeparator()
        db_icon = QIcon(":/icons/db.svg")
        ui_menu['menu.tools.openai.stores'] = QAction(db_icon, trans("dialog.assistant.store"), window)
        menu_tools.addAction(ui_menu['menu.tools.openai.stores'])
        ui_menu['menu.tools.openai.stores'].triggered.connect(self._toggle_assistant_store)

        menu_tools.addSeparator()
        reload_icon = QIcon(":/icons/reload.svg")
        ui_menu['menu.tools.ipython.rebuild'] = QAction(reload_icon, "Rebuild IPython Docker Image", window)
        menu_tools.addAction(ui_menu['menu.tools.ipython.rebuild'])
        ui_menu['menu.tools.ipython.rebuild'].triggered.connect(self._rebuild_ipython)

        ui_menu['menu.tools.python_legacy.rebuild'] = QAction(reload_icon, "Rebuild Python (Legacy) Docker Image", window)
        menu_tools.addAction(ui_menu['menu.tools.python_legacy.rebuild'])
        ui_menu['menu.tools.python_legacy.rebuild'].triggered.connect(self._rebuild_python_legacy)

        ui_menu['menu.tools.system.rebuild'] = QAction(reload_icon, "Rebuild System Sandbox Docker Image", window)
        menu_tools.addAction(ui_menu['menu.tools.system.rebuild'])
        ui_menu['menu.tools.system.rebuild'].triggered.connect(self._rebuild_system)