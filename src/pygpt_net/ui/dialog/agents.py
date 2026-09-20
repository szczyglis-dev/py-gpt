#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczyglinski                  #
# Updated Date: 2026.09.18 09:57:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QButtonGroup,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from pygpt_net.ui.widget.dialog.agents import AgentsV2EditorDialog
from pygpt_net.ui.widget.element.labels import DescLabel
from pygpt_net.ui.widget.lists.agents import AgentEditorList
from pygpt_net.utils import trans


class Agents:
    def __init__(self, window=None):
        self.window = window
        self.dialog_id = "agents.v2.editor"

    def setup(self):
        if self.dialog_id in self.window.ui.dialog:
            return
        nodes = self.window.ui.nodes

        nodes["agents.v2.editor.list"] = AgentEditorList(self.window)
        nodes["agents.v2.editor.list"].setMinimumWidth(230)

        nodes["agents.v2.editor.btn.new"] = QPushButton(QIcon(":/icons/add.svg"), "")
        nodes["agents.v2.editor.btn.defaults"] = QPushButton(QIcon(":/icons/reload.svg"), "")
        nodes["agents.v2.editor.btn.save"] = QPushButton(QIcon(":/icons/save.svg"), "")
        nodes["agents.v2.editor.btn.close"] = QPushButton("")

        nodes["agents.v2.editor.btn.new"].clicked.connect(
            lambda checked=False: self.window.controller.agents_v2.editor.new()
        )
        nodes["agents.v2.editor.btn.defaults"].clicked.connect(
            lambda checked=False: self.window.controller.agents_v2.editor.load_defaults()
        )
        nodes["agents.v2.editor.btn.save"].clicked.connect(
            lambda checked=False: self.window.controller.agents_v2.editor.save()
        )
        nodes["agents.v2.editor.btn.close"].clicked.connect(
            lambda checked=False: self.window.controller.agents_v2.editor.close()
        )
        for key in (
            "agents.v2.editor.btn.new",
            "agents.v2.editor.btn.defaults",
            "agents.v2.editor.btn.close",
        ):
            nodes[key].setAutoDefault(False)
        nodes["agents.v2.editor.btn.save"].setAutoDefault(True)

        nodes["agents.v2.editor.name.label"] = QLabel()
        nodes["agents.v2.editor.name.label"].setStyleSheet("font-weight: bold;")
        nodes["agents.v2.editor.name"] = QLineEdit()
        nodes["agents.v2.editor.info"] = DescLabel("", self.window)

        nodes["agents.v2.editor.prompt.label"] = QLabel()
        nodes["agents.v2.editor.prompt.label"].setStyleSheet("font-weight: bold;")
        nodes["agents.v2.editor.prompt.desc"] = DescLabel("", self.window)
        nodes["agents.v2.editor.prompt"] = QTextEdit()
        nodes["agents.v2.editor.prompt"].setAcceptRichText(False)
        nodes["agents.v2.editor.prompt"].setMinimumHeight(360)

        nodes["agents.v2.editor.runtime.label"] = QLabel()
        nodes["agents.v2.editor.runtime.label"].setStyleSheet("font-weight: bold;")
        nodes["agents.v2.editor.runtime.primary"] = QRadioButton()
        nodes["agents.v2.editor.runtime.orchestrator"] = QRadioButton()
        nodes["agents.v2.editor.runtime.swarm"] = QRadioButton()
        nodes["agents.v2.editor.runtime.group"] = QButtonGroup(self.window.ui.dialog.get(self.dialog_id))
        for key in (
            "agents.v2.editor.runtime.primary",
            "agents.v2.editor.runtime.orchestrator",
            "agents.v2.editor.runtime.swarm",
        ):
            nodes["agents.v2.editor.runtime.group"].addButton(nodes[key])
        nodes["agents.v2.editor.runtime.group"].setExclusive(True)
        nodes["agents.v2.editor.runtime.primary"].toggled.connect(
            lambda checked: self.window.controller.agents_v2.editor.runtime_changed("primary_agent", checked)
        )
        nodes["agents.v2.editor.runtime.orchestrator"].toggled.connect(
            lambda checked: self.window.controller.agents_v2.editor.runtime_changed("orchestrator", checked)
        )
        nodes["agents.v2.editor.runtime.swarm"].toggled.connect(
            lambda checked: self.window.controller.agents_v2.editor.runtime_changed("swarm", checked)
        )

        nodes["agents.v2.editor.help.label"] = QLabel()
        nodes["agents.v2.editor.help.label"].setStyleSheet("font-weight: bold;")
        nodes["agents.v2.editor.help"] = QTextBrowser()
        nodes["agents.v2.editor.help"].setOpenExternalLinks(False)
        nodes["agents.v2.editor.help"].setMinimumHeight(300)
        nodes["agents.v2.editor.help"].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(nodes["agents.v2.editor.list"], 1)
        left_layout.addWidget(nodes["agents.v2.editor.btn.new"])
        left_widget = QWidget()
        left_widget.setLayout(left_layout)

        defaults_row = QHBoxLayout()
        defaults_row.addStretch(1)
        defaults_row.addWidget(nodes["agents.v2.editor.btn.defaults"])

        runtime_row = QHBoxLayout()
        runtime_row.addWidget(nodes["agents.v2.editor.runtime.label"])
        runtime_row.addSpacing(8)
        runtime_row.addWidget(nodes["agents.v2.editor.runtime.primary"])
        runtime_row.addWidget(nodes["agents.v2.editor.runtime.orchestrator"])
        runtime_row.addWidget(nodes["agents.v2.editor.runtime.swarm"])
        runtime_row.addStretch(1)

        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(8, 4, 8, 4)
        right_layout.addWidget(nodes["agents.v2.editor.info"])
        right_layout.addSpacing(6)
        right_layout.addWidget(nodes["agents.v2.editor.name.label"])
        right_layout.addWidget(nodes["agents.v2.editor.name"])
        right_layout.addSpacing(10)
        right_layout.addWidget(nodes["agents.v2.editor.prompt.label"])
        right_layout.addWidget(nodes["agents.v2.editor.prompt.desc"])
        right_layout.addWidget(nodes["agents.v2.editor.prompt"])
        right_layout.addSpacing(6)
        right_layout.addLayout(runtime_row)
        right_layout.addLayout(defaults_row)
        right_layout.addSpacing(12)
        right_layout.addWidget(nodes["agents.v2.editor.help.label"])
        right_layout.addWidget(nodes["agents.v2.editor.help"])

        right_widget = QWidget()
        right_widget.setLayout(right_layout)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(right_widget)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(scroll)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 6)
        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.window.ui.splitters["dialog.agents.v2.editor"] = splitter

        footer = QHBoxLayout()
        footer.addStretch(1)
        footer.addWidget(nodes["agents.v2.editor.btn.save"])
        footer.addWidget(nodes["agents.v2.editor.btn.close"])

        layout = QVBoxLayout()
        layout.addWidget(splitter, 1)
        layout.addLayout(footer)

        dialog = AgentsV2EditorDialog(self.window, self.dialog_id)
        dialog.setLayout(layout)
        self.window.ui.dialog[self.dialog_id] = dialog
        self.retranslate(reload=False)

    def _help_text(self) -> str:
        return trans("agents.editor.help").replace("\\n", "\n")

    def retranslate(self, reload: bool = True):
        if self.dialog_id not in self.window.ui.dialog:
            return
        nodes = self.window.ui.nodes
        self.window.ui.dialog[self.dialog_id].setWindowTitle(trans("agents.editor.title"))
        nodes["agents.v2.editor.btn.new"].setText(trans("dialog.models.editor.btn.new"))
        nodes["agents.v2.editor.btn.defaults"].setText(trans("settings.agent.v2.prompt.from_defaults"))
        nodes["agents.v2.editor.btn.save"].setText(trans("dialog.models.editor.btn.save"))
        nodes["agents.v2.editor.btn.close"].setText(trans("action.close"))
        nodes["agents.v2.editor.name.label"].setText(trans("agents.editor.name"))
        nodes["agents.v2.editor.prompt.label"].setText(trans("agents.editor.system_prompt"))
        nodes["agents.v2.editor.runtime.label"].setText(trans("agents.editor.runtime"))
        nodes["agents.v2.editor.runtime.primary"].setText(trans("agents.editor.runtime.primary"))
        nodes["agents.v2.editor.runtime.orchestrator"].setText(trans("agents.editor.runtime.orchestrator"))
        nodes["agents.v2.editor.runtime.swarm"].setText(trans("agents.editor.runtime.swarm"))
        nodes["agents.v2.editor.help.label"].setText(trans("agents.editor.help.title"))
        nodes["agents.v2.editor.help"].setPlainText(self._help_text())
        if reload:
            self.window.controller.agents_v2.editor.reload()
