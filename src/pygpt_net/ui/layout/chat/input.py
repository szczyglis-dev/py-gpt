#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.15 11:05:00                  #
# ================================================== #

from functools import partial

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QRadioButton, QWidget, \
    QGridLayout, QSizePolicy, QLabel

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
        self.min_height_input_tab = 80
        self.min_height_input = 50
        self.prev_input_splitter_value = 0

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
        tabs.addTab(files, trans('attachments.tab'))
        tabs.addTab(files_uploaded, trans('attachments_uploaded.tab'))
        tabs.addTab(files_ctx, trans('attachments_uploaded.tab'))
        tabs.addTab(input_extra, trans('input.tab.extra'))
        tabs.currentChanged.connect(self.update_min_height)

        upload_icon = QIcon(":/icons/upload.svg")
        tabs.setTabIcon(1, QIcon(":/icons/attachment.svg"))
        tabs.setTabIcon(2, upload_icon)
        tabs.setTabIcon(3, upload_icon)

        # Keep only the compact capability/tool icons in the same row as the
        # Input / Attachments / Uploaded tabs. Chat metadata (plugins, mode,
        # model, token/context counter) remains in the footer below the input.
        tabs.set_header_widget(self._setup_tabs_icons())

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addLayout(self.setup_header())
        layout.addWidget(tabs)
        layout.addLayout(self.setup_bottom())
        layout.setContentsMargins(0, 0, 0, 5)
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

    def setup_bottom(self) -> QVBoxLayout:
        """
        Setup the area below the input in two rows.

        Row 1:
        - left: chat metadata,
        - right: Enter / Shift+Enter / Send.

        Capability/tool icons are displayed in the input tab bar row.

        Row 2:
        - left: application status,
        - center: audio output level.

        :return: QVBoxLayout
        """
        nodes = self.window.ui.nodes

        metadata_layout = self._setup_footer_metadata()
        buttons_layout = self.setup_buttons()

        # Keep chat-only metadata and controls in separate widgets. Non-chat
        # output tabs hide both of these, while the global status, audio UI and
        # capability/tool icons remain available.
        nodes['chat.footer.metadata'] = QWidget()
        nodes['chat.footer.metadata'].setLayout(metadata_layout)
        nodes['chat.footer.controls'] = QWidget()
        nodes['chat.footer.controls'].setLayout(buttons_layout)

        # Preserve the existing metadata/control positions. The former center
        # column is now just flexible space because its icons live above.
        top_layout = QGridLayout()
        top_layout.setContentsMargins(0, 0, 2, 0)
        top_layout.setHorizontalSpacing(8)
        top_layout.addWidget(
            nodes['chat.footer.metadata'],
            0,
            0,
            alignment=Qt.AlignLeft | Qt.AlignVCenter,
        )
        top_layout.addWidget(
            nodes['chat.footer.controls'],
            0,
            2,
            alignment=Qt.AlignRight | Qt.AlignVCenter,
        )

        side_width = max(
            nodes['chat.footer.metadata'].sizeHint().width(),
            nodes['chat.footer.controls'].sizeHint().width(),
        )
        top_layout.setColumnMinimumWidth(0, side_width)
        top_layout.setColumnMinimumWidth(2, side_width)
        top_layout.setColumnStretch(0, 1)
        top_layout.setColumnStretch(1, 0)
        top_layout.setColumnStretch(2, 1)

        # Second row: status on the left, audio bar kept in the visual center.
        self.window.ui.plugin_addon['audio.output.bar'] = OutputBar(self.window)
        status_layout = self.status.setup()
        # Align status text with the content above and leave a little breathing
        # room below it without moving the centered audio indicator.
        status_layout.setContentsMargins(4, 0, 0, 10)

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

        bottom_side_width = status_layout.sizeHint().width()
        bottom_row.setColumnMinimumWidth(0, bottom_side_width)
        bottom_row.setColumnMinimumWidth(2, bottom_side_width)
        bottom_row.setColumnStretch(0, 1)
        bottom_row.setColumnStretch(1, 0)
        bottom_row.setColumnStretch(2, 1)

        footer_layout = QVBoxLayout()
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.setSpacing(0)
        footer_layout.addLayout(top_layout)
        footer_layout.addLayout(bottom_row)

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

        # Chat metadata order: mode, model, plugins, token/context counter.
        layout.addWidget(plugin_addon['schedule'], alignment=Qt.AlignVCenter)
        layout.addSpacing(4)
        layout.addWidget(nodes['chat.label'], alignment=Qt.AlignVCenter)
        layout.addSpacing(22)
        layout.addWidget(nodes['chat.model'], alignment=Qt.AlignVCenter)
        layout.addSpacing(22)
        layout.addWidget(nodes['chat.plugins'], alignment=Qt.AlignVCenter)
        layout.addSpacing(18)
        layout.addWidget(nodes['input.counter'], alignment=Qt.AlignVCenter)
        layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        return layout

    def _setup_tabs_icons(self) -> QWidget:
        """Build capability/tool icons for the input tab bar row."""
        nodes = self.window.ui.nodes

        widget = QWidget()
        widget.setObjectName('input-tabs-icons')
        widget.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

        layout = QHBoxLayout(widget)
        # Bias the centered icon row upward by ~2 px relative to the tabs.
        # The corner widget is taller than the 16 px icons, so increasing only
        # the bottom inset shifts the icons without changing their size.
        layout.setContentsMargins(6, 0, 4, 6)
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

        nodes['input.send_enter'] = QRadioButton(trans("input.radio.enter"))
        nodes['input.send_enter'].toggled.connect(partial(self._on_send_mode_toggled, 1))

        nodes['input.send_shift_enter'] = QRadioButton(trans("input.radio.enter_shift"))
        nodes['input.send_shift_enter'].toggled.connect(partial(self._on_send_mode_toggled, 2))

        nodes['input.send_btn'] = QPushButton(trans("input.btn.send"))
        nodes['input.send_btn'].clicked.connect(controller.chat.input.send_input)

        nodes['input.stop_btn'] = QPushButton(trans("input.btn.stop"))
        nodes['input.stop_btn'].setVisible(False)
        nodes['input.stop_btn'].clicked.connect(controller.chat.common.handle_stop)

        nodes['input.update_btn'] = QPushButton(trans("input.btn.update"))
        nodes['input.update_btn'].setVisible(False)
        nodes['input.update_btn'].clicked.connect(controller.ctx.extra.edit_submit)

        nodes['input.cancel_btn'] = QPushButton(trans("input.btn.cancel"))
        nodes['input.cancel_btn'].setVisible(False)
        nodes['input.cancel_btn'].clicked.connect(controller.ctx.extra.edit_cancel)

        nodes['ui.input.buttons'] = QHBoxLayout()
        nodes['ui.input.buttons'].setContentsMargins(0, 0, 0, 0)
        nodes['ui.input.buttons'].setSpacing(6)
        nodes['ui.input.buttons'].addWidget(nodes['input.send_enter'], alignment=Qt.AlignVCenter)
        nodes['ui.input.buttons'].addWidget(nodes['input.send_shift_enter'], alignment=Qt.AlignVCenter)
        nodes['ui.input.buttons'].addWidget(nodes['input.send_btn'], alignment=Qt.AlignVCenter)
        nodes['ui.input.buttons'].addWidget(nodes['input.stop_btn'], alignment=Qt.AlignVCenter)
        nodes['ui.input.buttons'].addWidget(nodes['input.cancel_btn'], alignment=Qt.AlignVCenter)
        nodes['ui.input.buttons'].addWidget(nodes['input.update_btn'], alignment=Qt.AlignVCenter)
        nodes['ui.input.buttons'].setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        return nodes['ui.input.buttons']

    def _on_send_mode_toggled(self, mode: int, checked: bool):
        if checked:
            self.window.controller.chat.common.toggle_send_shift(mode)

    def update_min_height(self):
        """
        Update the minimum height of the input tab
        """
        tabs = self.window.ui.tabs['input']
        nodes = self.window.ui.nodes
        splitters = self.window.ui.splitters
        controller_ui = self.window.controller.ui

        idx = tabs.currentIndex()
        if idx == 0 or idx == 4:
            # nodes['input'].setMinimumHeight(self.min_height_input)
            tabs.setMinimumHeight(self.min_height_input_tab)
            sizes = controller_ui.splitter_output_size_input
            if sizes and sizes != [0, 0]:
                splitters['main.output'].setSizes(sizes)
        else:
            sizes = controller_ui.splitter_output_size_files
            if sizes and controller_ui.splitter_output_size_input != [0, 0]:
                splitters['main.output'].setSizes(sizes)
            # nodes['input'].setMinimumHeight(self.min_height_files_tab)
            tabs.setMinimumHeight(self.min_height_files_tab + 90)