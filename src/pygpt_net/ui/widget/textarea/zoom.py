#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.04 00:00:00                  #
# ================================================== #
"""Immediate local zoom with one shared settings commit after a wheel gesture."""
import re
import weakref
from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QApplication


class ZoomCommit(QObject):
    def __init__(self, window):
        super().__init__(window if isinstance(window, QObject) else QApplication.instance())
        self.window = window
        self.pending = set()
        self.values = {}
        self.editors = weakref.WeakKeyDictionary()
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(250)
        self.timer.timeout.connect(self.flush)
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.flush)

    def schedule(self, key):
        self.pending.add(key)
        self.timer.start()

    def flush(self):
        if not self.pending:
            return
        keys, self.pending = self.pending, set()
        values, self.values = self.values, {}
        window = self.window
        window.core.config.save()
        for key in keys:
            option = window.controller.settings.editor.get_option(key)
            if option is not None:
                option['value'] = values.get(key, window.core.config.get(key))
        # Font changes must not emit ON_THEME_CHANGE and reload the web renderer.
        for editor, key in list(self.editors.items()):
            if key in keys:
                try:
                    value = values.get(key, window.core.config.get(key))
                    if editor.isVisible():
                        editor.apply_zoom(value)
                    else:
                        editor.value = value  # Restore layout lazily in showEvent.
                except RuntimeError:
                    pass  # Qt may already have deleted a closed frontend.
        if keys - {'zoom', 'terminal.font_size', 'font_size', 'filesystem.preview.text.font_size'}:
            window.controller.theme.nodes.apply_all(dispatch_theme=False)
        if 'zoom' in keys:
            container = window.ui.nodes.get('input.container')
            if container is not None:
                container.sync_width()


def schedule_zoom(window, key, value):
    window.core.config.set(key, value)
    commit = zoom_commit(window)
    commit.values[key] = value
    commit.schedule(key)


def zoom_commit(window):
    commit = vars(window).get('_text_zoom_commit')
    if commit is None:
        commit = ZoomCommit(window)
        window._text_zoom_commit = commit
    return commit


def register_editor_zoom(widget, window, key):
    zoom_commit(window).editors[widget] = key


def queue_editor_zoom(widget, window, value, key):
    register_editor_zoom(widget, window, key)
    widget.value = max(8, min(42, int(value)))
    if not widget.zoom_timer.isActive():
        widget.zoom_timer.start()
    schedule_zoom(window, key, widget.value)


def local_font(widget, value):
    """Keep the editor's colors and other local styles intact."""
    style = widget.styleSheet()
    rule = f'font-size: {value}px'
    if re.search(r'font-size\s*:', style):
        style = re.sub(r'font-size\s*:\s*[^;}]+', rule, style)
    else:
        style += f'\nQTextEdit, QPlainTextEdit {{ {rule}; }}'
    if style != widget.styleSheet():
        widget.setStyleSheet(style)


def zoom_text(widget, window, value, key='font_size'):
    value = max(8, min(42, int(value)))
    widget.value = value
    local_font(widget, value)
    schedule_zoom(window, key, value)
