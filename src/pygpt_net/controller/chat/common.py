#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.28 12:00:00                  #
# ================================================== #

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QFileDialog

from pygpt_net.core.dispatcher import Event
from pygpt_net.utils import trans


class Common:
    def __init__(self, window=None):
        """
        Chat common controller

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Set up UI"""
        # stream mode
        if self.window.core.config.get('stream'):
            self.window.ui.nodes['input.stream'].setChecked(True)
        else:
            self.window.ui.nodes['input.stream'].setChecked(False)

        # send clear
        if self.window.core.config.get('send_clear'):
            self.window.ui.nodes['input.send_clear'].setChecked(True)
        else:
            self.window.ui.nodes['input.send_clear'].setChecked(False)

        # send with enter/shift/disabled
        mode = self.window.core.config.get('send_mode')
        if mode == 2:
            self.window.ui.nodes['input.send_shift_enter'].setChecked(True)
            self.window.ui.nodes['input.send_enter'].setChecked(False)
            self.window.ui.nodes['input.send_none'].setChecked(False)
        elif mode == 1:
            self.window.ui.nodes['input.send_enter'].setChecked(True)
            self.window.ui.nodes['input.send_shift_enter'].setChecked(False)
            self.window.ui.nodes['input.send_none'].setChecked(False)
        elif mode == 0:
            self.window.ui.nodes['input.send_enter'].setChecked(False)
            self.window.ui.nodes['input.send_shift_enter'].setChecked(False)
            self.window.ui.nodes['input.send_none'].setChecked(True)

        # cmd enabled
        if self.window.core.config.get('cmd'):
            self.window.ui.nodes['cmd.enabled'].setChecked(True)
        else:
            self.window.ui.nodes['cmd.enabled'].setChecked(False)

        # output timestamps
        self.window.ui.nodes['output.timestamp'].setChecked(self.window.core.config.get('output_timestamp'))

        # raw (plain) output
        self.window.ui.nodes['output.raw'].setChecked(self.window.core.config.get('render.plain'))

        # images generation
        if self.window.core.config.get('img_raw'):
            self.window.ui.config['global']['img_raw'].setChecked(True)
        else:
            self.window.ui.config['global']['img_raw'].setChecked(False)

        # set focus to input
        self.window.ui.nodes['input'].setFocus()

    def append_to_input(self, text: str):
        """
        Append text to input

        :param text: text to append
        """
        prev_text = self.window.ui.nodes['input'].toPlainText()
        cur = self.window.ui.nodes['input'].textCursor()
        cur.movePosition(QTextCursor.End)
        text = str(text).strip()
        if prev_text.strip() != "":
            text = "\n" + text
        s = text
        while s:
            head, sep, s = s.partition("\n")  # Split line at LF
            cur.insertText(head)  # Insert text at cursor
            if sep:  # New line if LF
                cur.insertBlock()
        cur.movePosition(QTextCursor.End)  # Move cursor to end of text
        self.window.ui.nodes['input'].setTextCursor(cur)  # Update visible cursor
        self.window.ui.nodes['input'].setFocus()  # Set focus to input

        # update tokens counter
        self.window.controller.ui.update_tokens()

    def toggle_stream(self, value: bool):
        """
        Toggle stream

        :param value: value of the checkbox
        """
        self.window.core.config.set('stream', value)

    def toggle_cmd(self, value: bool):
        """
        Toggle cmd enabled

        :param value: value of the checkbox
        """
        self.window.core.config.set('cmd', value)

        # stop commands thread if running
        if not value:
            self.window.controller.command.stop = True
        else:
            self.window.controller.command.stop = False

        self.window.controller.ui.update_tokens()  # update tokens counters

    def toggle_send_clear(self, value: bool):
        """
        Toggle send clear

        :param value: value of the checkbox
        """
        self.window.core.config.set('send_clear', value)

    def toggle_send_shift(self, value: bool):
        """
        Toggle send with shift

        :param value: value of the checkbox
        """
        self.window.core.config.set('send_mode', value)

    def focus_input(self):
        """Focus input"""
        self.window.ui.nodes['input'].setFocus()

    def lock_input(self):
        """Lock input"""
        self.window.controller.chat.input.locked = True
        self.window.ui.nodes['input.send_btn'].setEnabled(False)
        self.window.ui.nodes['input.stop_btn'].setVisible(True)

    def unlock_input(self):
        """Unlock input"""
        self.window.controller.chat.input.locked = False
        self.window.ui.nodes['input.send_btn'].setEnabled(True)
        self.window.ui.nodes['input.stop_btn'].setVisible(False)

    def stop(self):
        """Stop input"""
        event = Event(Event.FORCE_STOP, {
            "value": True,
        })
        self.window.core.dispatcher.dispatch(event)  # stop event
        event = Event(Event.AUDIO_INPUT_TOGGLE, {
            "value": False,
        })
        self.window.controller.assistant.threads.stop = True
        self.window.core.dispatcher.dispatch(event)  # stop audio input
        self.window.controller.chat.input.stop = True
        self.window.core.gpt.stop()
        self.unlock_input()
        self.window.controller.chat.input.generating = False
        self.window.ui.status(trans('status.stopped'))

    def check_api_key(self) -> bool:
        """
        Check if API KEY is set

        :return: True if API KEY is set, False otherwise
        """
        result = True
        if self.window.core.config.get('api_key') is None or self.window.core.config.get('api_key') == '':
            self.window.controller.launcher.show_api_monit()
            self.window.ui.status("Missing API KEY!")
            result = False
        return result

    def toggle_timestamp(self, value: bool):
        """
        Toggle timestamp

        :param value: value of the checkbox
        """
        self.window.core.config.set('output_timestamp', value)
        self.window.core.config.save()
        self.window.controller.ctx.refresh()

    def toggle_raw(self, value: bool):
        """
        Toggle raw (plain) output

        :param value: value of the checkbox
        """
        self.window.core.config.set('render.plain', value)
        self.window.core.config.save()

        # update checkbox in settings dialog
        self.window.controller.config.checkbox.apply(
            'config',
            'render.plain',
            {'value': value},
        )
        if not value:
            self.window.controller.theme.markdown.update(force=True)  # with state store
        else:
            self.window.controller.theme.markdown.clear()

        # restore previous font size
        self.window.controller.ui.update_font_size()

    def img_enable_raw(self):
        """Enable help for images"""
        self.window.core.config.set('img_raw', True)
        self.window.core.config.save()

    def img_disable_raw(self):
        """Disable help for images"""
        self.window.core.config.set('img_raw', False)
        self.window.core.config.save()

    def img_toggle_raw(self, state: bool):
        """
        Toggle help for images

        :param state: state of checkbox
        """
        if not state:
            self.img_disable_raw()
        else:
            self.img_enable_raw()

    def save_text(self, text: str):
        """
        Save text to file

        :param text: text to save
        """
        # first, open save dialog to select file
        file_name = QFileDialog.getSaveFileName(
            self.window,
            "Save as text file",
            self.window.core.config.get_user_dir('data'),
            "*",
        )[0]
        if file_name:
            # save file
            with open(file_name, 'w') as f:
                f.write(text)
                self.window.ui.status(trans('status.saved'))

