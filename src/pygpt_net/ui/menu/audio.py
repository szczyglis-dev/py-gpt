#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.24 23:00:00                  #
# ================================================== #

from PySide6.QtGui import QAction, QIcon

from pygpt_net.utils import trans


class Audio:
    def __init__(self, window=None):
        """
        Menu setup

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup audio menu"""
        w = self.window
        m = w.ui.menu

        title = trans("menu.audio")
        txt_output = trans("menu.audio.output")
        txt_input = trans("menu.audio.input")
        txt_ctrl_plugin = trans("menu.audio.control.plugin")
        txt_ctrl_global = trans("menu.audio.control.global")
        txt_cache_clear = trans("menu.audio.cache.clear")
        txt_stop = trans("menu.audio.stop")

        icon_cache = QIcon(":/icons/delete.svg")
        icon_stop = QIcon(":/icons/mute.svg")

        plugins_toggle = w.controller.plugins.toggle
        voice_toggle = w.controller.access.voice.toggle_voice_control
        audio_clear = w.controller.audio.clear_cache
        audio_stop = w.controller.audio.stop_audio

        menu = m.get('menu.audio')
        is_new_menu = menu is None
        if is_new_menu:
            menu = w.menuBar().addMenu(title)
            m['menu.audio'] = menu
        else:
            menu.setTitle(title)

        act_output = m.get('audio.output')
        if act_output is None:
            act_output = QAction(txt_output, w, checkable=True)
            m['audio.output'] = act_output
            act_output.triggered.connect(lambda _=False: plugins_toggle('audio_output'))
        else:
            act_output.setText(txt_output)

        act_input = m.get('audio.input')
        if act_input is None:
            act_input = QAction(txt_input, w, checkable=True)
            m['audio.input'] = act_input
            act_input.triggered.connect(lambda _=False: plugins_toggle('audio_input'))
        else:
            act_input.setText(txt_input)

        act_ctrl_plugin = m.get('audio.control.plugin')
        if act_ctrl_plugin is None:
            act_ctrl_plugin = QAction(txt_ctrl_plugin, w, checkable=True)
            m['audio.control.plugin'] = act_ctrl_plugin
            act_ctrl_plugin.triggered.connect(lambda _=False: plugins_toggle('voice_control'))
        else:
            act_ctrl_plugin.setText(txt_ctrl_plugin)

        act_ctrl_global = m.get('audio.control.global')
        if act_ctrl_global is None:
            act_ctrl_global = QAction(txt_ctrl_global, w, checkable=True)
            m['audio.control.global'] = act_ctrl_global
            act_ctrl_global.triggered.connect(lambda _=False: voice_toggle())
        else:
            act_ctrl_global.setText(txt_ctrl_global)

        act_cache_clear = m.get('audio.cache.clear')
        if act_cache_clear is None:
            act_cache_clear = QAction(icon_cache, txt_cache_clear, w, checkable=False)
            m['audio.cache.clear'] = act_cache_clear
            act_cache_clear.triggered.connect(lambda _=False: audio_clear())
        else:
            act_cache_clear.setText(txt_cache_clear)
            act_cache_clear.setIcon(icon_cache)

        act_stop = m.get('audio.stop')
        if act_stop is None:
            act_stop = QAction(icon_stop, txt_stop, w, checkable=False)
            m['audio.stop'] = act_stop
            act_stop.triggered.connect(lambda _=False: audio_stop())
        else:
            act_stop.setText(txt_stop)
            act_stop.setIcon(icon_stop)

        if is_new_menu:
            menu.addAction(act_input)
            menu.addAction(act_output)
            menu.addSeparator()
            menu.addAction(act_ctrl_plugin)
            menu.addAction(act_ctrl_global)
            menu.addSeparator()
            menu.addAction(act_cache_clear)
            menu.addAction(act_stop)