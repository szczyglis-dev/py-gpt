#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.17 20:41:00
# ================================================== #

from PySide6.QtCore import Qt, QSize, QTimer, QPoint
from PySide6.QtGui import QIcon, QAction, QActionGroup
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QMenu, \
    QGridLayout, QSizePolicy, QLabel

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.ui.layout.chat.attachments import Attachments
from pygpt_net.ui.layout.chat.attachments_uploaded import AttachmentsUploaded
from pygpt_net.ui.layout.chat.attachments_ctx import AttachmentsCtx
from pygpt_net.ui.layout.status import Status
from pygpt_net.ui.widget.audio.bar import OutputBar
from pygpt_net.ui.widget.audio.input import AudioInput
from pygpt_net.ui.widget.audio.input_button import AudioInputButton
from pygpt_net.ui.widget.audio.output import AudioOutput
from pygpt_net.ui.widget.element.labels import HelpLabel, ChatStatusLabel, IconLabel
from pygpt_net.ui.widget.tabs.Input import InputTabs
from pygpt_net.ui.widget.textarea.input import ChatInput
from pygpt_net.ui.widget.textarea.input_extra import ExtraInput
from pygpt_net.utils import trans


class ChatInputContainer(QWidget):
    """Responsive wrapper that keeps the whole composer aligned with chat content."""

    CHAT_CONTENT_WIDTH = 800  # mirrors body max-width in data/css/web-chatgpt.css

    def __init__(self, window, content_widget):
        super().__init__()
        self.window = window
        self.content_widget = content_widget
        self._columns_splitter_connected = False
        self._content_geometry = None
        self._last_chat_column_idx = 0

        # Do not center the composer with layout margins. Large horizontal
        # margins become part of Qt's minimumSizeHint and can make the main
        # window grow while the WebView zoom is being changed. The child is
        # positioned manually instead, so its responsive width never places a
        # horizontal size constraint on the application window.
        self.content_widget.setParent(self)
        self.content_widget.show()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # The columns splitter is created after the input in ChatMain.setup(),
        # so bind lazily after the UI has completed its setup.
        QTimer.singleShot(0, self.sync_width)

    def _ensure_columns_splitter_hook(self):
        if self._columns_splitter_connected:
            return
        splitter = self.window.ui.splitters.get('columns')
        if splitter is None:
            return
        try:
            splitter.splitterMoved.connect(self._on_columns_splitter_moved)
            self._columns_splitter_connected = True
        except Exception:
            pass

    def _on_columns_splitter_moved(self, _pos, _index):
        # Run after Qt has committed the final pane geometries.
        QTimer.singleShot(0, self.sync_width)

    def _is_split_visible(self) -> bool:
        """Return True when both output columns have visible width."""
        splitter = self.window.ui.splitters.get('columns')
        if splitter is None or splitter.count() < 2:
            return False
        try:
            sizes = splitter.sizes()
            return len(sizes) > 1 and sizes[0] > 0 and sizes[1] > 0
        except Exception:
            return False

    def _active_chat_column_idx(self) -> int:
        """Track the last active output column that actually contains a chat."""
        tabs = getattr(self.window.controller.ui, 'tabs', None)
        if tabs is None:
            return self._last_chat_column_idx

        try:
            column_idx = int(tabs.get_current_column_idx())
            tab = tabs.get_current_tab()
        except Exception:
            return self._last_chat_column_idx

        if tab is not None and tab.type == Tab.TAB_CHAT and column_idx in (0, 1):
            self._last_chat_column_idx = column_idx
        return self._last_chat_column_idx

    def _column_area(self, column_idx: int, available: int):
        """Return the selected output column's x/width in this wrapper."""
        splitter = self.window.ui.splitters.get('columns')
        if splitter is None or not self._is_split_visible():
            return 0, available

        try:
            column = splitter.widget(column_idx)
            if column is None or column.width() <= 0:
                return 0, available

            # Map through global coordinates instead of reimplementing QSplitter
            # handle arithmetic. This keeps the composer aligned with the real
            # output pane even when styles change the splitter handle width.
            global_left = column.mapToGlobal(QPoint(0, 0))
            local_left = self.mapFromGlobal(global_left).x()
            x = max(0, min(available, int(local_left)))
            width = max(0, min(int(column.width()), available - x))
            if width <= 0:
                return 0, available
            return x, width
        except Exception:
            return 0, available

    def _target_content_width(self) -> int:
        try:
            zoom = float(self.window.core.config.get('zoom', 1.0) or 1.0)
        except (TypeError, ValueError):
            zoom = 1.0
        return max(1, int(round(self.CHAT_CONTENT_WIDTH * zoom)))

    def sizeHint(self) -> QSize:
        """Keep only the composer's vertical hint; never constrain window width."""
        hint = self.content_widget.sizeHint()
        return QSize(0, max(0, hint.height()))

    def minimumSizeHint(self) -> QSize:
        """Do not let composer controls contribute to the main window min width."""
        hint = self.content_widget.minimumSizeHint()
        return QSize(0, max(0, hint.height()))

    def sync_width(self):
        """Align composer with the active chat output column."""
        self._ensure_columns_splitter_hook()

        available = max(0, self.width())
        height = max(0, self.height())

        # In split view, follow the output column whose chat was active most
        # recently. Selecting a non-chat tab does not move the composer; it
        # remains below the last active chat column until another chat gains
        # focus. With split view collapsed, use the whole output area.
        column_idx = self._active_chat_column_idx()
        area_x, area_width = self._column_area(column_idx, available)

        # Zoom scales the same 800 px content width as the WebView, but the
        # composer is always clamped to its actual output column. Geometry is
        # applied only to the child, so it never contributes a larger minimum
        # width to the main application window.
        width = min(area_width, self._target_content_width())
        x = area_x + max(0, (area_width - width) // 2)
        geometry = (x, 0, width, height)
        if geometry == self._content_geometry:
            return

        self._content_geometry = geometry
        self.content_widget.setGeometry(*geometry)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.sync_width()


class ChatInputRootContainer(QWidget):
    """Full-width input area with a centered composer and global status footer."""

    def __init__(self, composer_widget, footer_widget):
        super().__init__()
        self.composer_widget = composer_widget
        self.footer_widget = footer_widget

        # Only the global status footer spans the whole available panel width,
        # independently from the 800 px / zoom-constrained composer above it.
        # Ignore its horizontal hint so it cannot increase the main window's
        # minimum width.
        self.footer_widget.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 5)
        layout.setSpacing(0)
        layout.addWidget(self.composer_widget, 1)
        layout.addWidget(self.footer_widget, 0)

    def sizeHint(self) -> QSize:
        hint = super().sizeHint()
        return QSize(0, max(0, hint.height()))

    def minimumSizeHint(self) -> QSize:
        hint = super().minimumSizeHint()
        return QSize(0, max(0, hint.height()))


class Input:
    VISION_ICON_SIZE = 16

    def __init__(self, window=None):
        """
        Input UI

        :param window: Window instance
        """
        self.window = window
        self.status = Status(window)
        self.attachments = Attachments(window)
        self.attachments_uploaded = AttachmentsUploaded(window)
        self.attachments_ctx = AttachmentsCtx(window)

        # min height
        self.min_height_files_tab = 120
        self.min_height_input_tab = 130
        self.min_height_input = 100

        # Exact main.output splitter geometry from the moment the user leaves
        # Input/Extra for a files tab. Attachments/Uploaded may temporarily
        # grow the lower pane, but returning to Input must restore the exact
        # height the user had before opening them (including manual resizing).
        self._input_splitter_sizes_before_files = None
        self._last_input_tab_index = 0
        self._main_output_splitter_connected = False

    def setup(self) -> QWidget:
        """
        Setup input

        :return: QWidget
        """
        input = self.setup_input()
        input_extra = self.setup_input_extra()
        files = self.setup_attachments()
        files_uploaded = self.setup_attachments_uploaded()
        files_ctx = self.setup_attachments_ctx()

        # Create metadata/capability nodes before the tab widget. Only the
        # capability icons are moved into the tab bar row; metadata stays in
        # its existing footer position.
        self._setup_footer_nodes()

        self.window.ui.tabs['input'] = InputTabs(self.window)
        tabs = self.window.ui.tabs['input']
        tabs.setMinimumHeight(self.min_height_input_tab)
        tabs.addTab(input, trans('input.tab'))
        tabs.addTab(files, '')
        tabs.addTab(files_uploaded, '')
        tabs.addTab(files_ctx, '')
        tabs.addTab(input_extra, trans('input.tab.extra'))
        tabs.currentChanged.connect(self.update_min_height)

        upload_icon = QIcon(":/icons/upload.svg")
        tabs.setTabIcon(1, QIcon(":/icons/attachment.svg"))
        tabs.setTabIcon(2, upload_icon)
        tabs.setTabIcon(3, upload_icon)
        tabs.set_compact_tab_count(1, 0)
        tabs.set_compact_tab_count(2, 0)
        tabs.set_compact_tab_count(3, 0)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.addLayout(self.setup_header())
        content_layout.addWidget(tabs)
        # Chat metadata (model / plugins / context counter) and edit controls
        # belong to the responsive composer and therefore stay aligned with
        # the 800 px × WebView zoom content width.
        content_layout.addLayout(self.setup_composer_footer())
        content_layout.setContentsMargins(0, 0, 0, 0)

        composer = ChatInputContainer(self.window, content)
        self.window.ui.nodes['input.container'] = composer

        # Only the application-wide status row is full width. This lets the
        # clock / Ready status sit at the far-left edge without pulling the
        # chat metadata out of the centered composer.
        footer = QWidget()
        footer.setLayout(self.setup_bottom())
        self.window.ui.nodes['input.footer.container'] = footer

        widget = ChatInputRootContainer(composer, footer)
        self.window.ui.nodes['input.root'] = widget

        # main.output is created around this input later in the UI setup. Keep
        # the normal Input splitter size synchronized from the first event-loop
        # turn so a files-tab switch can always restore the exact prior height.
        QTimer.singleShot(0, self._ensure_main_output_splitter_hook)
        return widget

    def setup_input(self) -> QWidget:
        """
        Setup input tab

        :return: QWidget
        """
        self.window.ui.nodes['input'] = ChatInput(self.window)
        self.window.ui.nodes['input'].setMinimumHeight(self.min_height_input)

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(self.window.ui.nodes['input'])
        layout.setContentsMargins(0, 0, 0, 0)
        return widget

    def setup_input_extra(self) -> QWidget:
        """
        Setup input tab (extra)

        :return: QWidget
        """
        self.window.ui.nodes['input_extra'] = ExtraInput(self.window)
        self.window.ui.nodes['input_extra'].setMinimumHeight(self.min_height_input)

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(self.window.ui.nodes['input_extra'])
        layout.setContentsMargins(0, 0, 0, 0)
        return widget

    def setup_attachments(self) -> QWidget:
        """
        Setup attachments

        :return: QWidget
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addLayout(self.attachments.setup())
        layout.setContentsMargins(0, 0, 0, 0)
        widget.setMinimumHeight(self.min_height_files_tab)
        return widget

    def setup_attachments_uploaded(self) -> QWidget:
        """
        Setup attachments uploaded

        :return: QWidget
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addLayout(self.attachments_uploaded.setup())
        layout.setContentsMargins(0, 0, 0, 0)
        widget.setMinimumHeight(self.min_height_files_tab)
        return widget

    def setup_attachments_ctx(self) -> QWidget:
        """
        Setup attachments ctx

        :return: QWidget
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addLayout(self.attachments_ctx.setup())
        layout.setContentsMargins(0, 0, 0, 0)
        widget.setMinimumHeight(self.min_height_files_tab)
        return widget

    def setup_header(self) -> QHBoxLayout:
        """
        Setup input header

        :return: QHBoxLayout
        """
        # header (input label + input counter)
        self.window.ui.nodes['input.label'] = HelpLabel(trans("input.label"))

        # plugin audio input addon
        self.window.ui.plugin_addon['audio.input'] = AudioInput(self.window)
        self.window.ui.plugin_addon['audio.input.btn'] = AudioInputButton(self.window)

        self.window.ui.plugin_addon['audio.input'].setVisible(False)
        self.window.ui.plugin_addon['audio.input.btn'].setVisible(False)

        grid = QGridLayout()

        center_layout = QHBoxLayout()
        center_layout.addStretch()
        center_layout.addWidget(self.window.ui.plugin_addon['audio.input'])
        center_layout.addWidget(self.window.ui.plugin_addon['audio.input.btn'])
        center_layout.addStretch()
        grid.addLayout(center_layout, 0, 1, alignment=Qt.AlignCenter)

        grid.setContentsMargins(0, 0, 0, 0)
        return grid

    def setup_composer_footer(self) -> QGridLayout:
        """Build chat metadata/edit controls inside the constrained composer."""
        nodes = self.window.ui.nodes

        metadata_layout = self._setup_footer_metadata()
        buttons_layout = self.setup_buttons()

        nodes['chat.footer.metadata'] = QWidget()
        nodes['chat.footer.metadata'].setLayout(metadata_layout)
        nodes['chat.footer.controls'] = QWidget()
        nodes['chat.footer.controls'].setLayout(buttons_layout)

        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 2, 0)
        layout.setHorizontalSpacing(8)
        layout.addWidget(
            nodes['chat.footer.metadata'],
            0,
            0,
            alignment=Qt.AlignLeft | Qt.AlignVCenter,
        )
        layout.addWidget(
            nodes['chat.footer.controls'],
            0,
            2,
            alignment=Qt.AlignRight | Qt.AlignVCenter,
        )

        side_width = max(
            nodes['chat.footer.metadata'].sizeHint().width(),
            nodes['chat.footer.controls'].sizeHint().width(),
        )
        layout.setColumnMinimumWidth(0, side_width)
        layout.setColumnMinimumWidth(2, side_width)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 0)
        layout.setColumnStretch(2, 1)
        return layout

    def setup_bottom(self) -> QVBoxLayout:
        """Build the full-width application status row below the composer."""
        nodes = self.window.ui.nodes

        self.window.ui.plugin_addon['audio.output.bar'] = OutputBar(self.window)
        status_layout = self.status.setup()
        status_layout.setContentsMargins(4, 0, 0, 5)

        bottom_row = QGridLayout()
        bottom_row.setContentsMargins(2, 0, 2, 0)
        bottom_row.setHorizontalSpacing(6)
        bottom_row.addLayout(status_layout, 0, 0, alignment=Qt.AlignLeft | Qt.AlignVCenter)
        bottom_row.addWidget(
            self.window.ui.plugin_addon['audio.output.bar'],
            0,
            1,
            alignment=Qt.AlignCenter,
        )

        # Capability/tool icons are application-wide controls, so keep them in
        # the same full-width row as the global status. Status stays pinned to
        # the far left, while the icons are pinned to the far right.
        icons = self._setup_tabs_icons()
        bottom_row.addWidget(
            icons,
            0,
            2,
            alignment=Qt.AlignRight | Qt.AlignVCenter,
        )

        bottom_side_width = max(
            status_layout.sizeHint().width(),
            icons.sizeHint().width(),
        )
        bottom_row.setColumnMinimumWidth(0, bottom_side_width)
        bottom_row.setColumnMinimumWidth(2, bottom_side_width)
        bottom_row.setColumnStretch(0, 1)
        bottom_row.setColumnStretch(1, 0)
        bottom_row.setColumnStretch(2, 1)

        footer_layout = QVBoxLayout()
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.setSpacing(0)
        footer_layout.addLayout(bottom_row)

        # Keep the historic node name: controller.ui.mode intentionally keeps
        # this global footer visible while independently hiding chat metadata.
        nodes['chat.footer'] = QWidget()
        nodes['chat.footer'].setLayout(footer_layout)

        layout = QVBoxLayout()
        layout.addWidget(nodes['chat.footer'])
        layout.setContentsMargins(0, 0, 0, 0)
        return layout

    def _setup_footer_nodes(self):
        """Create controls formerly displayed below the chat output."""
        nodes = self.window.ui.nodes
        plugin_addon = self.window.ui.plugin_addon
        ctrl = self.window.controller
        tools = self.window.tools

        nodes['icon.plain'] = IconLabel(":/icons/text.svg", window=self.window)
        nodes['icon.plain'].clicked.connect(ctrl.chat.common.toggle_plain_view)
        ctrl.chat.common.update_plain_view_tooltip()

        nodes['icon.video.capture'] = IconLabel(":/icons/webcam.svg", window=self.window)
        nodes['icon.video.capture'].setToolTip(trans("icon.video.capture"))
        nodes['icon.video.capture'].clicked.connect(lambda: ctrl.camera.toggle_capture())

        nodes['icon.audio.output'] = IconLabel(":/icons/volume.svg", window=self.window)
        nodes['icon.audio.output'].setToolTip(trans("icon.audio.output"))
        nodes['icon.audio.output'].clicked.connect(lambda: ctrl.plugins.toggle_audio_output())

        nodes['icon.audio.input'] = IconLabel(":/icons/mic.svg", window=self.window)
        nodes['icon.audio.input'].setToolTip(trans("icon.audio.input"))
        nodes['icon.audio.input'].clicked.connect(lambda: ctrl.plugins.toggle('audio_input'))

        nodes['icon.interpreter'] = IconLabel(":/icons/code.svg", window=self.window)
        nodes['icon.interpreter'].setToolTip("Python/OS")
        nodes['icon.interpreter'].clicked.connect(lambda: tools.get("interpreter").toggle())

        nodes['icon.indexer'] = IconLabel(":/icons/db.svg", window=self.window)
        nodes['icon.indexer'].setToolTip("Indexer")
        nodes['icon.indexer'].clicked.connect(lambda: tools.get("indexer").toggle())

        min_policy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        nodes['chat.label'] = ChatStatusLabel("")
        nodes['chat.label'].setSizePolicy(min_policy)
        nodes['chat.label'].setWordWrap(False)

        nodes['chat.model'] = ChatStatusLabel("")
        nodes['chat.model'].setSizePolicy(min_policy)
        nodes['chat.model'].setWordWrap(False)

        nodes['chat.plugins'] = ChatStatusLabel("")
        nodes['chat.plugins'].setSizePolicy(min_policy)

        nodes['input.counter'] = ChatStatusLabel("")
        nodes['input.counter'].setToolTip("")
        nodes['input.counter'].setWordWrap(False)

        # Preserve addon initialization from the old output footer.
        plugin_addon['audio.output'] = AudioOutput(self.window)
        plugin_addon['schedule'] = ChatStatusLabel("")

        nodes['inline.vision'] = QLabel()
        nodes['inline.vision'].setPixmap(
            QIcon(":/icons/vision.svg").pixmap(QSize(self.VISION_ICON_SIZE, self.VISION_ICON_SIZE))
        )
        nodes['inline.vision'].setAlignment(Qt.AlignCenter)
        nodes['inline.vision'].setToolTip(trans('vision.checkbox.tooltip'))
        nodes['inline.vision'].setContentsMargins(0, 0, 0, 0)
        nodes['inline.vision'].setFixedSize(
            self.VISION_ICON_SIZE,
            self.VISION_ICON_SIZE,
        )
        nodes['inline.vision'].setVisible(False)

        # Kept for compatibility with the existing (currently disabled) loading
        # helper in ui/__init__.py.
        nodes['anim.loading'] = QWidget()
        nodes['anim.loading'].hide()

    def _setup_footer_metadata(self) -> QHBoxLayout:
        """Build chat metadata on the far left."""
        nodes = self.window.ui.nodes
        plugin_addon = self.window.ui.plugin_addon

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Chat metadata order: model, plugins, token/context counter.
        # Keep chat.label initialized for controller compatibility, but do not
        # show the mode name in the composer footer.
        layout.addWidget(plugin_addon['schedule'], alignment=Qt.AlignVCenter)
        layout.addSpacing(4)
        layout.addWidget(nodes['chat.model'], alignment=Qt.AlignVCenter)
        layout.addSpacing(22)
        layout.addWidget(nodes['chat.plugins'], alignment=Qt.AlignVCenter)
        layout.addSpacing(18)
        layout.addWidget(nodes['input.counter'], alignment=Qt.AlignVCenter)
        layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        return layout

    def _setup_tabs_icons(self) -> QWidget:
        """Build capability/tool icons for the global bottom status row."""
        nodes = self.window.ui.nodes

        widget = QWidget()
        widget.setObjectName('input-status-icons')
        widget.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 0, 4, 7)
        layout.setSpacing(5)
        layout.addWidget(nodes['icon.plain'], alignment=Qt.AlignVCenter)
        layout.addWidget(nodes['inline.vision'], alignment=Qt.AlignVCenter)
        layout.addWidget(nodes['icon.video.capture'], alignment=Qt.AlignVCenter)
        layout.addWidget(nodes['icon.audio.input'], alignment=Qt.AlignVCenter)
        layout.addWidget(nodes['icon.audio.output'], alignment=Qt.AlignVCenter)
        layout.addWidget(nodes['icon.interpreter'], alignment=Qt.AlignVCenter)
        layout.addWidget(nodes['icon.indexer'], alignment=Qt.AlignVCenter)
        layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        nodes['chat.icons.header'] = widget
        return widget

    def setup_buttons(self) -> QHBoxLayout:
        """
        Setup input buttons

        :return: QHBoxLayout
        """
        nodes = self.window.ui.nodes
        controller = self.window.controller

        # Send is an icon-only control embedded directly in ChatInput's
        # bottom-right bar, after the microphone/reasoning controls.
        nodes['input.send_btn'] = nodes['input'].add_right_icon(
            key="send",
            icon=QIcon(":/icons/play.svg"),
            tooltip=trans("input.btn.send"),
            callback=controller.chat.input.send_input,
            visible=True,
        )

        # Send-key behavior is selected from a compact context menu instead of
        # permanently occupying footer space with two radio buttons. Left click
        # still sends normally; right click opens the exclusive Enter mode menu.
        nodes['input.send.menu'] = QMenu(nodes['input.send_btn'])

        # Use the same visible section-header convention as the Reasoning
        # effort popup: disabled + bold action followed by a separator.
        # QMenu.addSection() can be rendered almost invisibly by some native
        # themes, while a disabled QAction remains readable in light/dark mode.
        nodes['input.send_mode.header'] = QAction(trans("input.send_with"), nodes['input.send.menu'])
        nodes['input.send_mode.header'].setEnabled(False)
        header_font = nodes['input.send_mode.header'].font()
        header_font.setBold(True)
        nodes['input.send_mode.header'].setFont(header_font)
        nodes['input.send.menu'].addAction(nodes['input.send_mode.header'])
        nodes['input.send.menu'].addSeparator()

        nodes['input.send_mode.group'] = QActionGroup(nodes['input.send.menu'])
        nodes['input.send_mode.group'].setExclusive(True)

        nodes['input.send_mode.enter'] = nodes['input.send.menu'].addAction(trans("input.radio.enter"))
        nodes['input.send_mode.enter'].setCheckable(True)
        nodes['input.send_mode.group'].addAction(nodes['input.send_mode.enter'])
        nodes['input.send_mode.enter'].triggered.connect(
            lambda checked: self._on_send_mode_selected(1, checked)
        )

        nodes['input.send_mode.shift_enter'] = nodes['input.send.menu'].addAction(
            trans("input.radio.enter_shift")
        )
        nodes['input.send_mode.shift_enter'].setCheckable(True)
        nodes['input.send_mode.group'].addAction(nodes['input.send_mode.shift_enter'])
        nodes['input.send_mode.shift_enter'].triggered.connect(
            lambda checked: self._on_send_mode_selected(2, checked)
        )

        nodes['input.send_btn'].setContextMenuPolicy(Qt.CustomContextMenu)
        nodes['input.send_btn'].customContextMenuRequested.connect(self._show_send_mode_menu)

        # Stop occupies the same compact icon bar as Send. It is hidden while
        # idle and shown by chat.common.lock_input().
        nodes['input.stop_btn'] = nodes['input'].add_right_icon(
            key="stop",
            icon=QIcon(":/icons/stop.svg"),
            tooltip=trans("input.btn.stop"),
            callback=controller.chat.common.handle_stop,
            visible=False,
        )

        # Context-item editing controls also live inside ChatInput. Keep their
        # text labels (they are less frequent/destructive actions), but let the
        # right-bar API own visibility so geometry and viewport margins are
        # always recalculated when edit mode starts/stops. Preserve the old
        # visual order: Cancel, then Update.
        nodes['input.cancel_btn'] = nodes['input'].add_right_button(
            key="cancel",
            text=trans("input.btn.cancel"),
            callback=controller.ctx.extra.edit_cancel,
            visible=False,
        )
        nodes['input.update_btn'] = nodes['input'].add_right_button(
            key="update",
            text=trans("input.btn.update"),
            callback=controller.ctx.extra.edit_submit,
            visible=False,
        )

        # Compatibility node retained for code that expects composer footer
        # controls to exist. The actual action buttons now live in ChatInput.
        nodes['ui.input.buttons'] = QHBoxLayout()
        nodes['ui.input.buttons'].setContentsMargins(0, 0, 0, 0)
        nodes['ui.input.buttons'].setSpacing(0)

        return nodes['ui.input.buttons']

    def _show_send_mode_menu(self, pos):
        """Show Send key behavior selector on right click."""
        nodes = self.window.ui.nodes
        mode = self.window.core.config.get('send_mode')
        if mode not in (1, 2):
            mode = 1

        # Refresh translation and check state just before opening so the popup
        # always reflects the current runtime config and active locale.
        nodes['input.send_mode.header'].setText(trans("input.send_with"))
        nodes['input.send_mode.enter'].setText(trans("input.radio.enter"))
        nodes['input.send_mode.shift_enter'].setText(trans("input.radio.enter_shift"))
        nodes['input.send_mode.enter'].setChecked(mode == 1)
        nodes['input.send_mode.shift_enter'].setChecked(mode == 2)

        button = nodes['input.send_btn']
        nodes['input.send.menu'].exec(button.mapToGlobal(pos))

    def _on_send_mode_selected(self, mode: int, checked: bool):
        if checked:
            self.window.controller.chat.common.toggle_send_shift(mode)

    def _ensure_main_output_splitter_hook(self):
        """Track manual Input-pane resizing independently from files-tab sizing."""
        if self._main_output_splitter_connected:
            return
        splitter = self.window.ui.splitters.get('main.output')
        if splitter is None:
            QTimer.singleShot(0, self._ensure_main_output_splitter_hook)
            return
        try:
            splitter.splitterMoved.connect(self._on_main_output_splitter_moved)
            self._main_output_splitter_connected = True
        except Exception:
            return
        self._remember_live_input_splitter_sizes()

    def _remember_live_input_splitter_sizes(self):
        """Persist current splitter sizes only while Input/Extra is active."""
        tabs = self.window.ui.tabs.get('input')
        splitter = self.window.ui.splitters.get('main.output')
        if tabs is None or splitter is None or tabs.currentIndex() not in (0, 4):
            return
        try:
            sizes = list(splitter.sizes())
            if sizes and len(sizes) == splitter.count():
                self.window.controller.ui.splitter_output_size_input = sizes
        except Exception:
            pass

    def _on_main_output_splitter_moved(self, _pos, _index):
        # User drags while Input is visible must become the new restore target.
        self._remember_live_input_splitter_sizes()

    def _restore_input_splitter_sizes(self, sizes):
        """Restore the exact pre-files splitter geometry after Qt relayouts tabs."""
        tabs = self.window.ui.tabs.get('input')
        splitter = self.window.ui.splitters.get('main.output')
        if tabs is None or splitter is None or tabs.currentIndex() not in (0, 4):
            return
        if not sizes or len(sizes) != splitter.count():
            return

        try:
            # Lower the files-tab constraint before restoring. Calling this on
            # the next event-loop turn is important: QTabWidget/QSplitter can
            # otherwise still use the previous page's cached minimum height.
            tabs.setMinimumHeight(self.min_height_input_tab)
            tabs.updateGeometry()

            composer = self.window.ui.nodes.get('input.container')
            if composer is not None:
                composer.updateGeometry()
            root = self.window.ui.nodes.get('input.root')
            if root is not None:
                root.updateGeometry()

            # Prevent ChatInput's content auto-resize timer from immediately
            # replacing the restored user height while the tab becomes visible.
            chat_input = self.window.ui.nodes.get('input')
            previous_guard = None
            if chat_input is not None:
                try:
                    timer = getattr(chat_input, '_auto_timer', None)
                    if timer is not None and timer.isActive():
                        timer.stop()
                    chat_input._pending_force = False
                    chat_input._pending_minimize_if_single = False
                    previous_guard = getattr(chat_input, '_splitter_resize_in_progress', False)
                    chat_input._splitter_resize_in_progress = True
                except Exception:
                    previous_guard = None

            try:
                splitter.setSizes(list(sizes))
            finally:
                if chat_input is not None and previous_guard is not None:
                    try:
                        chat_input._splitter_resize_in_progress = previous_guard
                    except Exception:
                        pass

            # Keep the normal-input remembered size synchronized with what Qt
            # actually accepted after applying current style/minimum hints.
            self.window.controller.ui.splitter_output_size_input = list(splitter.sizes())
        except Exception:
            # Geometry restoration must never break tab switching.
            return

    def update_min_height(self, _index=None):
        """Resize files tabs temporarily and restore Input to its exact prior height."""
        tabs = self.window.ui.tabs['input']
        nodes = self.window.ui.nodes
        splitters = self.window.ui.splitters
        controller_ui = self.window.controller.ui

        idx = tabs.currentIndex()
        previous_idx = self._last_input_tab_index
        current_is_input = idx in (0, 4)
        previous_was_input = previous_idx in (0, 4)
        splitter = splitters.get('main.output')

        if current_is_input:
            # Input/Extra use the normal minimum. If we are returning from a
            # files tab, restore the *live* splitter sizes captured immediately
            # before that files tab was opened, rather than a historical/cache
            # value that may not reflect a user's latest manual resize.
            tabs.setMinimumHeight(self.min_height_input_tab)
            tabs.updateGeometry()

            composer = nodes.get('input.container')
            if composer is not None:
                composer.updateGeometry()
            root = nodes.get('input.root')
            if root is not None:
                root.updateGeometry()

            restore_sizes = None
            if not previous_was_input and self._input_splitter_sizes_before_files:
                restore_sizes = list(self._input_splitter_sizes_before_files)
            elif controller_ui.splitter_output_size_input:
                restore_sizes = list(controller_ui.splitter_output_size_input)

            if splitter is not None and restore_sizes:
                # Apply once immediately so the UI snaps back without waiting,
                # then repeat on the next tick after Qt has discarded the
                # hidden Attachments/Uploaded page's old layout constraints.
                self._restore_input_splitter_sizes(restore_sizes)
                QTimer.singleShot(0, lambda s=list(restore_sizes): self._restore_input_splitter_sizes(s))

            if not previous_was_input:
                self._input_splitter_sizes_before_files = None

            self._last_input_tab_index = idx
            return

        # Capture the exact current Input/Extra height only on the transition
        # into the files area. Moving between Attachments and Uploaded must not
        # overwrite this snapshot with the already-expanded files-tab height.
        if previous_was_input and splitter is not None:
            # Prefer the continuously synchronized normal-Input geometry. This
            # is captured on manual splitter drags and by ChatInput auto-resize,
            # so it still represents the pre-click height even if QTabWidget
            # has already started relayouting the newly selected files page.
            saved_sizes = controller_ui.splitter_output_size_input
            if saved_sizes and len(saved_sizes) == splitter.count():
                self._input_splitter_sizes_before_files = list(saved_sizes)
            else:
                try:
                    live_sizes = list(splitter.sizes())
                    if live_sizes and len(live_sizes) == splitter.count():
                        self._input_splitter_sizes_before_files = live_sizes
                        controller_ui.splitter_output_size_input = list(live_sizes)
                except Exception:
                    pass

        self._last_input_tab_index = idx

        # Attachments/Uploaded must grow the *tab content area*, not the list
        # itself. Keep the original page/list minimum (120 px) and derive the
        # tab height from the active page's real minimum size plus the tab bar.
        page = tabs.currentWidget()
        page_min = 0
        if page is not None:
            try:
                page_min = max(0, int(page.minimumSizeHint().height()))
            except Exception:
                page_min = 0
        try:
            tab_bar_h = max(0, int(tabs.tabBar().sizeHint().height()))
        except Exception:
            tab_bar_h = 0

        # Small frame allowance covers QTabWidget styling without inflating the
        # attachment list. The historical 210 px target remains a fallback.
        content_target = page_min + tab_bar_h + 8
        files_tab_height = max(self.min_height_files_tab + 90, content_target)
        tabs.setMinimumHeight(files_tab_height)
        tabs.updateGeometry()

        composer = nodes.get('input.container')
        if composer is not None:
            composer.updateGeometry()
        root = nodes.get('input.root')
        if root is not None:
            root.updateGeometry()

        # Files tabs are grow-only relative to the pane height that was visible
        # before the switch. If Input is already tall enough to show the active
        # Attachments/Uploaded page, keep its exact splitter geometry instead of
        # shrinking/growing to a historical files-tab size. This also applies
        # when moving between the two files tabs: keep the current height unless
        # the newly selected page genuinely needs more room.
        baseline_sizes = None
        if splitter is not None:
            if previous_was_input and self._input_splitter_sizes_before_files:
                baseline_sizes = list(self._input_splitter_sizes_before_files)
            else:
                try:
                    current_sizes = list(splitter.sizes())
                    if current_sizes and len(current_sizes) == splitter.count():
                        baseline_sizes = current_sizes
                except Exception:
                    baseline_sizes = None

        if baseline_sizes and self._keep_files_height_if_sufficient(baseline_sizes):
            # Repeat after Qt finishes the tab relayout. If the final size hints
            # reveal that more height is actually required, the helper falls
            # back to the normal grow-only visibility pass.
            QTimer.singleShot(0, lambda s=list(baseline_sizes): self._keep_or_grow_files_height(s))
        else:
            QTimer.singleShot(0, self._ensure_files_tab_content_visible)

    def _input_pane_index(self, splitter, root):
        """Return the main.output splitter index containing the input root."""
        if splitter is None or root is None:
            return -1
        try:
            for i in range(splitter.count()):
                widget = splitter.widget(i)
                if widget is root or (widget is not None and widget.isAncestorOf(root)):
                    return i
        except Exception:
            pass
        return -1

    def _keep_files_height_if_sufficient(self, sizes):
        """Keep an existing files-pane height when it already fits all controls."""
        tabs = self.window.ui.tabs.get('input')
        splitter = self.window.ui.splitters.get('main.output')
        root = self.window.ui.nodes.get('input.root')
        if tabs is None or tabs.currentIndex() in (0, 4) or splitter is None or root is None:
            return False
        if not sizes or len(sizes) != splitter.count():
            return False

        try:
            root.updateGeometry()
            idx = self._input_pane_index(splitter, root)
            if idx < 0 or idx >= len(sizes):
                return False

            requested_h = max(0, int(sizes[idx]))
            required_h = max(0, int(root.minimumSizeHint().height()))
            if requested_h + 1 < required_h:
                return False

            splitter.setSizes(list(sizes))
            actual = list(splitter.sizes())
            if idx >= len(actual):
                return False

            # Qt may clamp setSizes() to a newly propagated minimum. Treat that
            # as insufficient so the regular grow pass can finish the layout.
            if int(actual[idx]) + 1 < required_h:
                return False

            self.window.controller.ui.splitter_output_size_files = actual
            return True
        except Exception:
            return False

    def _keep_or_grow_files_height(self, sizes):
        """Preserve the prior height if possible, otherwise grow only as needed."""
        if not self._keep_files_height_if_sufficient(sizes):
            self._ensure_files_tab_content_visible()

    def _ensure_files_tab_content_visible(self):
        """Grow the input pane just enough to show the active files tab controls."""
        tabs = self.window.ui.tabs.get('input')
        if tabs is None or tabs.currentIndex() in (0, 4):
            return

        splitter = self.window.ui.splitters.get('main.output')
        root = self.window.ui.nodes.get('input.root')
        if splitter is None or root is None:
            return

        try:
            root.updateGeometry()
            current = list(splitter.sizes())
            if not current:
                return

            input_idx = self._input_pane_index(splitter, root)
            if input_idx < 0 or input_idx >= len(current):
                return

            current_input_h = int(current[input_idx])
            required_h = max(0, int(root.minimumSizeHint().height()))

            # If Qt has not yet propagated the QTabWidget minimum through the
            # wrapper, account for the still-clipped tab height explicitly.
            clipped_tab_h = max(0, int(tabs.minimumHeight()) - int(tabs.height()))
            required_h = max(required_h, current_input_h + clipped_tab_h)
            if required_h <= current_input_h + 1:
                self.window.controller.ui.splitter_output_size_files = current
                return

            total = sum(current)
            if total <= 0:
                return

            other_min_total = 0
            for i in range(splitter.count()):
                if i == input_idx:
                    continue
                widget = splitter.widget(i)
                if widget is not None:
                    try:
                        other_min_total += max(0, int(widget.minimumSizeHint().height()))
                    except Exception:
                        pass

            target_h = min(required_h, max(current_input_h, total - other_min_total))
            if target_h <= current_input_h + 1:
                return

            delta = target_h - current_input_h
            new_sizes = list(current)
            new_sizes[input_idx] = target_h

            # main.output is normally a two-pane vertical splitter. Distribute
            # the required delta over the remaining panes without changing the
            # total splitter height.
            remaining = delta
            for i in range(len(new_sizes)):
                if i == input_idx or remaining <= 0:
                    continue
                widget = splitter.widget(i)
                min_h = 0
                if widget is not None:
                    try:
                        min_h = max(0, int(widget.minimumSizeHint().height()))
                    except Exception:
                        min_h = 0
                reducible = max(0, new_sizes[i] - min_h)
                take = min(reducible, remaining)
                new_sizes[i] -= take
                remaining -= take

            if remaining > 0:
                new_sizes[input_idx] -= remaining

            if new_sizes[input_idx] <= current_input_h + 1:
                return

            splitter.setSizes(new_sizes)
            self.window.controller.ui.splitter_output_size_files = list(splitter.sizes())
        except Exception:
            # Layout sizing must never break tab switching.
            return
