#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.02 00:00:00                  #
# ================================================== #

"""Mutable per-renderer session state shared by delivery and presentation.

Each Renderer owns one instance; PID-keyed state is never global.
"""

from PySide6.QtCore import QTimer
from pygpt_net.item.ctx import CtxItem, CtxMeta
from .buffer import AppendBuffer
from ..pid import PidData


class RenderState:
    # ========================================
    # Initialization
    # ========================================

    def __init__(self, config):
        def _cfg(name, default):
            try:
                return int(config.get(name, default) if config else default)
            except Exception:
                return default

        self.pids: dict[int, PidData] = {}
        self.prev_chunk_replace = False
        self.prev_chunk_newline = False

        # Bridge readiness and delayed node delivery.
        self.bridge_ready: dict[int, bool] = {}
        self.pending_nodes: dict[int, list[tuple[bool, str]]] = {}  # (replace, payload)
        self.pending_timer: dict[int, QTimer] = {}

        # Streaming thresholds and transport ordering barriers.
        self.stream_interval_ms: int = _cfg('render.stream.interval_ms', 30)
        self.stream_max_bytes: int = _cfg('render.stream.max_bytes', 8 * 1024)
        self.stream_emergency_bytes: int = _cfg('render.stream.emergency_bytes', 512 * 1024)
        self.stream_acc: dict[int, AppendBuffer] = {}
        self.stream_timer: dict[int, QTimer] = {}
        self.stream_header: dict[int, str] = {}
        self.stream_owner_id: dict[int, str] = {}
        self.stream_last_flush: dict[int, float] = {}
        self.stream_last_cleanup: float = 0.0

        # Only the latest executed beginStream callback releases buffered text.
        self.stream_begin_seq: dict[int, int] = {}
        self.stream_begin_pending: set[int] = set()
        self.stream_end_pending: dict[int, tuple[CtxMeta, CtxItem]] = {}
        self.stream_session_ctx: dict[int, int] = {}

        # Inline partial streams: (PID, durable parent ID, partial key).
        self.partial_stream_acc: dict[tuple, AppendBuffer] = {}
        self.partial_stream_timer: dict[tuple, QTimer] = {}
        self.partial_stream_started: set[tuple] = set()

        # UI-only workflow records: never persisted as model output.
        self.workflow_statuses: dict[tuple, list[dict]] = {}
        self.workflow_status_seq: int = 0

        # Desired spinner state survives WebView reloads.
        self.loading_visible: dict[int, bool] = {}
        self.loading_reserved: dict[int, bool] = {}
        self.loading_show_options: dict[int, tuple[int, bool]] = {}
        self.reasoning_activity_state: dict[tuple, dict] = {}
