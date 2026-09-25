#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import ssl
import time
from urllib.request import Request, urlopen

from pygpt_net.core.auto_updater.base import UpdateContext, UpdateError


class Downloader:
    CHUNK_SIZE = 256 * 1024

    def __init__(self, context: UpdateContext):
        self.context = context

    def download(self, url: str, target: str, status: str) -> str:
        if not url:
            raise UpdateError("Missing update download URL")

        os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
        tmp = target + ".part"
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass

        ctx = ssl.create_default_context()
        request = Request(url, headers={"User-Agent": "PyGPT Auto Updater"})
        started = time.monotonic()
        last_time = started
        last_bytes = 0
        speed = 0.0

        try:
            with urlopen(request, context=ctx, timeout=30) as response, open(tmp, "wb") as output:
                raw_total = response.headers.get("Content-Length", "")
                try:
                    total = int(raw_total)
                except (TypeError, ValueError):
                    total = 0

                received = 0
                self.context.progress(status, 0 if total else None, received, total, 0.0, None)
                while True:
                    self.context.check_cancelled()
                    chunk = response.read(self.CHUNK_SIZE)
                    if not chunk:
                        break
                    output.write(chunk)
                    received += len(chunk)

                    now = time.monotonic()
                    elapsed = max(now - last_time, 1e-6)
                    if elapsed >= 0.35:
                        instant = (received - last_bytes) / elapsed
                        speed = instant if speed <= 0 else speed * 0.72 + instant * 0.28
                        last_time = now
                        last_bytes = received

                    percent = int(min(100, received * 100 / total)) if total else None
                    eta = ((total - received) / speed) if total and speed > 1 else None
                    self.context.progress(status, percent, received, total, speed, eta)

            if total and received != total:
                raise UpdateError(f"Incomplete download: {received} of {total} bytes")
            os.replace(tmp, target)
            duration = max(time.monotonic() - started, 1e-6)
            final_speed = received / duration
            self.context.progress(status, 100, received, total or received, final_speed, 0.0)
            return target
        except Exception:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except OSError:
                pass
            raise
