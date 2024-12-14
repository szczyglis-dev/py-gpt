#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 17:00:00                  #
# ================================================== #

class TabsDebug:
    def __init__(self, window=None):
        """
        Tabs debug

        :param window: Window instance
        """
        self.window = window
        self.id = 'tabs'

    def update(self):
        """Update debug window."""
        self.window.core.debug.begin(self.id)
        self.window.core.debug.add(self.id, 'current Col', str(self.window.controller.ui.tabs.get_current_column_idx()))
        self.window.core.debug.add(self.id, 'current IDX', str(self.window.controller.ui.tabs.get_current_idx()))
        self.window.core.debug.add(self.id, 'current Tab', str(self.window.controller.ui.tabs.get_current_tab()))
        self.window.core.debug.add(self.id, 'current PID', str(self.window.controller.ui.tabs.get_current_pid()))
        self.window.core.debug.add(self.id, 'current Type', str(self.window.controller.ui.tabs.get_current_type()))
        self.window.core.debug.add(self.id, '----', '')
        self.window.core.debug.add(self.id, 'last_pid', str(self.window.core.tabs.last_pid))
        self.window.core.debug.add(self.id, 'locked', str(self.window.controller.ui.tabs.locked))
        self.window.core.debug.add(self.id, 'col', str(self.window.controller.ui.tabs.col))
        self.window.core.debug.add(self.id, 'count(pids)', str(len(self.window.core.tabs.pids)))
        self.window.core.debug.add(self.id, 'count(ctx bags)', str(len(self.window.core.ctx.container.bags)))
        self.window.core.debug.add(self.id, '----', '')

        # PIDs
        for pid in list(self.window.core.tabs.pids):
            tab = self.window.core.tabs.pids[pid]
            data = tab.to_dict()
            self.window.core.debug.add(self.id, "PID ["+str(pid)+"]", str(data))

        # mapping PID => meta.id
        self.window.core.debug.add(self.id, '----', '')
        self.window.core.debug.add(self.id, 'PID => meta.id', str(self.window.core.ctx.output.mapping))
        self.window.core.debug.add(self.id, '(last) meta.id => PID', str(self.window.core.ctx.output.last_pids))
        self.window.core.debug.add(self.id, '(last) PID', str(self.window.core.ctx.output.last_pid))
        self.window.core.debug.end(self.id)
