#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.12 00:00:00                  #
# ================================================== #

from pygpt_net.ui.widget.lists.base_list_combo_separator import BaseListComboSeparator


class ModelCombo(BaseListComboSeparator):
    def __init__(self, window=None, id=None):
        """
        Model select menu

        :param window: main window
        :param id: input id
        """
        super(ModelCombo, self).__init__(window, id)

    def on_combo_change(self, index):
        """
        On combo change

        :param index: combo index
        """
        if not self.initialized or self.locked:
            return
        self.current_id = self.combo.itemData(index)
        self.window.controller.model.select(self.current_id)
