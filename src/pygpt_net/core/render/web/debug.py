#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.07 05:00:00                  #
# ================================================== #

def hsize(n: int) -> str:
    """Human-readable byte size."""
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if abs(n) < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024.0
    return f"{n:.0f} PB"


def safe_sizeof(obj) -> int:
    """sys.getsizeof wrapper that never raises and never copies large buffers."""
    import sys
    try:
        return sys.getsizeof(obj)
    except Exception:
        return 0


def deep_size_lite(obj, seen: set | None = None) -> int:
    """
    Conservative deep size estimator:
    - Traverses only common containers and dataclass/__dict__/__slots__.
    - Avoids copying buffers (never calls getvalue() on StringIO).
    """
    from io import StringIO
    if seen is None:
        seen = set()
    oid = id(obj)
    if oid in seen:
        return 0
    seen.add(oid)

    size = safe_sizeof(obj)

    if obj is None:
        return size

    # Avoid copying StringIO content; rely on external tracked counters if any.
    if isinstance(obj, StringIO):
        return size  # StringIO object overhead; actual content accounted separately by our counters

    if isinstance(obj, dict):
        for k, v in obj.items():
            size += deep_size_lite(k, seen)
            size += deep_size_lite(v, seen)
        return size

    if isinstance(obj, (list, tuple, set, frozenset)):
        for it in obj:
            size += deep_size_lite(it, seen)
        return size

    # user objects
    if hasattr(obj, "__dict__"):
        size += deep_size_lite(obj.__dict__, seen)
    elif hasattr(obj, "__slots__"):
        for s in obj.__slots__:
            try:
                size += deep_size_lite(getattr(obj, s), seen)
            except Exception:
                pass

    return size


def pid_mem_snapshot(pctx, thr) -> dict:
    """
    Return a conservative per-pid memory snapshot (Python side only).
    """
    pid = getattr(pctx, "pid", None) if pctx else None
    snap = {
        "pid": pid,
        "exists": False,
        "pctx": {},
        "thr": {},
        "totals": {"python_estimate_bytes": 0},
    }
    if pctx is None:
        return snap
    snap["exists"] = True

    # PidData fields;
    buf = getattr(pctx, "buffer", "")
    live = getattr(pctx, "live_buffer", "")
    html = getattr(pctx, "html", "")
    header = getattr(pctx, "header", "")
    images = getattr(pctx, "images_appended", [])
    urls = getattr(pctx, "urls_appended", [])
    files = getattr(pctx, "files_appended", [])

    pctx_bytes = {
        "buffer_bytes": safe_sizeof(buf),
        "live_buffer_bytes": safe_sizeof(live),
        "html_bytes": safe_sizeof(html),
        "header_bytes": safe_sizeof(header),
        "images_list_bytes": deep_size_lite(images),
        "urls_list_bytes": deep_size_lite(urls),
        "files_list_bytes": deep_size_lite(files),
    }
    pctx_bytes["sum"] = sum(pctx_bytes.values())
    snap["pctx"] = pctx_bytes

    # Throttle state
    thr = thr.get(pid, None)
    thr_bytes = {
        "has_thr": thr is not None,
        "append_buffer_pending_bytes": 0,
        "replace_html_bytes": 0,
        "op": None,
    }
    if thr is not None:
        thr_bytes["op"] = thr.get("op")
        thr_bytes["append_buffer_pending_bytes"] = getattr(thr.get("append"), "_size", 0) or 0
        # Never trust replace_html here; we try to keep it empty to avoid duplication
        rh = thr.get("replace_html", "")
        thr_bytes["replace_html_bytes"] = safe_sizeof(rh)
    snap["thr"] = thr_bytes

    snap["totals"]["python_estimate_bytes"] = pctx_bytes["sum"] + thr_bytes["append_buffer_pending_bytes"] + \
                                              thr_bytes["replace_html_bytes"]
    return snap


def pid_mem_snapshot_human(pid: int) -> str:
    """Human-readable summary for quick logging."""
    s = pid_mem_snapshot(pid)
    if not s["exists"]:
        return f"PID {pid}: not found"
    p = s["pctx"]
    t = s["thr"]
    tot = s["totals"]["python_estimate_bytes"]
    lines = [
        f"PID {pid} memory snapshot:",
        f"  pctx.buffer:        {hsize(p['buffer_bytes'])}",
        f"  pctx.live_buffer:   {hsize(p['live_buffer_bytes'])}",
        f"  pctx.html:          {hsize(p['html_bytes'])}",
        f"  pctx.header:        {hsize(p['header_bytes'])}",
        f"  pctx.images_list:   {hsize(p['images_list_bytes'])}",
        f"  pctx.urls_list:     {hsize(p['urls_list_bytes'])}",
        f"  pctx.files_list:    {hsize(p['files_list_bytes'])}",
        f"  thr.op:             {t['op']}",
        f"  thr.append_pending: {hsize(t['append_buffer_pending_bytes'])}",
        f"  thr.replace_html:   {hsize(t['replace_html_bytes'])}",
        f"  TOTAL (Python est): {hsize(tot)}",
    ]
    return "\n".join(lines)


def tracemalloc_top(limit: int = 10):
    """
    Print top allocation stats filtered to renderer/parser for quick diagnosis.
    """
    import tracemalloc
    if not tracemalloc.is_tracing():
        print("tracemalloc is not started. Call tracemalloc.start(25) first.")
        return
    snap = tracemalloc.take_snapshot()
    stats = snap.filter_traces((
        tracemalloc.Filter(True, "*renderer.py"),
        tracemalloc.Filter(True, "*parser.py"),
    )).statistics('lineno')
    print("Top allocations (renderer/parser):")
    for s in stats[:limit]:
        print(s)


def malloc_trim_linux():
    """Ask glibc to return free arenas to OS (Linux only)."""
    try:
        import sys, ctypes
        if sys.platform.startswith("linux"):
            libc = ctypes.CDLL("libc.so.6")
            libc.malloc_trim(0)
    except Exception:
        pass


def dbg_count_qt(needle="QWebEngine"):
    import gc
    from collections import Counter
    cnt = Counter(type(o).__name__ for o in gc.get_objects() if needle in type(o).__name__)
    print(f"[QT COUNT] {needle} =>", dict(cnt))

def log_rss_mb(note=""):
    try:
        import os, psutil
        rss = psutil.Process(os.getpid()).memory_info().rss
        print(f"[RSS] {note} {rss / 1024 / 1024:.1f} MB")
    except Exception:
        pass

def parse_bytes(val) -> int:
    # accepts: int/float (bytes), "2GB", "2048 MB", "1_000_000", etc.
    if isinstance(val, (int, float)):
        return int(val)
    s = str(val).strip().replace(" ", "").replace("_", "").upper()
    units = {"B": 1, "KB": 1024, "MB": 1024 ** 2, "GB": 1024 ** 3, "TB": 1024 ** 4}
    for u in ("TB", "GB", "MB", "KB", "B"):
        if s.endswith(u):
            num = s[:-len(u)] or "0"
            return int(float(num) * units[u])
    return int(float(s))

def mem_used_bytes() -> int:
    import os, psutil
    return psutil.Process(os.getpid()).memory_info().rss  # bytes (RSS)