#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.22 18:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt, Slot, QUrl, QObject, Signal, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QVBoxLayout,
    QCheckBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QWidget,
    QSizePolicy,
)

from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.ui.widget.textarea.editor import BaseCodeEditor
from pygpt_net.ui.widget.textarea.html import HtmlOutput
from pygpt_net.utils import trans


class ToolWidget:
    def __init__(self, window=None, tool=None):
        """
        HTML/JS canvas widget

        :param window: Window instance
        :param tool: Tool instance
        """
        self.window = window
        self.tool = tool  # tool instance
        self.output = None  # canvas output
        self.edit = None  # canvas edit
        self.btn_edit = None  # edit checkbox

        # --- Navigation bar state ---
        # This toolbar is shown only when opening via URL (open_url),
        # and hidden when using set_output/load_output.
        self.nav_bar = None
        self.nav_layout = None
        self.address_bar = None
        self.btn_back = None
        self.btn_next = None
        self.btn_reload = None
        self.btn_go = None

    def on_open(self):
        """On open"""
        pass

    def on_delete(self):
        """On delete"""
        if self.tool:
            self.tool.signals.update.disconnect(self.set_output)
            self.tool.signals.reload.disconnect(self.load_output)
            self.tool.signals.url.disconnect(self.open_url)  # keep connections clean
        if self.output:
            self.output.on_delete()

    def set_tab(self, tab):
        """
        Set tab

        :param tab: Tab
        """
        self.output.set_tab(tab)
        self.edit.set_tab(tab)

    def setup(self, all: bool = True) -> QVBoxLayout:
        """
        Setup widget body

        :param all: If True, setup all widgets
        :return: QVBoxLayout
        """
        self.output = CanvasOutput(self.window)
        self.edit = CanvasEdit(self.window)
        self.edit.setVisible(False)
        self.edit.textChanged.connect(
            lambda: self.tool.save_output()
        )

        # ---- Navigation bar ----
        # Visible only when navigating URLs via open_url or address bar.
        self.nav_bar = QWidget()
        self.nav_layout = QHBoxLayout(self.nav_bar)
        self.nav_layout.setContentsMargins(6, 4, 6, 4)  # small margins for compact look
        self.nav_layout.setSpacing(6)
        self.nav_bar.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        # Icon size and fixed navbar height (to prevent taking too much space)
        icon_size_px = 20  # base icon size for QPushButtons
        nav_height = max(32, min(44, icon_size_px + 16))  # compact, never half-screen
        self.nav_bar.setFixedHeight(nav_height)

        # Buttons
        self.btn_back = QPushButton()
        self.btn_back.setToolTip("Back")
        self.btn_back.setIcon(QIcon(":/icons/back.svg"))
        self.btn_back.setIconSize(QSize(icon_size_px, icon_size_px))
        self.btn_back.setFixedHeight(nav_height - 8)
        self.btn_back.setEnabled(False)
        self.btn_back.setAutoDefault(False)  # prevent Enter from triggering this
        try:
            self.btn_back.setDefault(False)
        except Exception:
            pass

        self.btn_next = QPushButton()
        self.btn_next.setToolTip("Next")
        self.btn_next.setIcon(QIcon(":/icons/forward.svg"))
        self.btn_next.setIconSize(QSize(icon_size_px, icon_size_px))
        self.btn_next.setFixedHeight(nav_height - 8)
        self.btn_next.setEnabled(False)
        self.btn_next.setAutoDefault(False)
        try:
            self.btn_next.setDefault(False)
        except Exception:
            pass

        self.btn_reload = QPushButton()
        self.btn_reload.setToolTip("Reload")
        self.btn_reload.setIcon(QIcon(":/icons/reload.svg"))
        self.btn_reload.setIconSize(QSize(icon_size_px, icon_size_px))
        self.btn_reload.setFixedHeight(nav_height - 8)
        self.btn_reload.setAutoDefault(False)
        try:
            self.btn_reload.setDefault(False)
        except Exception:
            pass

        # "Go" button
        self.btn_go = QPushButton()
        self.btn_go.setToolTip("Open URL")
        self.btn_go.setIcon(QIcon(":/icons/redo.svg"))
        self.btn_go.setIconSize(QSize(icon_size_px, icon_size_px))
        self.btn_go.setFixedHeight(nav_height - 8)
        self.btn_go.setAutoDefault(False)  # avoid stealing Enter
        try:
            self.btn_go.setDefault(False)
        except Exception:
            pass

        # Address bar (custom line edit to capture Enter and avoid default button reload)
        self.address_bar = AddressLineEdit(on_return_callback=self._on_address_enter)
        self.address_bar.setPlaceholderText("Enter URL and press Enter")
        self.address_bar.setFixedHeight(nav_height - 8)
        # Still keep the Qt signal for completeness (won't fire because we intercept the key)
        self.address_bar.returnPressed.connect(self._on_address_enter)

        # Hook up button actions
        self.btn_back.clicked.connect(lambda: self._navigate('back'))
        self.btn_next.clicked.connect(lambda: self._navigate('forward'))
        self.btn_reload.clicked.connect(lambda: self._navigate('reload'))
        self.btn_go.clicked.connect(self._on_address_enter)  # "Go" triggers address open

        # Build nav layout
        self.nav_layout.addWidget(self.btn_back)
        self.nav_layout.addWidget(self.btn_next)
        self.nav_layout.addWidget(self.btn_reload)
        self.nav_layout.addWidget(self.address_bar, 1)
        self.nav_layout.addWidget(self.btn_go)
        self.nav_bar.setVisible(False)  # hidden by default

        # edit checkbox
        self.btn_edit = QCheckBox(trans("html_canvas.btn.edit"))
        self.btn_edit.stateChanged.connect(
            lambda: self.tool.toggle_edit(self)
        )

        path = self.tool.get_current_path()
        path_label = HelpLabel(path)
        path_label.setMaximumHeight(30)
        path_label.setAlignment(Qt.AlignRight)

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.btn_edit)
        bottom_layout.addWidget(path_label)

        output_layout = QVBoxLayout()
        # put navigation bar above the web output
        output_layout.addWidget(self.nav_bar)
        output_layout.addWidget(self.output)
        output_layout.addWidget(self.edit)
        output_layout.setContentsMargins(0, 0, 0, 0)

        # connect signals
        self.output.signals.save_as.connect(
            self.tool.handle_save_as)
        self.output.signals.audio_read.connect(
            self.window.controller.chat.render.handle_audio_read)

        # Keep nav bar in sync with the underlying view if signals are available
        # (urlChanged/loadStarted/loadFinished are part of QWebEngineView)
        if hasattr(self.output, 'urlChanged'):
            self.output.urlChanged.connect(self._on_url_changed)
        if hasattr(self.output, 'loadStarted'):
            try:
                self.output.loadStarted.connect(lambda: self._update_nav_controls())
            except TypeError:
                pass
        if hasattr(self.output, 'loadFinished'):
            try:
                self.output.loadFinished.connect(lambda ok: self._update_nav_controls())
            except TypeError:
                pass

        self.tool.signals.update.connect(self.set_output)
        self.tool.signals.reload.connect(self.load_output)
        self.tool.signals.url.connect(self.open_url)

        layout = QVBoxLayout()
        layout.addLayout(output_layout)
        layout.addLayout(bottom_layout)
        return layout

    @Slot(str)
    def set_output(self, content: str):
        """
        Set output content

        :param content: Content
        """
        self.edit.setPlainText(content)
        # Hide navigation bar when content is set via set_output (not a URL)
        self._show_navbar(False)

    @Slot(str)
    def open_url(self, url: str):
        """
        Open URL in output

        :param url: URL
        """
        print("Opening URL:", url)
        self._show_navbar(True)  # Show navigation bar for URL navigation
        if self.address_bar:
            self.address_bar.setText(url)
        self.output.setUrl(QUrl(url))
        self._update_nav_controls()

    @Slot(str)
    def load_output(self, path: str):
        """
        Load output content

        :param path: Content
        """
        self.output.setUrl(QUrl().fromLocalFile(path))
        # Hide navigation bar when loading from local file/path
        self._show_navbar(False)

    # ------------------
    # Navigation helpers
    # ------------------
    def _show_navbar(self, show: bool):
        """Show/hide the navigation bar."""
        if self.nav_bar:
            self.nav_bar.setVisible(show)
        # Keep controls state up-to-date
        self._update_nav_controls()

    def _navigate(self, action: str):
        """Perform navigation action on the output view."""
        if not self.output:
            return
        try:
            if action == 'back' and hasattr(self.output, 'back'):
                self.output.back()
            elif action == 'forward' and hasattr(self.output, 'forward'):
                self.output.forward()
            elif action == 'reload' and hasattr(self.output, 'reload'):
                self.output.reload()
        finally:
            self._update_nav_controls()

    def _on_address_enter(self):
        """Handle Enter pressed in the address bar or clicking GO."""
        if not self.output or not self.address_bar:
            return
        text = self.address_bar.text().strip()
        if not text:
            return
        url = QUrl.fromUserInput(text)
        if url.isValid():
            self._show_navbar(True)
            self.output.setUrl(url)
            self._update_nav_controls()

    def _on_url_changed(self, url: QUrl):
        """Keep address bar in sync with the view URL."""
        if self.address_bar:
            self.address_bar.setText(url.toString())
        self._update_nav_controls()

    def _update_nav_controls(self):
        """Enable/disable back/forward buttons based on history."""
        if not self.output:
            return
        # Reload is generally available when navbar is visible
        if self.btn_reload:
            self.btn_reload.setEnabled(True)
        # Back/forward depend on history if available
        if self.btn_back and self.btn_next:
            try:
                hist = self.output.history()
                self.btn_back.setEnabled(bool(hist and hist.canGoBack()))
                self.btn_next.setEnabled(bool(hist and hist.canGoForward()))
            except Exception:
                # If history is not available, keep safe defaults
                self.btn_back.setEnabled(False)
                self.btn_next.setEnabled(False)


class CanvasOutput(HtmlOutput):
    def __init__(self, window=None):
        """
        HTML canvas output

        :param window: main window
        """
        super(CanvasOutput, self).__init__(window)
        self.window = window


class CanvasEdit(BaseCodeEditor):
    def __init__(self, window=None):
        """
        Python interpreter output

        :param window: main window
        """
        super(CanvasEdit, self).__init__(window)
        self.window = window
        self.setReadOnly(False)
        self.value = 12
        self.max_font_size = 42
        self.min_font_size = 8
        self.setProperty('class', 'interpreter-output')
        self.default_stylesheet = ""
        self.setStyleSheet(self.default_stylesheet)
        self.tab = None
        self.installEventFilter(self)

    def set_tab(self, tab):
        """
        Set tab

        :param tab: Tab
        """
        self.tab = tab

    def eventFilter(self, source, event):
        """
        Focus event filter

        :param source: source
        :param event: event
        """
        if event.type() == event.Type.FocusIn:
            if self.tab is not None:
                col_idx = self.tab.column_idx
                self.window.controller.ui.tabs.on_column_focus(col_idx)
        return super().eventFilter(source, event)


# --- Address bar input widget ---
class AddressLineEdit(QLineEdit):
    """
    Custom QLineEdit that ensures Enter triggers opening the typed URL
    and prevents default buttons (e.g., Reload) from consuming the key.
    """
    def __init__(self, on_return_callback=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._on_return_callback = on_return_callback

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            # Call the assigned handler and stop propagation so default buttons won't trigger.
            if callable(self._on_return_callback):
                self._on_return_callback()
            event.accept()
            return
        super().keyPressEvent(event)


class ToolSignals(QObject):
    update = Signal(str)  # data
    reload = Signal(str)  # path
    url = Signal(str)  # url