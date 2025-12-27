#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.12.27 02:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QHBoxLayout, QWidget, QComboBox
from PySide6.QtCore import QSignalBlocker

from pygpt_net.ui.widget.option.combo import SeparatorComboBox, NoScrollCombo


class BaseListCombo(QWidget):
    def __init__(self, window=None, id: str = None):
        """
        Base list combo

        :param window: main window
        :param id: option id
        """
        super(BaseListCombo, self).__init__(window)
        self.window = window
        self.id = id
        self.current_id = None
        self.keys = []
        self.real_time = False
        self.combo = NoScrollCombo(parent=self.window)
        self.combo.currentIndexChanged.connect(self.on_combo_change)
        self.initialized = False
        self.locked = False
        self._data_index_map = {}
        self._keys_cache = None
        self._keys_cache_id = 0

        self.update()

        self.layout = QHBoxLayout()
        self.layout.addWidget(self.combo)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)
        self.fit_to_content()
        self.initialized = True

    def update(self):
        """Prepare items"""
        combo = self.combo
        blocker = QSignalBlocker(combo)
        combo.setUpdatesEnabled(False)
        try:
            combo.clear()
            self._data_index_map = {}
            idx = 0
            keys = self.keys
            add_item = combo.addItem
            if isinstance(keys, list):
                for item in keys:
                    if isinstance(item, dict):
                        for key, value in item.items():
                            add_item(value, key)
                            if key not in self._data_index_map:
                                self._data_index_map[key] = idx
                            idx += 1
                    else:
                        add_item(item, item)
                        if item not in self._data_index_map:
                            self._data_index_map[item] = idx
                        idx += 1
            elif isinstance(keys, dict):
                add_sep = combo.addSeparator
                for key, value in keys.items():
                    if isinstance(key, str) and key.startswith("separator::"):
                        add_sep(value)
                        idx += 1
                    else:
                        add_item(value, key)
                        if key not in self._data_index_map:
                            self._data_index_map[key] = idx
                        idx += 1
            cache = set()
            if isinstance(keys, list):
                for item in keys:
                    if isinstance(item, dict):
                        cache.update(item.keys())
                    else:
                        cache.add(item)
            elif isinstance(keys, dict):
                cache.update(keys.keys())
            self._keys_cache = cache
            self._keys_cache_id = id(keys)
        finally:
            combo.setUpdatesEnabled(True)
            del blocker

    def set_value(self, value):
        """
        Set value

        :param value: value
        """
        self.locked = True
        combo = self.combo
        blocker = QSignalBlocker(combo)
        try:
            index = self._data_index_map.get(value, -1)
            if index == -1:
                index = combo.findData(value)
                if index != -1 and value not in self._data_index_map:
                    self._data_index_map[value] = index
            if index != -1:
                if index != combo.currentIndex():
                    combo.setCurrentIndex(index)
                self.current_id = value
        finally:
            del blocker
            self.locked = False

    def get_value(self):
        """
        Get value

        :return: value
        """
        return self.current_id

    def has_key(self, name: str) -> bool:
        """
        Check if combo has key

        :param name: key name
        :return:
        """
        keys = self.keys
        if self._keys_cache is None or self._keys_cache_id != id(keys):
            cache = set()
            if isinstance(keys, list):
                for item in keys:
                    if isinstance(item, dict):
                        cache.update(item.keys())
                    else:
                        cache.add(item)
            elif isinstance(keys, dict):
                cache.update(keys.keys())
            self._keys_cache = cache
            self._keys_cache_id = id(keys)
        return name in self._keys_cache

    def set_keys(self, keys):
        """
        Set keys

        :param keys: keys
        """
        self.locked = True
        self.keys = keys
        self._keys_cache = None
        self._keys_cache_id = 0
        self.update()
        self.locked = False

    def on_combo_change(self, index):
        """
        On combo change

        :param index: combo index
        """
        if not self.initialized or self.locked:
            return
        self.current_id = self.combo.itemData(index) if index >= 0 else None

    def fit_to_content(self):
        """Fit to content"""
        self.combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)