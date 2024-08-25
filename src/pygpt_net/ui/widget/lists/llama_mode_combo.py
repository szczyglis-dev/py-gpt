#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.25 04:00:00                  #
# ================================================== #

from .base_combo import BaseCombo

class LlamaModeCombo(BaseCombo):
    def __init__(self, window=None, parent_id: str = None, id: str = None, option: dict = None):
        """
        Llama index mode select combobox

        :param window: main window
        :param id: option id
        :param parent_id: parent option id
        :param option: option data
        """
        super(LlamaModeCombo, self).__init__(window, parent_id, id, option)

    def on_combo_change(self, index):
        """
        On combo change

        :param index: combo index
        """
        if not self.initialized:
            return
        self.current_id = self.combo.itemData(index)
        self.window.controller.idx.select_mode(self.current_id)
