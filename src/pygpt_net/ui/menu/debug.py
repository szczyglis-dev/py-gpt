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

        # add separator and sub-menu with Chrome debug
        menu.addSeparator()

        # Sub-menu "Chrome"
        m['menu.debug.chrome'] = menu.addMenu("Chromium")
        chrome_urls = {
            'sandbox': ('Sandbox', 'chrome://sandbox'),
            'gpu': ('GPU', 'chrome://gpu'),
            'version': ('Version', 'chrome://version'),
            'flags': ('Flags', 'chrome://flags'),
            'components': ('Components', 'chrome://components'),
            'policy': ('Policy', 'chrome://policy'),
            'dns': ('DNS', 'chrome://dns'),
            'net_export': ('Net Export', 'chrome://net-export'),
            'media_internals': ('Media Internals', 'chrome://media-internals'),
            'webrtc_internals': ('WebRTC Internals', 'chrome://webrtc-internals'),
            'discards': ('Discards (Tab Discarding)', 'chrome://discards'),
            'crashes': ('Crashes', 'chrome://crashes'),
            'histograms': ('Histograms', 'chrome://histograms'),
            'process_internals': ('Process Internals', 'chrome://process-internals'),
            'tracing': ('Tracing', 'chrome://tracing'),
            'chrome_urls': ('All Chrome URLs', 'chrome://chrome-urls'),
        }

        for key, (label, url) in chrome_urls.items():
            action_key = f"debug.chrome.{key}"
            m[action_key] = QAction(label, win)
            m[action_key].triggered.connect(lambda _=False, u=url: dbg.open_chrome_debug(u))
            m['menu.debug.chrome'].addAction(m[action_key])

        m['debug.render'].setChecked(bool(win.core.config.get('debug.render')))