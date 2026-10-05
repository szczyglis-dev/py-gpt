#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.30 13:58:00                  #
# ================================================== #

import html
import re

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from pygpt_net.ui.widget.dialog.quick_start import QuickStartDialog
from pygpt_net.utils import trans


class QuickStart:
    """First-run onboarding shown immediately after accepting the license."""

    PLUGINS_STEP_1 = (
        ("filesystem", "dialog.quick_start.filesystem.desc"),
        ("canvas_web", "dialog.quick_start.canvas.desc"),
        ("mcp", "dialog.quick_start.mcp.desc"),
        ("openai_dalle", "dialog.quick_start.image.desc"),
    )
    DEFAULT_ENABLED_PLUGINS = {
        "filesystem",
    }

    def __init__(self, window=None):
        self.window = window
        self.stack = None
        self.btn_back = None
        self.btn_next = None
        self.btn_finish = None
        self.checkboxes = {}
        self.plugin_labels = {}
        self.plugin_desc_labels = {}
        self.radio_api_yes = None
        self.radio_api_no = None
        self.api_group = None
        self.radio_api_no_desc = None
        self.language_combo = None
        self.language_label = None
        self.title_label = None
        self.intro_label = None
        self.primary_question = None
        self.extra_question = None
        self.plugins_more_label = None
        self.plugins_tools_hint_labels = []
        self.api_question = None
        self.theme_hint_label = None
        self.dialog = None

    def setup(self):
        """Build the quick-start wizard in the currently selected language."""
        if "quick_start" in self.window.ui.dialog:
            return
        self.checkboxes = {}
        self.plugin_labels = {}
        self.plugin_desc_labels = {}

        # Quick Start always opens in English. The user can switch the
        # language immediately on the first page and the whole UI is updated
        # live. English remains only the default selection, not a pinned item.
        if str(self.window.core.config.get("lang") or "en") != "en":
            self.window.controller.lang.toggle("en")

        dialog = QuickStartDialog(self.window, "quick_start")
        self.dialog = dialog
        dialog.setWindowTitle(trans("dialog.quick_start.title"))
        dialog.setMinimumSize(620, 470)

        self.stack = QStackedWidget(dialog)
        self.stack.addWidget(self._build_intro_page())
        self.stack.addWidget(self._build_plugins_page(
            "dialog.quick_start.plugins.primary.question",
            self.PLUGINS_STEP_1,
            show_tools_hint=True,
        ))
        self.stack.addWidget(self._build_api_page())
        self.stack.currentChanged.connect(self._update_navigation)

        self.btn_back = QPushButton(trans("dialog.quick_start.back"), dialog)
        self.btn_back.clicked.connect(self.back)
        self.btn_next = QPushButton(trans("dialog.quick_start.next"), dialog)
        self.btn_next.clicked.connect(self.next)
        self.btn_finish = QPushButton(trans("dialog.quick_start.finish"), dialog)
        self.btn_finish.clicked.connect(self.finish)

        nav = QHBoxLayout()
        nav.setContentsMargins(0, 8, 0, 0)
        nav.addStretch(1)
        nav.addWidget(self.btn_back)
        nav.addWidget(self.btn_next)
        nav.addWidget(self.btn_finish)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(14)
        layout.addWidget(self.stack, 1)
        layout.addLayout(nav)
        dialog.setLayout(layout)

        self.window.ui.dialog["quick_start"] = dialog
        self._update_navigation(0)

    def _build_intro_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(18)

        self.title_label = QLabel(trans("dialog.quick_start.title"), page)
        title_font = self.title_label.font()
        title_font.setBold(True)
        title_font.setPointSize(title_font.pointSize() + 4)
        self.title_label.setFont(title_font)

        self.intro_label = QLabel(trans("dialog.quick_start.intro"), page)
        self.intro_label.setWordWrap(True)
        self.intro_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.language_label = QLabel(trans("dialog.quick_start.language.select"), page)
        language_font = self.language_label.font()
        language_font.setBold(True)
        self.language_label.setFont(language_font)

        self.language_combo = QComboBox(page)
        self.language_combo.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.language_combo.setFixedWidth(300)
        available = set(self.window.core.config.get_available_langs())
        mapping = getattr(self.window.controller.lang, "LANG_MAPPING", {})
        items = []
        for code in available:
            name = str(mapping.get(code, code.upper()))
            if code == "en":
                name = re.sub(r"\s*\(default\)\s*$", "", name, flags=re.IGNORECASE)
            label = f"{code.upper()} - {name}"
            items.append((code.casefold(), label, code))
        for _, label, code in sorted(items):
            self.language_combo.addItem(label, code)

        # Keep EN in its natural alphabetical position, but select it by
        # default on the first page.
        idx = self.language_combo.findData("en")
        if idx >= 0:
            self.language_combo.setCurrentIndex(idx)
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)

        layout.addWidget(self.title_label)
        layout.addSpacing(8)
        layout.addWidget(self.intro_label)
        layout.addSpacing(6)
        layout.addWidget(self.language_label)
        layout.addWidget(self.language_combo)
        layout.addStretch(1)
        return page

    def _build_plugins_page(
        self,
        question_key: str,
        plugins,
        footer_key: str = None,
        show_tools_hint: bool = False,
    ) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(14)

        question = QLabel(trans(question_key), page)
        question.setWordWrap(True)
        question_font = question.font()
        question_font.setBold(True)
        question_font.setPointSize(question_font.pointSize() + 1)
        question.setFont(question_font)
        if question_key == "dialog.quick_start.plugins.primary.question":
            self.primary_question = question
        elif question_key == "dialog.quick_start.plugins.extra.question":
            self.extra_question = question
        layout.addWidget(question)
        layout.addSpacing(2)

        for plugin_id, desc_key in plugins:
            row, checkbox = self._plugin_row(plugin_id, desc_key, page)
            self.checkboxes[plugin_id] = checkbox
            layout.addWidget(row)

        if footer_key:
            layout.addSpacing(4)
            note = QLabel(trans(footer_key), page)
            note.setWordWrap(True)
            note_font = note.font()
            note_font.setItalic(True)
            note.setFont(note_font)
            if footer_key == "dialog.quick_start.plugins.more":
                self.plugins_more_label = note
            layout.addWidget(note)

        layout.addStretch(1)

        if show_tools_hint:
            hint = QLabel(trans("dialog.quick_start.plugins.tools_hint"), page)
            hint.setWordWrap(True)
            hint_font = hint.font()
            hint_font.setItalic(True)
            hint.setFont(hint_font)
            self.plugins_tools_hint_labels.append(hint)
            layout.addWidget(hint)
        return page

    def _plugin_row(self, plugin_id: str, desc_key: str, parent: QWidget):
        row = QWidget(parent)
        row.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(4, 4, 4, 4)
        row_layout.setSpacing(10)
        row_layout.setAlignment(Qt.AlignTop)

        checkbox = QCheckBox(row)
        checkbox.setChecked(plugin_id in self.DEFAULT_ENABLED_PLUGINS)
        checkbox.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        text_widget = QWidget(row)
        text_layout = QVBoxLayout(text_widget)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        name = QLabel(self._plugin_name(plugin_id), text_widget)
        name_font = name.font()
        name_font.setBold(True)
        name.setFont(name_font)

        desc = QLabel(trans(desc_key), text_widget)
        desc.setWordWrap(True)
        desc.setTextInteractionFlags(Qt.TextSelectableByMouse)

        text_layout.addWidget(name)
        text_layout.addWidget(desc)
        self.plugin_labels[plugin_id] = name
        self.plugin_desc_labels[plugin_id] = (desc, desc_key)
        row_layout.addWidget(checkbox, 0, Qt.AlignTop)
        row_layout.addWidget(text_widget, 1)
        return row, checkbox

    def _plugin_name(self, plugin_id: str) -> str:
        """Use the plugin's translated name, without the technical '(inline)' suffix."""
        try:
            name = self.window.core.plugins.get_name(plugin_id)
        except Exception:
            name = plugin_id
        return re.sub(r"\s*[\(（][^\)）]+[\)）]\s*$", "", str(name)).strip()

    def _theme_hint_text(self) -> str:
        menu_path = f"<b>{html.escape(trans('menu.config'))} -&gt; {html.escape(trans('menu.theme'))}</b>"
        try:
            return trans("dialog.quick_start.theme_hint").format(menu=menu_path)
        except (KeyError, ValueError):
            return trans("dialog.quick_start.theme_hint")

    def _build_api_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(14)

        question = QLabel(trans("dialog.quick_start.api.question"), page)
        question.setWordWrap(True)
        question_font = question.font()
        question_font.setBold(True)
        question_font.setPointSize(question_font.pointSize() + 1)
        question.setFont(question_font)
        self.api_question = question
        layout.addWidget(question)
        layout.addSpacing(8)

        self.radio_api_yes = QRadioButton(trans("dialog.quick_start.yes").upper(), page)
        yes_font = self.radio_api_yes.font()
        yes_font.setBold(True)
        self.radio_api_yes.setFont(yes_font)

        no_row = QWidget(page)
        no_layout = QHBoxLayout(no_row)
        no_layout.setContentsMargins(0, 0, 0, 0)
        no_layout.setSpacing(6)

        self.radio_api_no = QRadioButton(trans("dialog.quick_start.no").upper(), no_row)
        no_font = self.radio_api_no.font()
        no_font.setBold(True)
        self.radio_api_no.setFont(no_font)
        self.radio_api_no_desc = QLabel(trans("dialog.quick_start.no.local_models"), no_row)
        self.radio_api_no_desc.setWordWrap(True)
        no_layout.addWidget(self.radio_api_no, 0, Qt.AlignTop)
        no_layout.addWidget(self.radio_api_no_desc, 1)

        self.api_group = QButtonGroup(page)
        self.api_group.setExclusive(True)
        self.api_group.addButton(self.radio_api_yes)
        self.api_group.addButton(self.radio_api_no)
        self.radio_api_yes.setChecked(True)
        layout.addWidget(self.radio_api_yes)
        layout.addWidget(no_row)
        layout.addStretch(1)

        self.theme_hint_label = QLabel(self._theme_hint_text(), page)
        self.theme_hint_label.setWordWrap(True)
        self.theme_hint_label.setTextFormat(Qt.RichText)
        theme_hint_font = self.theme_hint_label.font()
        theme_hint_font.setItalic(True)
        self.theme_hint_label.setFont(theme_hint_font)
        layout.addWidget(self.theme_hint_label)
        return page

    def _on_language_changed(self, index: int):
        """Apply the selected language immediately and refresh this wizard."""
        if self.language_combo is None or index < 0:
            return
        lang = self.language_combo.itemData(index)
        if not lang:
            return
        if str(self.window.core.config.get("lang") or "") != str(lang):
            self.window.controller.lang.toggle(str(lang))
        self._refresh_texts()

    def _refresh_texts(self):
        """Refresh wizard text after a runtime language switch."""
        if self.dialog is not None:
            self.dialog.setWindowTitle(trans("dialog.quick_start.title"))
        if self.title_label is not None:
            self.title_label.setText(trans("dialog.quick_start.title"))
        if self.intro_label is not None:
            self.intro_label.setText(trans("dialog.quick_start.intro"))
        if self.language_label is not None:
            self.language_label.setText(trans("dialog.quick_start.language.select"))
        if self.primary_question is not None:
            self.primary_question.setText(trans("dialog.quick_start.plugins.primary.question"))
        if self.extra_question is not None:
            self.extra_question.setText(trans("dialog.quick_start.plugins.extra.question"))
        if self.plugins_more_label is not None:
            self.plugins_more_label.setText(trans("dialog.quick_start.plugins.more"))
        for label in self.plugins_tools_hint_labels:
            label.setText(trans("dialog.quick_start.plugins.tools_hint"))
        if self.api_question is not None:
            self.api_question.setText(trans("dialog.quick_start.api.question"))
        if self.theme_hint_label is not None:
            self.theme_hint_label.setText(self._theme_hint_text())

        for plugin_id, label in self.plugin_labels.items():
            label.setText(self._plugin_name(plugin_id))
        for desc, key in self.plugin_desc_labels.values():
            desc.setText(trans(key))

        if self.radio_api_yes is not None:
            self.radio_api_yes.setText(trans("dialog.quick_start.yes").upper())
        if self.radio_api_no is not None:
            self.radio_api_no.setText(trans("dialog.quick_start.no").upper())
        if self.radio_api_no_desc is not None:
            self.radio_api_no_desc.setText(trans("dialog.quick_start.no.local_models"))
        if self.btn_back is not None:
            self.btn_back.setText(trans("dialog.quick_start.back"))
        if self.btn_next is not None:
            self.btn_next.setText(trans("dialog.quick_start.next"))
        if self.btn_finish is not None:
            self.btn_finish.setText(trans("dialog.quick_start.finish"))

    def open(self):
        """Open only for a pending, unfinished first-run onboarding."""
        cfg = self.window.core.config
        if cfg.get("quick_start.finished", False):
            return
        if not cfg.get("quick_start.pending", False):
            return

        dialog = self.window.ui.dialog.get("quick_start")
        if dialog is None:
            self.setup()
            dialog = self.window.ui.dialog.get("quick_start")
        if dialog is None:
            return
        dialog.completed = False
        self.stack.setCurrentIndex(0)
        self._update_navigation(0)
        dialog.resize(660, 500)
        qr = dialog.frameGeometry()
        screen = self.window.screen()
        if screen is not None:
            qr.moveCenter(screen.availableGeometry().center())
            dialog.move(qr.topLeft())
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        dialog.setFocus()

    def next(self):
        if self.stack.currentIndex() < self.stack.count() - 1:
            self.stack.setCurrentIndex(self.stack.currentIndex() + 1)

    def back(self):
        if self.stack.currentIndex() > 0:
            self.stack.setCurrentIndex(self.stack.currentIndex() - 1)

    def _update_navigation(self, index: int):
        if self.btn_back is None:
            return
        last = self.stack.count() - 1
        self.btn_back.setVisible(index > 0)
        self.btn_next.setVisible(index < last)
        self.btn_finish.setVisible(index == last)
        if index < last:
            self.btn_next.setDefault(True)
            self.btn_next.setFocus()
        else:
            self.btn_finish.setDefault(True)
            self.btn_finish.setFocus()

    def finish(self):
        """Persist selected plugins, close the wizard and optionally open API Keys."""
        plugins = self.window.controller.plugins
        for plugin_id, checkbox in self.checkboxes.items():
            if checkbox.isChecked():
                plugins.enable(plugin_id)
            else:
                plugins.disable(plugin_id)

        # Keep dependent UI and the optional active plugin preset consistent
        # with the newly selected first-run defaults.
        self.window.controller.ui.update_tokens()
        self.window.controller.attachment.update()
        plugins.presets.save_current()

        cfg = self.window.core.config
        cfg.set("quick_start.finished", True)
        cfg.set("quick_start.pending", False)
        cfg.save()

        open_api_keys = bool(self.radio_api_yes and self.radio_api_yes.isChecked())
        dialog = self.window.ui.dialog.get("quick_start")
        if dialog is not None:
            dialog.completed = True
            dialog.close()

        if open_api_keys:
            QTimer.singleShot(0, self._open_api_keys)

    def _open_api_keys(self):
        self.window.controller.settings.open_section("api_keys")
        option_id = self.window.core.llm.get_settings_option_id("openai", "api_key")
        option = self.window.ui.config.get("config", {}).get(option_id)
        if option is not None:
            option.setFocus()
