#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.25 20:00:00                  #
# ================================================== #

from __future__ import annotations

import json
import os
import ssl
import time
from typing import Optional, Tuple
from urllib.parse import quote, urlsplit
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from pygpt_net.core.auto_updater import AUTO_UPDATER_GITHUB_API_BASE_URL, AUTO_UPDATER_GITHUB_HOSTS
from pygpt_net.core.auto_updater.base import UpdateContext, UpdateError


class Downloader:
    CHUNK_SIZE = 256 * 1024

    def __init__(self, context: UpdateContext):
        self.context = context

    @staticmethod
    def _github_release_asset(url: str) -> Optional[Tuple[str, str, str, str]]:
        """
        Parse a public GitHub Releases browser download URL.

        Returns: (owner, repo, tag, filename) or None.
        """
        try:
            parsed = urlsplit(url)
            if parsed.scheme not in ("http", "https"):
                return None
            if parsed.netloc.lower() not in AUTO_UPDATER_GITHUB_HOSTS:
                return None
            parts = [part for part in parsed.path.split("/") if part]
            if len(parts) < 6 or parts[2:4] != ["releases", "download"]:
                return None
            owner, repo, tag = parts[0], parts[1], parts[4]
            filename = "/".join(parts[5:])
            if not owner or not repo or not tag or not filename:
                return None
            return owner, repo, tag, filename
        except Exception:
            return None

    def _open_github_release_asset(self, url: str, ctx: ssl.SSLContext):
        """
        Resolve a GitHub release asset through GitHub's asset API.

        raw.githubusercontent.com cannot serve GitHub Release assets. The asset
        API returns a redirect to GitHub's binary CDN
        (release-assets.githubusercontent.com / objects.githubusercontent.com),
        which is the URL we want the updater to stream.
        """
        parsed = self._github_release_asset(url)
        if parsed is None:
            return None

        owner, repo, tag, filename = parsed
        api_url = (
            f"{AUTO_UPDATER_GITHUB_API_BASE_URL}/repos/{quote(owner)}/{quote(repo)}/"
            f"releases/tags/{quote(tag, safe='')}"
        )
        self.context.log(
            f"[download] Resolving GitHub release asset through API: "
            f"tag={tag!r}, filename={filename!r}."
        )
        meta_request = Request(
            api_url,
            headers={
                "User-Agent": "PyGPT-Auto-Updater",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        with urlopen(meta_request, context=ctx, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))

        asset = None
        for item in payload.get("assets", []):
            if item.get("name") == filename:
                asset = item
                break
        if asset is None:
            raise UpdateError(
                f"GitHub release asset not found: tag={tag}, filename={filename}"
            )

        asset_api_url = str(asset.get("url") or "")
        if not asset_api_url:
            raise UpdateError(
                f"GitHub release asset has no API download URL: {filename}"
            )

        asset_request = Request(
            asset_api_url,
            headers={
                "User-Agent": "PyGPT-Auto-Updater",
                "Accept": "application/octet-stream",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        response = urlopen(asset_request, context=ctx, timeout=30)
        self.context.log(
            f"[download] GitHub asset resolved to binary URL: {response.geturl()!r}."
        )
        return response

    def _open_response(self, url: str, ctx: ssl.SSLContext, binary: bool):
        headers = {
            "User-Agent": "Mozilla/5.0 (PyGPT Auto Updater)",
        }
        if binary:
            headers["Accept"] = "application/octet-stream"

        request = Request(url, headers=headers)
        try:
            response = urlopen(request, context=ctx, timeout=30)
        except HTTPError as exc:
            self.context.log(
                f"[download] HTTP error while opening URL: status={exc.code!r}, "
                f"url={url!r}."
            )
            # GitHub occasionally rejects browser-style release asset requests
            # with 406/other HTTP errors. For an exact releases/download URL,
            # resolve the same asset through GitHub's release asset API and let
            # GitHub redirect us to its binary CDN.
            if binary:
                github_response = self._open_github_release_asset(url, ctx)
                if github_response is not None:
                    content_type = (github_response.headers.get("Content-Type") or "").lower()
                    self.context.log(
                        f"[download] GitHub API fallback after HTTP {exc.code}: "
                        f"final_url={github_response.geturl()!r}, "
                        f"status={getattr(github_response, 'status', None)!r}, "
                        f"content_type={content_type!r}."
                    )
                    if "text/html" in content_type:
                        github_response.close()
                        raise UpdateError("GitHub returned HTML instead of the release asset")
                    return github_response
            raise
        final_url = response.geturl()
        content_type = (response.headers.get("Content-Type") or "").lower()
        self.context.log(
            f"[download] HTTP response resolved: input_url={url!r}, "
            f"final_url={final_url!r}, status={getattr(response, 'status', None)!r}, "
            f"content_type={content_type!r}."
        )

        # A GitHub Releases browser endpoint should redirect to GitHub's binary
        # CDN. If it instead returns a HTML page, do not save that page as an
        # AppImage. Resolve the exact release asset via GitHub's API and retry.
        if binary and "text/html" in content_type:
            response.close()
            github_response = self._open_github_release_asset(url, ctx)
            if github_response is not None:
                content_type = (github_response.headers.get("Content-Type") or "").lower()
                self.context.log(
                    f"[download] GitHub API fallback response: "
                    f"final_url={github_response.geturl()!r}, "
                    f"status={getattr(github_response, 'status', None)!r}, "
                    f"content_type={content_type!r}."
                )
                if "text/html" in content_type:
                    github_response.close()
                    raise UpdateError("GitHub returned HTML instead of the release asset")
                return github_response
            raise UpdateError("Download URL returned HTML instead of a binary file")

        return response

    def download(
            self,
            url: str,
            target: str,
            status: str,
            *,
            binary: bool = False,
            expected_magic: bytes = b"",
    ) -> str:
        if not url:
            raise UpdateError("Missing update download URL")

        target = os.path.abspath(target)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        tmp = target + ".part"
        self.context.log(
            f"[download] Starting download: url={url!r}, target={target!r}, "
            f"temporary={tmp!r}, chunk_size={self.CHUNK_SIZE}, binary={binary}."
        )
        try:
            if os.path.exists(tmp):
                self.context.log(f"[download] Removing stale partial file: {tmp!r}.")
                os.remove(tmp)
        except OSError as exc:
            self.context.log(f"[download] Unable to remove stale partial file {tmp!r}: {exc}")

        ctx = ssl.create_default_context()
        started = time.monotonic()
        last_time = started
        last_bytes = 0
        speed = 0.0

        try:
            self.context.log("[download] Opening HTTPS response.")
            response = self._open_response(url, ctx, binary)
            with response, open(tmp, "wb") as output:
                raw_total = response.headers.get("Content-Length", "")
                try:
                    total = int(raw_total)
                except (TypeError, ValueError):
                    total = 0
                self.context.log(
                    f"[download] Response opened: status={getattr(response, 'status', None)!r}, "
                    f"content_length={total or 'unknown'} bytes, final_url={response.geturl()!r}."
                )

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

            self.context.log(f"[download] Network stream completed: received={received}, expected={total}.")
            if total and received != total:
                raise UpdateError(f"Incomplete download: {received} of {total} bytes")

            if expected_magic:
                with open(tmp, "rb") as stream:
                    actual_magic = stream.read(len(expected_magic))
                if actual_magic != expected_magic:
                    self.context.log(
                        f"[download] Binary signature mismatch: expected={expected_magic!r}, "
                        f"actual={actual_magic!r}."
                    )
                    raise UpdateError("Downloaded file is not a valid AppImage binary")
                self.context.log(
                    f"[download] Binary signature verified: {expected_magic!r}."
                )

            os.replace(tmp, target)
            self.context.log(f"[download] Partial file atomically moved to final target: {target!r}.")
            duration = max(time.monotonic() - started, 1e-6)
            final_speed = received / duration
            self.context.progress(status, 100, received, total or received, final_speed, 0.0)
            self.context.log(
                f"[download] Download finished successfully in {duration:.2f}s at "
                f"{final_speed:.2f} B/s."
            )
            return target
        except Exception as exc:
            self.context.log(f"[download] Download failed: {type(exc).__name__}: {exc}")
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
                    self.context.log(f"[download] Removed partial file after failure: {tmp!r}.")
            except OSError as cleanup_exc:
                self.context.log(f"[download] Failed to remove partial file {tmp!r}: {cleanup_exc}")
            raise
