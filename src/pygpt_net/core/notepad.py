#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.23 22:00:00                  #
# ================================================== #
import datetime
import json
import os

from .provider.notepad.json_file import JsonFileProvider


class Notepad:
    def __init__(self, window=None):
        """
        Notepad

        :param window: Window instance
        """
        self.window = window
        self.providers = {}
        self.provider = "json_file"
        self.items = {}

        # register data providers
        self.add_provider(JsonFileProvider())  # json file provider

    def add_provider(self, provider):
        """
        Add data provider

        :param provider: data provider instance
        """
        self.providers[provider.id] = provider
        self.providers[provider.id].window = self.window

    def get_by_id(self, id):
        """
        Get notepad by id

        :param id: notepad id
        :return: notepad instance
        :rtype: NotepadItem
        """
        if id in self.items:
            return self.items[id]
        return None

    def get_all(self):
        """
        Get all notepads

        :return: notepads dict
        :rtype: dict
        """
        return self.items

    def update(self, notepad):
        """
        Update notepad

        :param notepad: notepad instance
        :return: True if success
        :rtype: bool
        """
        if notepad.id not in self.items:
            return False

        notepad.updated_at = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        self.items[notepad.id] = notepad
        self.save(notepad.id)
        return True

    def load(self, id):
        """
        Load notepad by id

        :param id: notepad id
        """
        if self.provider in self.providers:
            try:
                self.items[id] = self.providers[self.provider].load(id)
            except Exception as e:
                self.window.app.errors.log(e)

    def load_all(self):
        """Load all notepads"""
        if self.provider in self.providers:
            try:
                self.items = self.providers[self.provider].load_all()
            except Exception as e:
                self.window.app.errors.log(e)

    def save(self, id):
        """
        Save notepad

        :param id: notepad id
        :return: True if saved, False if not
        :rtype: bool
        """
        if id not in self.items:
            return False

        if self.provider in self.providers:
            try:
                self.providers[self.provider].save(self.items[id])
                return True
            except Exception as e:
                self.window.app.errors.log(e)
        return False

    def save_all(self):
        """
        Save all notepads
        """
        if self.provider in self.providers:
            try:
                self.providers[self.provider].save_all(self.items)
            except Exception as e:
                self.window.app.errors.log(e)
