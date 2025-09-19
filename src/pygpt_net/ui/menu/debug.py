#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.19 00:00:00                  #
# ================================================== #

from PySide6.QtGui import QAction

from pygpt_net.utils import trans


class Debug:
    def __init__(self, window=None):
        """
        Menu setup

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup debug menu"""
        win = self.window
        ui = win.ui
        m = ui.menu
        dbg = win.controller.debug

        keys = (
            'config',
            'context',
            'presets',
            'models',
            'plugins',
            'attachments',
            'assistants',
            'agent',
            # 'agent_builder',
            'events',
            'indexes',
            'ui',
            'tabs',
            'db',
            'logger',
            'app.log',
            'fixtures.stream',
            'kernel',
            'render'
        )
        for k in keys:
            m[f'debug.{k}'] = QAction(trans(f"menu.debug.{k}"), win, checkable=True)

        for k in ('config',
                  'context',
                  'presets',
                  'models',
                  'plugins',
                  'attachments',
                  'assistants',
                  'agent',
                  # 'agent_builder',
                  'events',
                  'indexes',
                  'ui',
                  'tabs',
                  'db',
                  'kernel'):
            m[f'debug.{k}'].triggered.connect(lambda _=False, kk=k: dbg.toggle(kk))

        m['debug.logger'].triggered.connect(dbg.toggle_logger)
        m['debug.app.log'].triggered.connect(dbg.toggle_app_log)
        m['debug.render'].triggered.connect(dbg.toggle_render)
        m['debug.fixtures.stream'].triggered.connect(
            lambda _=False: dbg.fixtures.toggle_from_menu("stream")
        )

        m['menu.debug'] = win.menuBar().addMenu(trans("menu.debug"))
        menu = m['menu.debug']
        menu.addActions(
            [
                m['debug.logger'],
                m['debug.render'],
                m['debug.db'],
                m['debug.app.log']
            ]
        )

        menu.addSeparator()
        menu.addActions(
            [
                m['debug.fixtures.stream']
            ]
        )

        menu.addSeparator()
        menu.addActions(
            [
                m['debug.agent'],
                # m['debug.agent_builder'],
                m['debug.assistants'],
                m['debug.attachments'],
                m['debug.config'],
                m['debug.context'],
                m['debug.events'],
                m['debug.indexes'],
                m['debug.kernel'],
                m['debug.models'],
                m['debug.plugins'],
                m['debug.presets'],
                m['debug.tabs'],
                m['debug.ui'],
            ]
        )

        m['debug.render'].setChecked(bool(win.core.config.get('debug.render')))