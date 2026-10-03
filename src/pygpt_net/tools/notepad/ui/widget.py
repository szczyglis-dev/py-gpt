#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.04 00:00:00                  #
# ================================================== #
"""Notepad tab layout and microphone controls."""
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy, QPushButton
from pygpt_net.core.events import Event
from pygpt_net.core.tabs.tab import Tab
from pygpt_net.ui.widget.audio.bar import InputRecordWidget
from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.utils import trans
from .editor import NotepadOutput

class NotepadHelpLabel(HelpLabel):
    """Help label that follows the full responsive width of the notepad tab."""

    def __init__(self, text, window=None):
        super().__init__(text, window)
        self.setMinimumWidth(0)
        policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        # Preserve QLabel's height-for-width behaviour used by word wrapping.
        # Without this flag the layout may reserve only a single text line.
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)

class NotepadWidget(QWidget):
    def __init__(self, session, window=None):
        """
        Notepad

        :param window: main window
        """
        super(NotepadWidget, self).__init__(window)
        self.window = window
        self.session = session
        self.id = session.item.idx
        self.textarea = NotepadOutput(session, self.window)
        self.help_label = NotepadHelpLabel(
            trans('tip.output.tab.notepad'),
            self,
        )
        self.tab = None

        # When Chat Input is hidden on a Notepad tab, keep the simple audio
        # input action available directly below the notepad. The wrapper owns
        # the requested 15 px breathing room and disappears completely when
        # simple audio input is disabled/advanced.
        self.mic_button = QPushButton(self)
        self.mic_button.setObjectName('notepadMicButton')
        self.mic_button.setIcon(QIcon(':/icons/mic.svg'))
        self.mic_button.setIconSize(QSize(20, 20))
        self.mic_button.setFixedSize(QSize(26, 26))
        self.mic_button.setCursor(Qt.PointingHandCursor)
        self.mic_button.setFocusPolicy(Qt.NoFocus)
        self.mic_button.setFlat(True)
        self.mic_button.setToolTip(trans('audio.note.btn.tooltip'))
        self.mic_button.clicked.connect(self.toggle_microphone)

        # Reuse the same input recording widget as ChatInput so colors,
        # elapsed time, level rendering and animations stay identical.
        self.record_status = InputRecordWidget(self.window, self)
        policy = self.record_status.sizePolicy()
        policy.setRetainSizeWhenHidden(True)
        self.record_status.setSizePolicy(policy)

        self.mic_container = QWidget(self)
        mic_layout = QVBoxLayout(self.mic_container)
        mic_layout.setContentsMargins(15, 15, 15, 15)
        mic_layout.setSpacing(8)
        mic_layout.addWidget(self.mic_button, 0, Qt.AlignCenter)
        mic_layout.addWidget(self.record_status, 0, Qt.AlignCenter)
        self.mic_container.setVisible(False)

        layout = QVBoxLayout()
        layout.addWidget(self.textarea, 1)
        layout.addWidget(self.mic_container, 0)
        self.help_label.hide()
        layout.setContentsMargins(15, 0, 15, 0)
        layout.setSpacing(0)
        self.setLayout(layout)
        self.setProperty('class', 'layout-notepad')

    def set_tab(self, tab: Tab):
        """
        Set tab

        :param tab: Tab
        """
        self.tab = tab
        self.textarea.set_tab(tab)


    def toggle_microphone(self):
        """Toggle simple microphone recording from the Notepad tab."""
        try:
            if not self.window.controller.audio.is_recording():
                self.window.controller.audio.ui.on_input_toggle_requested("input", notepad=self)
        except Exception:
            pass
        self.window.dispatch(Event(Event.AUDIO_INPUT_RECORD_TOGGLE))

    def set_mic_visible(self, visible: bool):
        """Show/hide the dedicated Notepad microphone including its margins."""
        self.mic_container.setVisible(bool(visible))

    def set_mic_state(self, active: bool):
        """Mirror the recording icon/tooltip used by ChatInput."""
        if active:
            self.mic_button.setIcon(QIcon(':/icons/mic_off.svg'))
            self.mic_button.setToolTip(trans('audio.speak.btn.stop.tooltip'))
        else:
            self.mic_button.setIcon(QIcon(':/icons/mic.svg'))
            self.mic_button.setToolTip(trans('audio.note.btn.tooltip'))

    def set_record_pending(self):
        """Show the compact recording-pending state in the Notepad row."""
        self.record_status.show_pending()

    def set_recording_active(self):
        """Show the full input record meter in the Notepad row."""
        self.record_status.show_recording()

    def set_record_level(self, level: int):
        """Update the Notepad input meter level."""
        self.record_status.setLevel(level)

    def reset_recording_ui(self):
        """Hide the Notepad recording status widgets."""
        self.record_status.reset()

    def setText(self, text: str):
        """
        Set text

        :param text: Text
        """
        self.textarea.setText(text)
        self.textarea.on_update()

    def toPlainText(self) -> str:
        """
        Get plain text

        :return: Plain text
        """
        return self.textarea.toPlainText()


    def on_delete(self):
        """On delete"""
        self.session.close()
        self.tab = None  # clear tab reference
        self.deleteLater()

