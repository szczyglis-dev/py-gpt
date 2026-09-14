#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.14 13:55:00                  #
# ================================================== #

from PySide6.QtCore import QEvent, QObject
from PySide6.QtGui import Qt, QCursor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QLineEdit,
    QListView,
    QPushButton,
    QRadioButton,
    QSplitter,
    QTextEdit,
    QToolButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
    QLabel,
    QSizePolicy,
)

from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.utils import trans

from .assistants import Assistants
from .banner import Banner
from .indexes import Indexes
from .mode import Mode
from .model import Model
from .presets import Presets
from .prompt import Prompt
from .footer import Footer


class ToolboxSectionHover(QObject):
    """Keep an independent hover state for each logical toolbox section."""

    _STYLE_WIDGETS = (
        QLabel,
        QPushButton,
        QToolButton,
        QCheckBox,
        QRadioButton,
        QComboBox,
        QLineEdit,
        QTextEdit,
        QListView,
        QTreeView,
    )

    def register(self, section: QWidget) -> QWidget:
        """Register a complete section and all of its current descendants."""
        section.setProperty('toolboxSection', True)
        self._install_filters(section)
        self._set_hover(section, False, force=True)
        return section

    def _install_filters(self, section: QWidget):
        section.installEventFilter(self)
        for widget in section.findChildren(QWidget):
            widget.installEventFilter(self)

    @staticmethod
    def _section_for(widget) -> QWidget | None:
        """Resolve the registered section owning ``widget``."""
        current = widget if isinstance(widget, QWidget) else None
        while current is not None:
            if bool(current.property('toolboxSection')):
                return current
            current = current.parentWidget()
        return None

    def _set_hover(self, section: QWidget, hovered: bool, force: bool = False):
        """Apply one section hover state to every text-rendering child."""
        hovered = bool(hovered)
        if not force and bool(section.property('toolboxHover')) == hovered:
            return

        section.setProperty('toolboxHover', hovered)
        widgets = [section, *section.findChildren(QWidget)]
        for widget in widgets:
            if widget is not section and not isinstance(widget, self._STYLE_WIDGETS):
                continue
            try:
                widget.setProperty('toolboxHover', hovered)
                style = widget.style()
                style.unpolish(widget)
                style.polish(widget)
                # Do not call widget.update() polymorphically here.
                # QAbstractItemView subclasses (e.g. ComboPopupListView) expose
                # update(QModelIndex), which shadows QWidget.update() in PySide.
                # Calling it without an index crashes during toolbox setup.
                QWidget.update(widget)
                if isinstance(widget, QAbstractItemView):
                    widget.viewport().update()
            except RuntimeError:
                # Ignore a widget that was destroyed during a layout/mode switch.
                continue

    def eventFilter(self, watched, event):
        section = self._section_for(watched)
        if section is None:
            return super().eventFilter(watched, event)

        event_type = event.type()
        if event_type == QEvent.Enter:
            self._set_hover(section, True)
        elif event_type == QEvent.Leave:
            # QCursor already points at the new widget when Leave is delivered.
            # Therefore moving between children of the same section keeps the
            # section active, while crossing into another section clears it.
            try:
                pos = section.mapFromGlobal(QCursor.pos())
                self._set_hover(section, section.rect().contains(pos))
            except RuntimeError:
                pass
        return super().eventFilter(watched, event)


class ToolboxMain:
    MIN_WIDTH = 256

    def __init__(self, window=None):
        """
        Toolbox UI

        :param window: Window instance
        """
        self.window = window
        self.assistants = Assistants(window)
        self.banner = Banner(window)
        self.indexes = Indexes(window)
        self.footer = Footer(window)
        self.mode = Mode(window)
        self.model = Model(window)
        self.presets = Presets(window)
        self.prompt = Prompt(window)

    def setup(self) -> QSplitter:
        """
        Setup toolbox

        :return: QSplitter
        :rtype: QSplitter
        """
        ui = self.window.ui
        nodes = ui.nodes

        # mode / model
        tip = HelpLabel(trans('tip.toolbox.mode'), self.window)
        tip.setAlignment(Qt.AlignCenter)
        nodes['tip.toolbox.mode'] = tip

        # Build logical sections separately. Hover is handled independently for
        # every section (Mode, Model, Presets/Agents, Assistants, System prompt,
        # Footer), rather than for the complete toolbox.
        mode_widget = self.mode.setup()
        model_widget = self.model.setup()
        presets_widget = self.presets.setup()
        assistants_widget = self.assistants.setup()
        prompt_widget = self.prompt.setup()
        footer_widget = self.footer.setup()

        # presets / assistants
        toolbox_mode = QWidget(self.window)
        layout = QVBoxLayout(toolbox_mode)
        self.banner.setup(layout)  # banner is inserted only after a successful remote load
        layout.addWidget(mode_widget)  # modes
        layout.addWidget(model_widget)  # models
        layout.addWidget(tip)
        layout.addWidget(presets_widget, 1)  # presets / agents
        layout.addWidget(assistants_widget, 1)  # assistants
        layout.setContentsMargins(0, 0, 0, 0)

        # The toolbox must remain horizontally shrinkable. Some mode-specific
        # controls have wide size hints (or are only visible in selected modes),
        # so using the default horizontal policy here would let those hints raise
        # the effective minimum width of the whole right pane.
        toolbox_mode.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        toolbox_mode.setMinimumWidth(0)
        nodes['toolbox.mode'] = toolbox_mode
        nodes['toolbox.mode.layout'] = layout

        bottom_widget = QWidget(self.window)
        bottom_widget.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        bottom_widget.setMinimumWidth(0)
        bottom = QVBoxLayout(bottom_widget)
        bottom.addWidget(prompt_widget)
        bottom.addWidget(footer_widget)
        bottom.setContentsMargins(0, 0, 0, 0)

        # rows
        splitter = QSplitter(Qt.Vertical, self.window)
        splitter.setProperty('class', 'toolbox')
        # Keep one stable minimum width regardless of which mode-specific
        # widgets are currently visible. QSizePolicy.Ignored makes the parent
        # splitter ignore changing child size hints while the explicit minimum
        # below still prevents collapsing the toolbox too far.
        splitter.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        splitter.setMinimumWidth(self.MIN_WIDTH)
        splitter.addWidget(toolbox_mode)  # mode/model
        splitter.addWidget(bottom_widget)  # system prompt, footer (names, temp, logo, etc.)

        hover = ToolboxSectionHover(splitter)
        hover.register(mode_widget)
        hover.register(model_widget)
        hover.register(presets_widget)
        hover.register(assistants_widget)
        # Prompt/footer containers are layout-only. Register their logical
        # sections independently so hover cannot leak between System prompt and
        # Agents mode or between per-mode options and Split screen.
        for section in self.prompt.hover_sections:
            hover.register(section)
        for section in self.footer.hover_sections:
            hover.register(section)
        # Keep an explicit Python reference in addition to QObject parenting.
        splitter._toolbox_section_hover = hover

        ui.splitters['toolbox'] = splitter
        return splitter
