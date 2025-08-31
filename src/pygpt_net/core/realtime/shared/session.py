#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.31 23:00:00                  #
# ================================================== #

from typing import Optional
from pygpt_net.item.ctx import CtxItem

def set_ctx_rt_handle(ctx: Optional[CtxItem], handle: Optional[str], window=None):
    """Persist server session handle into ctx.extra['rt_session_id'] (best effort)."""
    try:
        if not ctx:
            return
        if not isinstance(ctx.extra, dict):
            ctx.extra = {}
        val = (handle or "").strip()
        if val:
            ctx.extra["rt_session_id"] = val
            if window:
                try:
                    window.core.ctx.update_item(ctx)
                except Exception:
                    pass
    except Exception:
        pass

def set_rt_session_expires_at(ctx: Optional[CtxItem], epoch_seconds: Optional[int], window=None):
    """Persist optional session expiration timestamp into ctx.extra."""
    if not ctx or epoch_seconds is None:
        return
    try:
        if not isinstance(ctx.extra, dict):
            ctx.extra = {}
        ctx.extra["rt_session_expires_at"] = int(epoch_seconds)
        if window:
            try:
                window.core.ctx.update_item(ctx)
            except Exception:
                pass
    except Exception:
        pass

def extract_last_session_id(items: list[CtxItem]) -> Optional[str]:
    """Extract last known session ID from a list of CtxItems."""
    if not items:
        return None
    for item in reversed(items):
        if not item or not isinstance(item.extra, dict):
            continue
        val = item.extra.get("rt_session_id")
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None