#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.17 01:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QPushButton, QLabel, QVBoxLayout, QWidget, QHBoxLayout

from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.utils import trans


class CtxTab:
    def __init__(self, window=None):
        """
        Tab: Context indexing

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """
        Setup tab widget
        """
        self.window.ui.nodes["tool.indexer.ctx.last_auto.label"] = HelpLabel(trans("tool.indexer.tab.ctx.last_auto"))
        self.window.ui.nodes["tool.indexer.ctx.last_auto"] = QLabel("")

        self.window.ui.nodes["tool.indexer.ctx.auto_enabled.label"] = HelpLabel(trans("tool.indexer.tab.ctx.auto_enabled"))
        self.window.ui.nodes["tool.indexer.ctx.auto_enabled"] = QLabel("")

        self.window.ui.nodes["tool.indexer.ctx.last_meta_id.label"] = HelpLabel(trans("tool.indexer.tab.ctx.last_meta_id"))
        self.window.ui.nodes["tool.indexer.ctx.last_meta_id"] = QLabel("")

        self.window.ui.nodes["tool.indexer.ctx.last_meta_ts.label"] = HelpLabel(trans("tool.indexer.tab.ctx.last_meta_ts"))
        self.window.ui.nodes["tool.indexer.ctx.last_meta_ts"] = QLabel("")

        # auto db index enabled
        auto_enabled_layout = QHBoxLayout()
        auto_enabled_layout.addWidget(self.window.ui.nodes["tool.indexer.ctx.auto_enabled.label"])
        auto_enabled_layout.addWidget(self.window.ui.nodes["tool.indexer.ctx.auto_enabled"])

        # auto db index TS
        last_auto_layout = QHBoxLayout()
        last_auto_layout.addWidget(self.window.ui.nodes["tool.indexer.ctx.last_auto.label"])
        last_auto_layout.addWidget(self.window.ui.nodes["tool.indexer.ctx.last_auto"])

        # last meta in DB
        last_meta_layout = QHBoxLayout()
        last_meta_layout.addWidget(self.window.ui.nodes["tool.indexer.ctx.last_meta_id.label"])
        last_meta_layout.addWidget(self.window.ui.nodes["tool.indexer.ctx.last_meta_id"])

        last_meta_ts_layout = QHBoxLayout()
        last_meta_ts_layout.addWidget(self.window.ui.nodes["tool.indexer.ctx.last_meta_ts.label"])
        last_meta_ts_layout.addWidget(self.window.ui.nodes["tool.indexer.ctx.last_meta_ts"])

        self.window.ui.nodes["tool.indexer.ctx.btn.idx_all"] = QPushButton(trans('settings.llama.extra.btn.idx_db_all'))
        self.window.ui.nodes["tool.indexer.ctx.btn.idx_all"].clicked.connect(
            lambda: self.window.tools.get("indexer").idx_ctx_db_all()
        )
        self.window.ui.nodes["tool.indexer.ctx.btn.idx_update"] = QPushButton(
            trans('settings.llama.extra.btn.idx_db_update'))
        self.window.ui.nodes["tool.indexer.ctx.btn.idx_update"].clicked.connect(
            lambda: self.window.tools.get("indexer").idx_ctx_db_update()
        )

        idx_btn_layout = QHBoxLayout()
        idx_btn_layout.addWidget(self.window.ui.nodes["tool.indexer.ctx.btn.idx_all"])
        idx_btn_layout.addWidget(self.window.ui.nodes["tool.indexer.ctx.btn.idx_update"])

        self.window.ui.nodes["tool.indexer.ctx.idx.tip"] = QLabel(trans("tool.indexer.tab.ctx.idx.tip"))
        self.window.ui.nodes["tool.indexer.ctx.header.tip"] = HelpLabel(trans("tool.indexer.tab.ctx.tip"))

        # layout
        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.nodes["tool.indexer.ctx.header.tip"])
        layout.addLayout(auto_enabled_layout)
        layout.addLayout(last_auto_layout)
        layout.addLayout(last_meta_layout)
        layout.addLayout(last_meta_ts_layout)
        layout.addWidget(QLabel(""))
        layout.addWidget(self.window.ui.nodes["tool.indexer.ctx.idx.tip"])
        layout.addLayout(idx_btn_layout)
        layout.addStretch(1)

        self.window.tools.get("indexer").update_tab_ctx()

        widget = QWidget()
        widget.setLayout(layout)

        return widget