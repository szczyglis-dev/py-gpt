#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.28 08:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QPushButton, QHBoxLayout, QLabel, QVBoxLayout, QSplitter, QWidget, QSizePolicy, \
    QTabWidget, QFileDialog, QScrollArea, QFrame

from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_AGENT_LLAMA,
    MODE_AUDIO,
    MODE_CHAT,
    MODE_COMPLETION,
    MODE_EXPERT,
    MODE_IMAGE,
    MODE_LANGCHAIN,
    MODE_LLAMA_INDEX,
    MODE_VISION,
    MODE_RESEARCH,
    MODE_COMPUTER,
    MODE_AGENT_OPENAI,
)
from pygpt_net.ui.base.config_dialog import BaseConfigDialog
from pygpt_net.ui.widget.dialog.editor import EditorDialog
from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.ui.widget.lists.experts import ExpertsEditor
from pygpt_net.utils import trans


class Preset(BaseConfigDialog):
    def __init__(self, window=None, *args, **kwargs):
        super(Preset, self).__init__(window, *args, **kwargs)
        """
        Preset editor dialog

        :param window: Window instance
        """
        self.window = window
        self.id = "preset"
        self.dialog_id = "preset.presets"

    def setup(self):
        """Setup preset editor dialog"""
        self.window.ui.nodes['preset.btn.current'] = QPushButton(trans("dialog.preset.btn.current"))
        self.window.ui.nodes['preset.btn.save'] = QPushButton(trans("dialog.preset.btn.save"))
        self.window.ui.nodes['preset.btn.current'].clicked.connect(self.window.controller.presets.editor.from_current)
        self.window.ui.nodes['preset.btn.save'].clicked.connect(self.window.controller.presets.editor.save)

        self.window.ui.nodes['preset.btn.current'].setAutoDefault(False)
        self.window.ui.nodes['preset.btn.save'].setAutoDefault(True)

        footer = QHBoxLayout()
        footer.addWidget(self.window.ui.nodes['preset.btn.current'])
        footer.addWidget(self.window.ui.nodes['preset.btn.save'])

        # fields
        self.window.ui.paths[self.id] = QLabel(str(self.window.core.config.path))

        # get option fields config
        fields = self.window.controller.presets.editor.get_options()

        # build settings widgets
        widgets = self.build_widgets(self.id, fields, excluded=["tool.function"])  # from base config dialog

        # apply settings widgets
        for key in widgets:
            self.window.ui.config[self.id][key] = widgets[key]

        # apply widgets to layouts
        options = {}
        for key in widgets:
            if key == "tool.function":
                continue
            if fields[key]["type"] in ['text', 'int', 'float']:
                # if key != "prompt":  # built separately
                options[key] = self.add_option(widgets[key], fields[key])
            elif fields[key]["type"] == 'textarea':
                if key == "prompt":
                    widgets[key].setMinimumHeight(100)
                    continue
                if key == "description":
                    widgets[key].setMinimumHeight(50)
                else:
                    widgets[key].setMinimumHeight(100)
                options[key] = self.add_row_option(widgets[key], fields[key])
            elif fields[key]["type"] == 'bool':
                options[key] = self.add_raw_option(widgets[key], fields[key])
            elif fields[key]["type"] == 'dict':
                options[key] = self.add_row_option(widgets[key], fields[key])
            elif fields[key]["type"] == 'combo':
                options[key] = self.add_option(widgets[key], fields[key])
            elif fields[key]["type"] == 'bool_list':
                options[key] = self.add_row_option(widgets[key], fields[key])

        rows = QVBoxLayout()

        for key in options:
            options[key].setContentsMargins(0, 0, 0, 0)

        # modes
        mode_keys_left = [
            MODE_CHAT,
            MODE_LLAMA_INDEX,
            MODE_AUDIO,
            MODE_RESEARCH,
        ]
        mode_keys_middle = [
            MODE_COMPLETION,
            MODE_IMAGE,
            # MODE_VISION,
            MODE_COMPUTER,
            MODE_EXPERT,
        ]
        mode_keys_right = [
            MODE_AGENT_LLAMA,
            MODE_AGENT_OPENAI,
            MODE_AGENT,
        ]

        rows_mode_left = QVBoxLayout()
        rows_mode_left.setContentsMargins(0, 0, 0, 0)
        for key in mode_keys_left:
            rows_mode_left.addLayout(options[key])
        rows_mode_left.addStretch()

        rows_mode_middle = QVBoxLayout()
        rows_mode_middle.setContentsMargins(0, 0, 0, 0)
        for key in mode_keys_middle:
            rows_mode_middle.addLayout(options[key])
        rows_mode_middle.addStretch()

        rows_mode_right = QVBoxLayout()
        rows_mode_right.setContentsMargins(0, 0, 0, 0)
        for key in mode_keys_right:
            rows_mode_right.addLayout(options[key])
        rows_mode_right.addStretch()

        rows_mode = QHBoxLayout()
        rows_mode.addLayout(rows_mode_left)
        rows_mode.addLayout(rows_mode_middle)
        rows_mode.addLayout(rows_mode_right)
        rows_mode.setAlignment(Qt.AlignTop)
        rows_mode.setContentsMargins(0, 0, 0, 0)
        rows_mode.addStretch(1)

        # modes
        modes = QWidget()
        modes.setLayout(rows_mode)
        modes.setContentsMargins(0, 0, 0, 0)
        # Ensure modes column never grows taller than its content; avoids creating vertical gap above the splitter.
        modes.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.window.ui.nodes['preset.editor.modes'] = modes

        # experts
        self.window.ui.nodes['preset.editor.experts'] = ExpertsEditor(self.window)

        # desc and prompt
        desc = QWidget()
        desc.setLayout(options['description'])
        desc.setContentsMargins(0, 5, 0, 5)
        self.window.ui.nodes['preset.editor.description'] = desc

        # prompt + extra options
        prompt_layout = QVBoxLayout()
        prompt_layout.addWidget(widgets['prompt'])
        prompt_layout.setContentsMargins(0, 10, 0, 10)

        footer_layout = self.prepare_extra_config(prompt_layout)

        prompt_layout = QVBoxLayout()
        prompt_layout.setContentsMargins(0, 0, 0, 0)
        prompt_layout.addWidget(self.window.ui.nodes['preset.editor.description'])
        prompt_layout.addLayout(footer_layout)

        widget_prompt = QWidget()
        widget_prompt.setLayout(prompt_layout)
        widget_prompt.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        widget_prompt.setMinimumHeight(300)

        # left column
        left_keys = [
            "filename",
            "name",
            "model",
            "temperature",
            "agent_provider",
            "agent_provider_openai",
            "idx",
        ]
        # personalize tab
        personalize_keys = [
            "ai_name",
            "user_name",
            "ai_avatar",
            "ai_personalize",
        ]
        for key in left_keys:
            option_layout = options[key]
            if key in ["agent_provider", "agent_provider_openai"]:
                # special case with settings icon on right
                node_layout = QHBoxLayout()
                builder_btn = QPushButton(QIcon(":/icons/robot.svg"), "")
                builder_btn.setToolTip(trans("agent.builder.tooltip"))
                builder_btn.clicked.connect(lambda: self.window.tools.get("agent_builder").toggle())
                node_layout.setContentsMargins(0, 0, 0, 0)
                node_layout.addLayout(options[key])
                node_layout.addWidget(builder_btn)
                # align top right
                node_layout.setAlignment(builder_btn, Qt.AlignTop | Qt.AlignRight)
                option_layout = node_layout

            node_key = f"preset.editor.{key}"
            node = QWidget()
            node.setLayout(option_layout)
            node.setContentsMargins(0, 0, 0, 0)
            rows.addWidget(node)
            self.window.ui.nodes[node_key] = node

        # remote tools
        remote_tools =  QWidget()
        remote_tools.setLayout(options['remote_tools'])
        remote_tools.setContentsMargins(0, 0, 0, 0)
        self.window.ui.nodes['preset.editor.remote_tools'] = remote_tools

        rows_remote_tools = QVBoxLayout()
        rows_remote_tools.addWidget(self.window.ui.nodes['preset.editor.remote_tools'])
        rows_remote_tools.addStretch(1)

        widget_remote_tools = QWidget()
        widget_remote_tools.setLayout(rows_remote_tools)

        # personalize
        personalize_rows = QVBoxLayout()
        for key in personalize_keys:
            node_key = f"preset.editor.{key}"
            node = QWidget()
            node.setLayout(options[key])
            node.setContentsMargins(0, 0, 0, 0)
            personalize_rows.addWidget(node)
            self.window.ui.nodes[node_key] = node

        self.window.ui.nodes['preset.editor.ai_avatar'].setVisible(False)

        # warning label
        warn_label = HelpLabel(trans("preset.personalize.warning"))

        # avatar
        self.window.ui.nodes['preset.editor.avatar'] = AvatarWidget(self.window)
        personalize_rows.addWidget(self.window.ui.nodes['preset.editor.avatar'])
        personalize_rows.addStretch(1)
        personalize_rows.addWidget(warn_label)

        rows.setContentsMargins(0, 0, 0, 0)
        rows.addStretch(1)
        rows.setAlignment(Qt.AlignTop)

        widget_base = QWidget()
        widget_base.setLayout(rows)
        widget_base.setMinimumWidth(300)
        # Keep base column at content height; do not stretch vertically.
        widget_base.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

        self.window.ui.nodes['preset.editor.experts'].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        main = QHBoxLayout()
        main.addWidget(widget_base)
        main.addWidget(self.window.ui.nodes['preset.editor.modes'])

        widget_main = QWidget()
        widget_main.setLayout(main)
        # Critical: ensure the whole top pane (base + modes) stays at content height.
        widget_main.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(widget_main)
        splitter.addWidget(widget_prompt)
        splitter.setChildrenCollapsible(False)  # avoid accidental collapsing of any pane
        # All extra vertical space goes to bottom (extra agent options); top stays at its sizeHint.
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        self.window.ui.splitters['editor.presets'] = splitter

        widget_personalize = QWidget()
        widget_personalize.setLayout(personalize_rows)

        experts_rows = QVBoxLayout()
        experts_rows.addWidget(self.window.ui.nodes['preset.editor.experts'])

        widget_experts = QWidget()
        widget_experts.setLayout(experts_rows)

        tabs = QTabWidget()
        tabs.addTab(splitter, trans("preset.tab.general"))
        tabs.addTab(widget_personalize, trans("preset.tab.personalize"))
        tabs.addTab(widget_experts, trans("preset.tab.experts"))
        tabs.addTab(widget_remote_tools, trans("preset.tab.remote_tools"))
        self.window.ui.tabs['preset.editor.tabs'] = tabs

        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.tabs['preset.editor.tabs'])
        layout.addLayout(footer)

        dialog = EditorDialog(self.window, self.dialog_id)
        dialog.setSizeGripEnabled(True)
        dialog.setWindowFlags(
            dialog.windowFlags() | Qt.WindowMaximizeButtonHint
        )
        dialog.setLayout(layout)
        dialog.setWindowTitle(trans('dialog.preset'))
        dialog.on_close_callback = self.on_close
        self.window.ui.dialog['editor.' + self.dialog_id] = dialog


    def prepare_extra_config(self, prompt_layout):
        """
        Build extra configuration for the preset editor dialog

        :param prompt_layout: Layout for the prompt editor
        """
        prompt_layout.setContentsMargins(0, 10, 0, 10)
        prompt_widget = QWidget()
        prompt_widget.setLayout(prompt_layout)

        self.window.ui.nodes['preset.editor.extra'] = {}

        tabs = QTabWidget()

        # Make the prompt tab scrollable to avoid vertical overlap in narrow layouts.
        scroll_prompt = QScrollArea()
        scroll_prompt.setWidget(prompt_widget)
        scroll_prompt.setWidgetResizable(True)
        scroll_prompt.setFrameShape(QFrame.NoFrame)
        tabs.addTab(
            scroll_prompt,
            trans("preset.prompt"),
        )
        tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        tabs.setMinimumHeight(150)
        layout = QVBoxLayout()
        layout.addWidget(tabs)
        self.window.ui.tabs['preset.editor.extra'] = tabs
        return layout


    def build_option_widgets(self, id: str, fields: dict) -> tuple:
        """
        Build option widgets for the preset editor dialog

        :param id: Agent config unique id
        :param fields: Dictionary of options
        :return: tuple of widgets and options (layouts)
        """
        if id not in self.window.ui.config:
            self.window.ui.config[id] = {}

        widgets = self.build_widgets(id, fields)  # from base config dialog

        # apply settings widgets
        for key in widgets:
            self.window.ui.config[id][key] = widgets[key]

        # apply widgets to layouts
        options = {}
        for key in widgets:
            if fields[key]["type"] in ['text', 'int', 'float']:
                options[key] = self.add_option(widgets[key], fields[key])
            elif fields[key]["type"] == 'textarea':
                widgets[key].setMinimumHeight(100)
                options[key] = self.add_row_option(widgets[key], fields[key])
            elif fields[key]["type"] == 'bool':
                widgets[key].setMaximumHeight(38)
                options[key] = self.add_raw_option(widgets[key], fields[key])
            elif fields[key]["type"] == 'dict':
                options[key] = self.add_row_option(widgets[key], fields[key])
            elif fields[key]["type"] == 'combo':
                options[key] = self.add_option(widgets[key], fields[key])
            elif fields[key]["type"] == 'bool_list':
                options[key] = self.add_row_option(widgets[key], fields[key])

        return widgets, options

    # on close
    def on_close(self):
        """Close event callback"""
        self.window.controller.presets.select_current(no_scroll=True)
        self.window.controller.presets.editor.opened = False


class AvatarWidget(QWidget):
    def __init__(self, window=None):
        super().__init__(window)
        self.window = window
        self.avatar_preview = None
        self.choose_button = None
        self.remove_button = None
        self.path_line_edit = None
        self.init_ui()

    def init_ui(self):
        """Initialize the avatar widget UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        current_avatar_label = QLabel(trans("preset.personalize.avatar.current"))
        # Center the section title for better visual balance.
        current_avatar_label.setAlignment(Qt.AlignHCenter)
        main_layout.addWidget(current_avatar_label)

        self.avatar_preview = QLabel(self)
        self.avatar_preview.setFixedSize(200, 200)
        # Keep a visible border, but round it to visually indicate the circular avatar.
        self.avatar_preview.setStyleSheet("border: 1px solid gray; border-radius: 100px; background: transparent;")
        self.avatar_preview.setAlignment(Qt.AlignCenter)
        # Center the avatar widget within the column.
        main_layout.addWidget(self.avatar_preview, 0, Qt.AlignHCenter)

        buttons_layout = QHBoxLayout()

        self.choose_button = QPushButton(trans("preset.personalize.avatar.choose"), self)
        self.choose_button.clicked.connect(self.open_file_dialog)
        buttons_layout.addWidget(self.choose_button)

        self.remove_button = QPushButton(trans("preset.personalize.avatar.remove"), self)
        self.remove_button.clicked.connect(self.window.controller.presets.editor.remove_avatar)
        self.remove_button.setEnabled(False)
        buttons_layout.addWidget(self.remove_button)
        buttons_layout.setContentsMargins(0, 10, 0, 0)
        # Center the action buttons below the avatar.
        buttons_layout.setAlignment(Qt.AlignCenter)

        main_layout.addLayout(buttons_layout)
        main_layout.setContentsMargins(0, 10, 0, 0)
        main_layout.addStretch()

    def open_file_dialog(self):
        """Open a file dialog to select an avatar image file."""
        file_name, _ = QFileDialog.getOpenFileName(
            self, trans("preset.personalize.avatar.choose.title"), "", "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp)"
        )
        if file_name:
            self.window.controller.presets.editor.upload_avatar(file_name)

    def load_avatar(self, file_path: str):
        """
        Load and display the avatar image from the given file path.

        :param file_path: Path to the avatar image file
        """
        from PySide6.QtGui import QPixmap
        pixmap = QPixmap(file_path)
        if not pixmap.isNull():
            cover_pix = self.get_cover_pixmap(pixmap, self.avatar_preview.width(), self.avatar_preview.height())
            # Render the avatar as a circular pixmap.
            circle_pix = self.get_circular_pixmap(cover_pix, self.avatar_preview.width(), self.avatar_preview.height())
            self.avatar_preview.setPixmap(circle_pix)
        self.remove_button.setEnabled(True)

    def enable_remove_button(self, enabled: bool = True):
        """
        Enable or disable the remove button based on the presence of an avatar.

        :param enabled: True to enable, False to disable
        """
        self.remove_button.setEnabled(enabled)

    def disable_remove_button(self):
        """Disable the remove button."""
        self.enable_remove_button(False)

    def get_cover_pixmap(self, pixmap, target_width, target_height):
        """
        Scale and crop the pixmap to fit the target dimensions while maintaining aspect ratio.

        :param pixmap: Original pixmap
        :param target_width: Target width for the avatar preview
        :param target_height: Target height for the avatar preview
        :return: Scaled and cropped pixmap
        """
        factor = max(target_width / pixmap.width(), target_height / pixmap.height())
        new_width = int(pixmap.width() * factor)
        new_height = int(pixmap.height() * factor)
        scaled_pix = pixmap.scaled(new_width, new_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        x = (scaled_pix.width() - target_width) // 2
        y = (scaled_pix.height() - target_height) // 2
        return scaled_pix.copy(x, y, target_width, target_height)

    def get_circular_pixmap(self, pixmap, target_width: int, target_height: int):
        """
        Create a circular version of the given pixmap using an antialiased clip path.

        :param pixmap: Source pixmap already scaled/cropped to target size
        :param target_width: Target width
        :param target_height: Target height
        :return: Circular masked pixmap with transparent corners
        """
        from PySide6.QtGui import QPainter, QPainterPath, QPixmap  # local import to avoid altering global imports
        result = QPixmap(target_width, target_height)
        result.fill(Qt.transparent)

        painter = QPainter(result)
        painter.setRenderHint(QPainter.Antialiasing, True)
        path = QPainterPath()
        path.addEllipse(0, 0, target_width, target_height)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()

        return result

    def remove_avatar(self):
        """Remove the current avatar image."""
        self.avatar_preview.clear()
        self.remove_button.setEnabled(False)