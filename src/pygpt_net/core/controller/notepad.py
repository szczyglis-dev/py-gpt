#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.18 14:00:00                  #
# ================================================== #

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
        if data is None:
            data = {}
            data['1'] = ""
            data['2'] = ""
            data['3'] = ""
            data['4'] = ""
            data['5'] = ""

        if '1' not in data:
            data['1'] = ""
        self.window.ui.nodes['notepad1'].setText(data['1'])

        if '2' not in data:
            data['2'] = ""
        self.window.ui.nodes['notepad2'].setText(data['2'])

        if '3' not in data:
            data['3'] = ""
        self.window.ui.nodes['notepad3'].setText(data['3'])

        if '4' not in data:
            data['4'] = ""
        self.window.ui.nodes['notepad3'].setText(data['4'])

        if '5' not in data:
            data['5'] = ""
        self.window.ui.nodes['notepad3'].setText(data['5'])

    def save(self):
        """
        Save notepad contents
        """
        data = {}
        data['1'] = self.window.ui.nodes['notepad1'].toPlainText()
        data['2'] = self.window.ui.nodes['notepad2'].toPlainText()
        data['3'] = self.window.ui.nodes['notepad3'].toPlainText()
        data['4'] = self.window.ui.nodes['notepad4'].toPlainText()
        data['5'] = self.window.ui.nodes['notepad5'].toPlainText()
        self.window.app.notepad.save(data)
        self.update()

    def setup(self):
        """Setup notepad"""
        # send clear
        self.load()

    def update(self):
        """Update notepad"""
        pass
