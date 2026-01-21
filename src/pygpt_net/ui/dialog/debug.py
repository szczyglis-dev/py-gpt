#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.21 01:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt, QEvent, QTimer, QObject
from PySide6.QtWidgets import QScrollArea, QSplitter, QSplitterHandle, QPushButton, \
    QCheckBox, QHBoxLayout, QAbstractItemView, QLabel, QVBoxLayout

from pygpt_net.ui.widget.dialog.debug import DebugDialog
from pygpt_net.ui.widget.lists.debug import DebugList
from pygpt_net.ui.widget.textarea.editor import CodeEditor


class SmoothSplitterHandle(QSplitterHandle):
    """
    Splitter handle that notifies the parent splitter about drag begin/end.
    This allows the splitter to temporarily freeze heavy widgets during drag.
    """
    def __init__(self, orientation, parent):
        super().__init__(orientation, parent)
        self._drag_active = False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_active = True
            sp = self.splitter()
            if hasattr(sp, "_on_drag_begin"):
                sp._on_drag_begin()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if self._drag_active:
            sp = self.splitter()
            if hasattr(sp, "_on_drag_end"):
                sp._on_drag_end()
            self._drag_active = False


class SmoothSplitter(QSplitter):
    """
    Splitter optimized for heavy child widgets:
    - Uses non-opaque resize to avoid continuous relayout during drag.
    - Freezes updates on registered heavy widgets while dragging.
    """
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self._heavy_widgets = []
        self.setOpaqueResize(False)            # rubber-band; resize applied on release
        self.setChildrenCollapsible(False)     # keep both panes visible

    def createHandle(self):
        return SmoothSplitterHandle(self.orientation(), self)

    def add_heavy_widget(self, w):
        if w and w not in self._heavy_widgets:
            self._heavy_widgets.append(w)

    def _on_drag_begin(self):
        for w in self._heavy_widgets:
            try:
                w.setUpdatesEnabled(False)
            except Exception:
                pass

    def _on_drag_end(self):
        for w in self._heavy_widgets:
            try:
                w.setUpdatesEnabled(True)
                w.update()
            except Exception:
                pass


class ResizeFreezeFilter(QObject):
    """
    Event filter that throttles expensive repaints during parent widget resize.
    Freezes updates for registered heavy widgets while the resize is in progress,
    and restores them shortly after the last resize event.
    """
    def __init__(self, heavy_widgets, parent=None, defer_ms=120):
        super().__init__(parent)
        self._heavy_widgets = [w for w in heavy_widgets if w is not None]
        self._defer_ms = defer_ms
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._unfreeze)
        self._frozen = False
        self._saved_view_update_modes = {}

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Resize:
            self._freeze()
            self._timer.start(self._defer_ms)
        return False

    def _freeze(self):
        if self._frozen:
            return
        self._frozen = True
        for w in self._heavy_widgets:
            try:
                if isinstance(w, QAbstractItemView):
                    self._saved_view_update_modes[w] = w.viewportUpdateMode()
                    w.setViewportUpdateMode(QAbstractItemView.NoViewportUpdate)
            except Exception:
                pass
            try:
                w.setUpdatesEnabled(False)
            except Exception:
                pass

    def _unfreeze(self):
        if not self._frozen:
            return
        self._frozen = False
        for w in self._heavy_widgets:
            try:
                w.setUpdatesEnabled(True)
            except Exception:
                pass
            try:
                if isinstance(w, QAbstractItemView) and w in self._saved_view_update_modes:
                    w.setViewportUpdateMode(self._saved_view_update_modes.pop(w))
            except Exception:
                pass
            try:
                w.update()
            except Exception:
                pass


class Debug:
    def __init__(self, window=None):
        """
        Debug setup

        :param window: Window instance
        """
        self.window = window

    def setup(self, id: str):
        """
        Setup debug dialog

        :param id: debug id
        """
        self.window.ui.debug[id] = DebugList(self.window)

        scroll = QScrollArea()
        scroll.setWidget(self.window.ui.debug[id])
        scroll.setWidgetResizable(True)

        # data viewer
        viewer = CodeEditor(self.window)
        viewer.setReadOnly(True)
        self.window.ui.debug[id].viewer = viewer

        # optimized splitter for heavy widgets
        splitter = SmoothSplitter(Qt.Horizontal)
        splitter.addWidget(scroll)
        splitter.addWidget(viewer)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        # register heavy widgets to freeze during drag
        splitter.add_heavy_widget(self.window.ui.debug[id])
        splitter.add_heavy_widget(self.window.ui.debug[id].viewport())
        splitter.add_heavy_widget(viewer)

        realtime_btn = QCheckBox("Realtime")
        realtime_btn.setChecked(False)
        realtime_btn.toggled.connect(
            lambda checked: self.window.controller.dialogs.debug.set_realtime(id, checked)
        )

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(
            lambda: self.window.controller.dialogs.debug.refresh(id)
        )

        last_update_label = QLabel("Last update: N/A")
        self.window.ui.debug[id].last_update_label = last_update_label

        opts_layout = QHBoxLayout()
        opts_layout.addWidget(realtime_btn)
        opts_layout.addStretch(1)
        opts_layout.addWidget(refresh_btn)
        opts_layout.addStretch(1)
        opts_layout.addWidget(last_update_label)

        layout = QVBoxLayout()
        layout.addWidget(splitter, 1)
        layout.addLayout(opts_layout, 0)
        layout.setContentsMargins(5, 5, 5, 5)

        self.window.ui.dialog['debug.' + id] = DebugDialog(self.window, id)
        self.window.ui.dialog['debug.' + id].setLayout(layout)
        self.window.ui.dialog['debug.' + id].setWindowTitle("Debug" + ": " + id)

        # throttle heavy repaints during dialog resize
        heavy_widgets = [
            self.window.ui.debug[id],
            getattr(self.window.ui.debug[id], "viewport", lambda: None)(),
            viewer,
            scroll,
            getattr(scroll, "viewport", lambda: None)(),
        ]
        resize_filter = ResizeFreezeFilter(heavy_widgets, parent=self.window.ui.dialog['debug.' + id], defer_ms=120)
        self.window.ui.dialog['debug.' + id].installEventFilter(resize_filter)
        splitter.installEventFilter(resize_filter)
        # keep a strong reference to avoid garbage collection
        self.window.ui.dialog['debug.' + id]._resize_freeze_filter = resize_filter