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


class About:
    def __init__(self, window=None):
        """
        Menu setup

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup about menu"""
        w = self.window
        m = w.ui.menu

        icon_info = QIcon(":/icons/info.svg")
        icon_history = QIcon(":/icons/history.svg")
        icon_updater = QIcon(":/icons/updater.svg")
        icon_public = QIcon(":/icons/public_filled.svg")
        icon_favorite = QIcon(":/icons/favorite.svg")

        m['info.about'] = QAction(icon_info, trans("menu.info.about"), w)
        m['info.about'].setMenuRole(QAction.MenuRole.NoRole)
        m['info.changelog'] = QAction(icon_history, trans("menu.info.changelog"), w)
        m['info.updates'] = QAction(icon_updater, trans("menu.info.updates"), w)
        m['info.report'] = QAction(icon_public, trans("menu.info.report"), w)
        m['info.website'] = QAction(icon_public, trans("menu.info.website"), w)
        m['info.docs'] = QAction(icon_public, trans("menu.info.docs"), w)
        m['info.pypi'] = QAction(icon_public, trans("menu.info.pypi"), w)
        m['info.snap'] = QAction(icon_public, trans("menu.info.snap"), w)
        m['info.ms_store'] = QAction(icon_public, trans("menu.info.ms_store"), w)
        m['info.github'] = QAction(icon_public, trans("menu.info.github"), w)
        m['info.discord'] = QAction(icon_public, trans("menu.info.discord"), w)
        m['info.license'] = QAction(icon_info, trans("menu.info.license"), w)

        m['donate.coffee'] = QAction(icon_favorite, "Buy me a coffee", w)
        m['donate.coffee'].setMenuRole(QAction.MenuRole.NoRole)
        m['donate.paypal'] = QAction(icon_favorite, "PayPal", w)
        m['donate.github'] = QAction(icon_favorite, "GitHub Sponsors", w)

        dlg_info = w.controller.dialogs.info
        launcher = w.controller.launcher

        m['donate.coffee'].triggered.connect(lambda checked=False, i=dlg_info: i.donate('coffee'))
        m['donate.paypal'].triggered.connect(lambda checked=False, i=dlg_info: i.donate('paypal'))
        m['donate.github'].triggered.connect(lambda checked=False, i=dlg_info: i.donate('github'))

        m['info.about'].triggered.connect(lambda checked=False, i=dlg_info: i.toggle('about'))
        m['info.changelog'].triggered.connect(lambda checked=False, i=dlg_info: i.toggle('changelog'))
        m['info.updates'].triggered.connect(lambda checked=False, l=launcher: l.check_updates())
        m['info.report'].triggered.connect(lambda checked=False, i=dlg_info: i.goto_report())
        m['info.website'].triggered.connect(lambda checked=False, i=dlg_info: i.goto_website())
        m['info.docs'].triggered.connect(lambda checked=False, i=dlg_info: i.goto_docs())
        m['info.pypi'].triggered.connect(lambda checked=False, i=dlg_info: i.goto_pypi())
        m['info.snap'].triggered.connect(lambda checked=False, i=dlg_info: i.goto_snap())
        m['info.ms_store'].triggered.connect(lambda checked=False, i=dlg_info: i.goto_ms_store())
        m['info.github'].triggered.connect(lambda checked=False, i=dlg_info: i.goto_github())
        m['info.discord'].triggered.connect(lambda checked=False, i=dlg_info: i.goto_discord())
        m['info.license'].triggered.connect(lambda checked=False, i=dlg_info: i.toggle('license', width=500, height=480))

        m['menu.about'] = w.menuBar().addMenu(trans("menu.info"))
        m['menu.about'].addActions([
            m['info.about'],
            m['info.changelog'],
            m['info.updates'],
            m['info.report'],
            m['info.docs'],
            m['info.website'],
            m['info.github'],
            m['info.pypi'],
            m['info.snap'],
            m['info.ms_store'],
            m['info.discord'],
            m['info.license'],
        ])

        m['menu.donate'] = m['menu.about'].addMenu(trans("menu.info.donate"))
        m['menu.donate'].addActions([
            m['donate.coffee'],
            m['donate.paypal'],
            m['donate.github'],
        ])