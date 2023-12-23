#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.23 01:00:00                  #
# ================================================== #
import datetime


class Notepad:
    def __init__(self, window=None):
        """
        Notepad controller

        :param window: Window instance
        """
        self.window = window

    def load(self):
        """
        Load notepad contents
        """
        data = self.window.app.notepad.load()
        num_notepads = self.get_num_notepads()
        if data is None:
            data = {}
            if num_notepads > 0:
                for i in range(1, num_notepads + 1):
                    data[str(i)] = ""

        if num_notepads > 0:
            for i in range(1, num_notepads + 1):
                id = 'notepad' + str(i)
                if str(i) not in data:
                    data[str(i)] = ""
                if id in self.window.ui.nodes:
                    self.window.ui.nodes['notepad' + str(i)].setText(data[str(i)])

    def save(self):
        """
        Save notepad contents
        """
        data = {}
        num_notepads = self.get_num_notepads()
        if num_notepads > 0:
            for i in range(1, num_notepads + 1):
                id = 'notepad' + str(i)
                if id in self.window.ui.nodes:
                    data[str(i)] = self.window.ui.nodes[id].toPlainText()
            self.window.app.notepad.save(data)
            self.update()

    def setup(self):
        """Setup notepad"""
        # send clear
        self.load()

    def append_text(self, text, i):
        """
        Append text to notepad

        :param text: Text to append
        :param i: Notepad index
        """
        id = 'notepad' + str(i)
        if id not in self.window.ui.nodes:
            return
        dt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ":\n--------------------------\n"
        prev_text = self.window.ui.nodes['notepad' + str(i)].toPlainText()
        if prev_text != "":
            prev_text += "\n\n"
        new_text = prev_text + dt + text.strip()
        self.window.ui.nodes['notepad' + str(i)].setText(new_text)
        self.save()

    def get_num_notepads(self):
        """
        Get number of notepads

        :return: Number of notepads
        :rtype: int
        """
        return self.window.config.get('notepad.num') or 5

    def update(self):
        """Update notepad"""
        pass
