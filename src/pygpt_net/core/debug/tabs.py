#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.14 20:00:00                  #
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
        debug = self.window.core.debug
        tabs_controller = self.window.controller.ui.tabs
        tabs_core = self.window.core.tabs
        ctx_output = self.window.core.ctx.output
        ctx_container = self.window.core.ctx.container

        debug.begin(self.id)
        debug.add(self.id, 'current Col', str(tabs_controller.get_current_column_idx()))
        debug.add(self.id, 'current IDX', str(tabs_controller.get_current_idx()))
        debug.add(self.id, 'current Tab', str(tabs_controller.get_current_tab()))
        debug.add(self.id, 'current PID', str(tabs_controller.get_current_pid()))
        debug.add(self.id, 'current Type', str(tabs_controller.get_current_type()))
        debug.add(self.id, '----', '')
        debug.add(self.id, 'last_pid', str(tabs_core.last_pid))
        debug.add(self.id, 'locked', str(tabs_controller.locked))
        debug.add(self.id, 'col', str(tabs_controller.col))
        debug.add(self.id, 'count(pids)', str(len(tabs_core.pids)))
        debug.add(self.id, 'count(ctx bags)', str(len(ctx_container.bags)))
        debug.add(self.id, '----', '')

        # PIDs
        for pid in list(tabs_core.pids):
            tab = tabs_core.pids[pid]
            data = tab.to_dict()
            debug.add(self.id, f"PID [{pid}]", str(data))

        # mapping PID => meta.id
        debug.add(self.id, '----', '')
        debug.add(self.id, 'PID => meta.id', str(ctx_output.mapping))
        debug.add(self.id, '(last) meta.id => PID', str(ctx_output.last_pids))
        debug.add(self.id, '(last) PID', str(ctx_output.last_pid))
        debug.end(self.id)
