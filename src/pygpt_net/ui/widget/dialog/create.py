#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.27 19:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QDialog, QLabel, QHBoxLayout, QVBoxLayout, QPushButton, QCheckBox

from pygpt_net.utils import trans
from pygpt_net.ui.widget.option.input import DirectoryInput
from pygpt_net.ui.widget.textarea.create import CreateInput


class CreateDialog(QDialog):
    def __init__(self, window=None, id=None):
        """
        Create dialog

        :param window: main window
        :param id: info window id
        """
        super(CreateDialog, self).__init__(window)
        self.window = window
        self.id = id
        self.current = None
        self.input = CreateInput(window, id)
        self.input.setMinimumWidth(400)

        # Project-only workdir controls. They stay hidden for every other use of
        # this shared create/rename dialog.
        self.project_mode = False
        self.project_workdir_enabled = False
        self.project_use_shared = QCheckBox(trans("dialog.project.use_shared_workdir"))
        self.project_use_shared.setChecked(True)
        self.project_workdir_label = QLabel(trans("dialog.project.workdir"))
        self.project_workdir = DirectoryInput(
            self.window,
            "project",
            "workdir",
            {"label": trans("dialog.project.workdir"), "value": ""},
        )
        self.project_use_shared.toggled.connect(self._toggle_project_workdir)
        self.project_use_shared.setVisible(False)
        self.project_workdir_label.setVisible(False)
        self.project_workdir.setVisible(False)

        self.window.ui.nodes['dialog.create.btn.update'] = QPushButton(trans('dialog.create.update'))
        self.window.ui.nodes['dialog.create.btn.update'].clicked.connect(
            lambda: self.window.controller.dialogs.confirm.accept_create(
                self.id,
                self.window.ui.dialog['create'].current,
                self.input.text()),
        )

        self.window.ui.nodes['dialog.create.btn.dismiss'] = QPushButton(trans('dialog.create.dismiss'))
        self.window.ui.nodes['dialog.create.btn.dismiss'].clicked.connect(
            lambda: self.window.controller.dialogs.confirm.dismiss_create())

        bottom = QHBoxLayout()
        bottom.addWidget(self.window.ui.nodes['dialog.create.btn.dismiss'])
        bottom.addWidget(self.window.ui.nodes['dialog.create.btn.update'])

        self.window.ui.nodes['dialog.create.label'] = QLabel(trans("dialog.create.title"))

        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.nodes['dialog.create.label'])
        layout.addWidget(self.input)
        layout.addWidget(self.project_use_shared)
        layout.addWidget(self.project_workdir_label)
        layout.addWidget(self.project_workdir)
        layout.addLayout(bottom)

        self.setLayout(layout)

    def _toggle_project_workdir(self, use_shared: bool):
        self.project_workdir.setEnabled(not use_shared)

    def set_project_mode(
            self,
            enabled: bool,
            use_shared: bool = True,
            workdir: str = "",
            edit: bool = False,
            allow_workdir: bool = True,
    ):
        """Configure the shared dialog for project create/edit."""
        self.project_mode = bool(enabled)
        self.project_workdir_enabled = bool(enabled and allow_workdir)
        self.project_use_shared.setText(trans("dialog.project.use_shared_workdir"))
        self.project_workdir_label.setText(trans("dialog.project.workdir"))
        self.project_use_shared.setVisible(self.project_workdir_enabled)
        self.project_workdir_label.setVisible(self.project_workdir_enabled)
        self.project_workdir.setVisible(self.project_workdir_enabled)

        if not enabled:
            self.setWindowTitle(trans("dialog.create.title"))
            self.window.ui.nodes['dialog.create.label'].setText(trans("dialog.create.title"))
            return

        self.project_use_shared.setChecked(bool(use_shared))
        if not workdir:
            workdir = self.window.core.filesystem.get_shared_data_dir()
        self.project_workdir.value = workdir
        self.project_workdir.setText(workdir)
        self._toggle_project_workdir(bool(use_shared))

        if edit:
            title = trans("dialog.project.edit.title")
        else:
            title = trans("dialog.project.create.title")
        self.setWindowTitle(title)
        self.window.ui.nodes['dialog.create.label'].setText(trans("dialog.project.name"))

    def showEvent(self, event):
        if self.id != "ctx.group":
            self.set_project_mode(False)
        super().showEvent(event)

    def get_project_workdir_settings(self):
        if not self.project_workdir_enabled:
            return None, None
        return self.project_use_shared.isChecked(), self.project_workdir.text().strip()
