#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.21 15:45:00                  #
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
    MIN_WIDTH = 200

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

    def setup(self) -> QWidget:
        """
        Setup toolbox.

        The mode/model area and System prompt remain inside the vertical
        splitter.  Mode-specific controls and the global footer live outside
        that splitter, at the bottom of the toolbox, so moving the splitter
        cannot compress or hide them.

        :return: Toolbox widget
        :rtype: QWidget
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

        # The lower splitter pane now contains only the System prompt.  Keep the
        # node for compatibility with code/plugins which may reference it.
        bottom_widget = QWidget(self.window)
        bottom_widget.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        bottom_widget.setMinimumWidth(0)
        bottom = QVBoxLayout(bottom_widget)
        bottom.addWidget(prompt_widget, 1)
        bottom.setContentsMargins(0, 0, 0, 0)
        nodes['toolbox.bottom'] = bottom_widget

        # Only the upper toolbox content and System prompt are resizable.  The
        # footer is deliberately not a splitter child: it always stays at its
        # natural height at the bottom and therefore cannot be hidden by moving
        # the vertical splitter handle.
        splitter = QSplitter(Qt.Vertical, self.window)
        splitter.setProperty('class', 'toolbox')
        splitter.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        splitter.setMinimumWidth(0)
        splitter.addWidget(toolbox_mode)
        splitter.addWidget(bottom_widget)

        # Keep the System prompt pane at the user-selected height across window
        # resizes. The upper toolbox area absorbs the remaining height.
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)

        toolbox = QWidget(self.window)
        toolbox.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        toolbox.setMinimumWidth(self.MIN_WIDTH)
        toolbox_layout = QVBoxLayout(toolbox)
        toolbox_layout.addWidget(splitter, 1)
        toolbox_layout.addWidget(footer_widget, 0)
        toolbox_layout.setContentsMargins(0, 0, 0, 0)
        toolbox_layout.setSpacing(0)
        nodes['toolbox'] = toolbox

        hover = ToolboxSectionHover(toolbox)
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
        toolbox._toolbox_section_hover = hover

        # Preserve the existing splitter key and saved geometry format.  The
        # stored two sizes now control mode/model vs System prompt only; footer
        # height is derived from its visible contents and is not user-resizable.
        ui.splitters['toolbox'] = splitter
        return toolbox
