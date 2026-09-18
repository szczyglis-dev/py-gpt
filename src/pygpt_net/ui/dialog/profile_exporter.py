#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.18 13:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.utils import trans


class _SectionRow(QWidget):
    def __init__(self, label: str, checked: bool = True, parent=None):
        super().__init__(parent)
        self.checkbox = QCheckBox(label, self)
        self.checkbox.setChecked(checked)
        self.size = HelpLabel("(…)", self)
        self.size.setWordWrap(False)
        self.size.setContentsMargins(0, 0, 0, 0)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        layout.addWidget(self.checkbox)
        layout.addWidget(self.size)
        layout.addStretch(1)
        self.setLayout(layout)

    def set_size(self, value: str):
        self.size.setText(f"({value})")


class ExportProfileDialog(QDialog):
    """Select the active-profile sections to export."""

    def __init__(self, window, controller):
        super().__init__(window)
        self.window = window
        self.controller = controller
        self.setWindowTitle(trans("profile.export.dialog.title"))
        self.setMinimumWidth(560)

        description = QLabel(trans("profile.export.dialog.description"), self)
        description.setWordWrap(True)
        description.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.rows = {
            "db": _SectionRow(trans("profile.export.section.db"), True, self),
            "config": _SectionRow(trans("profile.export.section.config"), True, self),
            "files": _SectionRow(trans("profile.export.section.files"), True, self),
            "data": _SectionRow(trans("profile.export.section.data"), False, self),
        }

        self.cancel_btn = QPushButton(trans("input.btn.cancel"), self)
        self.cancel_btn.clicked.connect(self.reject)
        self.export_btn = QPushButton(trans("profile.export.btn"), self)
        self.export_btn.clicked.connect(self.controller.export_selected)
        self.export_btn.setEnabled(False)

        footer = QHBoxLayout()
        footer.addStretch(1)
        footer.addWidget(self.cancel_btn)
        footer.addWidget(self.export_btn)

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 14)
        layout.setSpacing(10)
        layout.addWidget(description)
        for section in ("db", "config", "files", "data"):
            layout.addWidget(self.rows[section])
        layout.addSpacing(6)
        layout.addLayout(footer)
        self.setLayout(layout)

    def set_sizes(self, sizes, formatter):
        for section, row in self.rows.items():
            row.set_size(formatter(sizes.get(section, 0)))
        self.export_btn.setEnabled(True)

    def selected_sections(self):
        return [
            section for section, row in self.rows.items()
            if row.checkbox.isChecked()
        ]


class ImportProfileDialog(QDialog):
    """Select sections and the new profile name for import."""

    def __init__(self, window, controller, filename: str, exported, default_name: str):
        super().__init__(window)
        self.window = window
        self.controller = controller
        self.setWindowTitle(trans("profile.import.dialog.title"))
        self.setMinimumWidth(560)

        description = QLabel(
            trans("profile.import.dialog.description").format(filename=filename),
            self,
        )
        description.setWordWrap(True)
        description.setTextInteractionFlags(Qt.TextSelectableByMouse)

        exported = set(exported)
        self.checkboxes = {}
        labels = {
            "db": trans("profile.export.section.db"),
            "config": trans("profile.export.section.config"),
            "files": trans("profile.export.section.files"),
            "data": trans("profile.export.section.data"),
        }
        for section in ("db", "config", "files", "data"):
            checkbox = QCheckBox(labels[section], self)
            checkbox.setEnabled(section in exported)
            checkbox.setChecked(section in exported)
            self.checkboxes[section] = checkbox

        name_label = QLabel(trans("profile.import.name.label"), self)
        self.name_input = QLineEdit(default_name, self)
        self.name_input.setMinimumWidth(400)

        self.cancel_btn = QPushButton(trans("input.btn.cancel"), self)
        self.cancel_btn.clicked.connect(self.reject)
        self.import_btn = QPushButton(trans("profile.import.btn"), self)
        self.import_btn.clicked.connect(self.controller.import_selected)
        self.import_btn.setDefault(True)

        footer = QHBoxLayout()
        footer.addStretch(1)
        footer.addWidget(self.cancel_btn)
        footer.addWidget(self.import_btn)

        help_label = HelpLabel(trans("profile.import.workdir.help"), self)

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 14)
        layout.setSpacing(10)
        layout.addWidget(description)
        for section in ("db", "config", "files", "data"):
            layout.addWidget(self.checkboxes[section])
        layout.addSpacing(6)
        layout.addWidget(name_label)
        layout.addWidget(self.name_input)
        layout.addSpacing(6)
        layout.addLayout(footer)
        layout.addWidget(help_label)
        self.setLayout(layout)

    def selected_sections(self):
        return [
            section for section, checkbox in self.checkboxes.items()
            if checkbox.isEnabled() and checkbox.isChecked()
        ]
