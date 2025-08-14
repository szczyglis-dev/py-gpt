#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.15 00:00:00                  #
# ================================================== #

from __future__ import annotations

import base64
import http.server
import json
import mimetypes
import os
import random
import socket
import threading
import time

from typing import Any, Dict, List, Optional
from urllib.parse import urlencode, urlparse, parse_qs

import requests
from PySide6.QtCore import Slot

from pygpt_net.plugin.base.worker import BaseWorker, BaseSignals


class WorkerSignals(BaseSignals):
    pass


class Worker(BaseWorker):
    """
    Slack plugin worker: OAuth v2 (auto), Auth test, Users, Conversations, Chat, Files (External upload).
    """

    def __init__(self, *args, **kwargs):
        super(Worker, self).__init__()
        self.signals = WorkerSignals()
        self.args = args
        self.kwargs = kwargs
        self.plugin = None
        self.cmds = None
        self.ctx = None
        self.msg = None

    # ---------------------- Core runner ----------------------

    @Slot()
    def run(self):
        try:
            responses = []
            for item in self.cmds:
                if self.is_stopped():
                    break
                try:
                    response = None
                    if item["cmd"] in self.plugin.allowed_cmds and self.plugin.has_cmd(item["cmd"]):

                        # ---- Auth ----
                        if item["cmd"] == "slack_oauth_begin":
                            response = self.cmd_slack_oauth_begin(item)
                        elif item["cmd"] == "slack_oauth_exchange":
                            response = self.cmd_slack_oauth_exchange(item)
                        elif item["cmd"] == "slack_oauth_refresh":
                            response = self.cmd_slack_oauth_refresh(item)
                        elif item["cmd"] == "slack_auth_test":
                            response = self.cmd_slack_auth_test(item)

                        # ---- Users / Contacts ----
                        elif item["cmd"] == "slack_users_list":
                            response = self.cmd_slack_users_list(item)

                        # ---- Conversations (channels/DMs) ----
                        elif item["cmd"] == "slack_conversations_list":
                            response = self.cmd_slack_conversations_list(item)
                        elif item["cmd"] == "slack_conversations_history":
                            response = self.cmd_slack_conversations_history(item)
                        elif item["cmd"] == "slack_conversations_replies":
                            response = self.cmd_slack_conversations_replies(item)
                        elif item["cmd"] == "slack_conversations_open":
                            response = self.cmd_slack_conversations_open(item)

                        # ---- Chat ----
                        elif item["cmd"] == "slack_chat_post_message":
                            response = self.cmd_slack_chat_post_message(item)
                        elif item["cmd"] == "slack_chat_delete":
                            response = self.cmd_slack_chat_delete(item)

                        # ---- Files ----
                        elif item["cmd"] == "slack_files_upload":
                            response = self.cmd_slack_files_upload(item)

                        if response:
                            responses.append(response)

                except Exception as e:
                    responses.append(self.make_response(item, self.throw_error(e)))

            if responses:
                self.reply_more(responses)
            if self.msg is not None:
                self.status(self.msg)
        except Exception as e:
            self.error(e)
        finally:
            self.cleanup()

    # ---------------------- HTTP / Helpers ----------------------

    def _api_base(self) -> str:
        return (self.plugin.get_option_value("api_base") or "https://slack.com/api").rstrip("/")

    def _oauth_base(self) -> str:
        return (self.plugin.get_option_value("oauth_base") or "https://slack.com").rstrip("/")

    def _timeout(self) -> int:
        try:
            return int(self.plugin.get_option_value("http_timeout") or 30)
        except Exception:
            return 30

    def _now(self) -> int:
        return int(time.time())

    def _auth_header(self) -> Dict[str, str]:
        # Prefer bot token; fallback to user token; autostart OAuth if enabled.
        token = (self.plugin.get_option_value("bot_token") or "").strip()
        if not token:
            token = (self.plugin.get_option_value("user_token") or "").strip()
        if not token and bool(self.plugin.get_option_value("oauth_auto_begin") or True):
            self._auto_authorize_interactive()
            token = (self.plugin.get_option_value("bot_token") or "").strip() or \
                    (self.plugin.get_option_value("user_token") or "").strip()
        if not token:
            raise RuntimeError("Missing Slack token. Provide bot_token/user_token or complete OAuth.")
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "pygpt-net-slack-plugin/1.0",
        }

    def _handle_response(self, r: requests.Response) -> dict:
        try:
            data = r.json() if r.content else {}
        except Exception:
            data = {"raw": r.text}
        if r.status_code == 429:
            ra = r.headers.get("Retry-After")
            raise RuntimeError(json.dumps({"status": 429, "error": "ratelimited", "retry_after": ra}, ensure_ascii=False))
        if not (200 <= r.status_code < 300):
            raise RuntimeError(f"HTTP {r.status_code}: {data or r.text}")
        if isinstance(data, dict) and not data.get("ok", True):
            # Slack-style error envelope
            raise RuntimeError(json.dumps({"status": r.status_code, "error": data.get("error"), "data": data}, ensure_ascii=False))
        data["_meta"] = {
            "status": r.status_code,
            "ratelimit-retry-after": r.headers.get("Retry-After"),
        }
        return data

    def _get(self, method: str, params: dict = None):
        url = f"{self._api_base()}/{method.lstrip('/')}"
        headers = self._auth_header()
        r = requests.get(url, headers=headers, params=params or {}, timeout=self._timeout())
        return self._handle_response(r)

    def _post_form(self, method: str, form: dict = None):
        url = f"{self._api_base()}/{method.lstrip('/')}"
        headers = self._auth_header()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        r = requests.post(url, headers=headers, data=form or {}, timeout=self._timeout())
        return self._handle_response(r)

    def _post_json(self, method: str, payload: dict):
        url = f"{self._api_base()}/{method.lstrip('/')}"
        headers = self._auth_header()
        headers["Content-Type"] = "application/json"
        r = requests.post(url, headers=headers, json=payload or {}, timeout=self._timeout())
        return self._handle_response(r)

    # ---------------------- OAuth2 (Slack, no-PKCE) ----------------------

    def _gen_state(self, n: int = 32) -> str:
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        return "".join(random.choice(alphabet) for _ in range(n))

    def _redirect_is_local(self, redirect_uri: str) -> bool:
        try:
            u = urlparse(redirect_uri)
            return u.scheme in ("http",) and (u.hostname in ("127.0.0.1", "localhost"))
        except Exception:
            return False

    def _can_bind(self, host: str, port: int) -> bool:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            return True
        except Exception:
            return False
        finally:
            try:
                s.close()
            except Exception:
                pass

    def _pick_port(self, host: str, preferred: int) -> int:
        base = preferred if preferred and preferred >= 1024 else 8733
        for p in range(base, base + 40):
            if self._can_bind(host, p):
                return p
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((host, 0))
        free_port = s.getsockname()[1]
        s.close()
        return free_port

    def _prepare_effective_redirect(self, redirect_uri: str) -> str:
        u = urlparse(redirect_uri)
        host = u.hostname or "127.0.0.1"
        scheme = u.scheme or "http"
        path = u.path or "/"
        if not self._redirect_is_local(redirect_uri):
            return redirect_uri
        port = u.port
        allow_fallback = bool(self.plugin.get_option_value("oauth_allow_port_fallback") or True)
        if not port or port < 1024 or not self._can_bind(host, port):
            if not allow_fallback and (not port or port < 1024):
                raise RuntimeError("Configured redirect_uri uses a privileged/unavailable port. Use port >1024.")
            pref = int(self.plugin.get_option_value("oauth_local_port") or 8733)
            new_port = self._pick_port(host, pref)
            return f"{scheme}://{host}:{new_port}{path}"
        return redirect_uri

    def _build_auth_url(self, state: str, redirect_uri: str) -> str:
        client_id = self.plugin.get_option_value("oauth2_client_id") or ""
        scope = (self.plugin.get_option_value("bot_scopes") or "").replace(" ", "")
        user_scope = (self.plugin.get_option_value("user_scopes") or "").replace(" ", "")
        q = {
            "client_id": client_id,
            "scope": scope,
            "redirect_uri": redirect_uri,
            "state": state,
        }
        if user_scope:
            q["user_scope"] = user_scope
        return f"{self._oauth_base()}/oauth/v2/authorize?{urlencode(q)}"

    def _oauth_exchange_code(self, code: str, redirect_uri: str) -> dict:
        client_id = self.plugin.get_option_value("oauth2_client_id") or ""
        client_secret = self.plugin.get_option_value("oauth2_client_secret") or ""
        token_url = f"{self._api_base()}/oauth.v2.access"
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        # Slack recommends HTTP Basic for client auth
        if client_id and client_secret:
            basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
            headers["Authorization"] = f"Basic {basic}"
        else:
            data["client_id"] = client_id
            data["client_secret"] = client_secret
        r = requests.post(token_url, headers=headers, data=data, timeout=self._timeout())
        res = self._handle_response(r)
        self._save_oauth_tokens(res)
        return res

    def _oauth_refresh_token(self):
        client_id = self.plugin.get_option_value("oauth2_client_id") or ""
        client_secret = self.plugin.get_option_value("oauth2_client_secret") or ""
        refresh = self.plugin.get_option_value("oauth2_refresh_token") or ""
        if not (client_id and client_secret and refresh):
            raise RuntimeError("Cannot refresh: missing client_id/client_secret/refresh_token")
        token_url = f"{self._api_base()}/oauth.v2.access"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        headers["Authorization"] = f"Basic {basic}"
        r = requests.post(token_url, headers=headers, data=data, timeout=self._timeout())
        res = self._handle_response(r)
        self._save_oauth_tokens(res)
        return res

    def _save_oauth_tokens(self, res: dict):
        # Slack returns bot access_token (xoxb-...) and authed_user with optional access_token
        bot_token = res.get("access_token") or ""
        authed_user = (res.get("authed_user") or {})
        user_token = authed_user.get("access_token") or ""
        refresh_bot = res.get("refresh_token") or ""
        refresh_user = authed_user.get("refresh_token") or ""
        expires_in = int(res.get("expires_in") or 0)
        expires_at = self._now() + expires_in - 60 if expires_in else 0

        if bot_token:
            self.plugin.set_option_value("bot_token", bot_token)
        if user_token:
            self.plugin.set_option_value("user_token", user_token)
        if refresh_bot:
            self.plugin.set_option_value("oauth2_refresh_token", refresh_bot)
        elif refresh_user:
            self.plugin.set_option_value("oauth2_refresh_token", refresh_user)
        if expires_at:
            self.plugin.set_option_value("oauth2_expires_at", str(expires_at))

        if res.get("team"):
            team = res.get("team") or {}
            if isinstance(team, dict) and team.get("id"):
                self.plugin.set_option_value("team_id", team.get("id"))
        if res.get("bot_user_id"):
            self.plugin.set_option_value("bot_user_id", res.get("bot_user_id"))
        if authed_user.get("id"):
            self.plugin.set_option_value("authed_user_id", authed_user.get("id"))

    def _run_local_callback_and_wait(self, expected_state: str, auth_url: str, redirect_uri: str) -> (str, str):
        u = urlparse(redirect_uri)
        host = u.hostname or "127.0.0.1"
        port = u.port or 8733
        timeout_sec = int(self.plugin.get_option_value("oauth_local_timeout") or 180)
        html_ok = (self.plugin.get_option_value("oauth_success_html")
                   or "<html><body><h3>Authorization complete. You can close this window.</h3></body></html>")
        html_err = (self.plugin.get_option_value("oauth_fail_html")
                    or "<html><body><h3>Authorization failed.</h3></body></html>")

        result = {"code": None, "state": None}
        event = threading.Event()

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):
                return

            def do_GET(self):
                try:
                    q = urlparse(self.path)
                    qs = parse_qs(q.query)
                    result["code"] = (qs.get("code") or [None])[0]
                    result["state"] = (qs.get("state") or [None])[0]
                    ok = result["code"] is not None
                    data = html_ok if ok else html_err
                    self.send_response(200 if ok else 400)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(data.encode("utf-8"))))
                    self.end_headers()
                    self.wfile.write(data.encode("utf-8"))
                finally:
                    event.set()

        try:
            httpd = http.server.HTTPServer((host, port), Handler)
        except Exception as e:
            raise RuntimeError(f"Cannot bind local callback on {host}:{port}: {e}")

        thr = threading.Thread(target=httpd.serve_forever, daemon=True)
        thr.start()

        try:
            if bool(self.plugin.get_option_value("oauth_open_browser") or True):
                self.plugin.open_url(auth_url)
        except Exception:
            pass

        got = event.wait(timeout=timeout_sec)
        try:
            httpd.shutdown()
        except Exception:
            pass
        thr.join(timeout=5)

        if not got or not result["code"]:
            raise RuntimeError("No OAuth code received (timeout). Check callback URL in Slack App settings.")
        if expected_state and result["state"] and expected_state != result["state"]:
            raise RuntimeError("OAuth state mismatch")
        return result["code"], result["state"]

    def _auto_authorize_interactive(self):
        client_id = self.plugin.get_option_value("oauth2_client_id") or ""
        redirect_cfg = self.plugin.get_option_value("oauth2_redirect_uri") or ""
        if not (client_id and redirect_cfg):
            raise RuntimeError("OAuth auto-start: set oauth2_client_id and oauth2_redirect_uri first.")

        state = self._gen_state()
        self.plugin.set_option_value("oauth2_state", state)
        effective_redirect = self._prepare_effective_redirect(redirect_cfg)
        auth_url = self._build_auth_url(state, effective_redirect)

        if bool(self.plugin.get_option_value("oauth_open_browser") or True):
            try:
                self.plugin.open_url(auth_url)
            except Exception:
                pass

        if bool(self.plugin.get_option_value("oauth_local_server") or True) and self._redirect_is_local(effective_redirect):
            code, _ = self._run_local_callback_and_wait(state, auth_url, effective_redirect)
            self._oauth_exchange_code(code, effective_redirect)
            self.msg = f"Slack: Authorization complete on {effective_redirect}."
            return

        self.msg = f"Authorize in browser and run slack_oauth_exchange with 'code'. URL: {auth_url}"

    # ---------------------- Auth commands ----------------------

    def cmd_slack_oauth_begin(self, item: dict) -> dict:
        client_id = self.plugin.get_option_value("oauth2_client_id") or ""
        redirect_cfg = self.plugin.get_option_value("oauth2_redirect_uri") or ""
        if not (client_id and redirect_cfg):
            return self.make_response(item, "Set oauth2_client_id and oauth2_redirect_uri in options first.")
        state = self._gen_state()
        self.plugin.set_option_value("oauth2_state", state)
        effective_redirect = self._prepare_effective_redirect(redirect_cfg)
        auth_url = self._build_auth_url(state, effective_redirect)
        if bool(self.plugin.get_option_value("oauth_open_browser") or True):
            try:
                self.plugin.open_url(auth_url)
            except Exception:
                pass
        return self.make_response(item, {"authorize_url": auth_url, "redirect_uri": effective_redirect, "state": state})

    def cmd_slack_oauth_exchange(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        code = p.get("code")
        state = p.get("state")
        expected_state = (self.plugin.get_option_value("oauth2_state") or "")
        if not code:
            return self.make_response(item, "Param 'code' required.")
        if expected_state and state and expected_state != state:
            return self.make_response(item, "State mismatch.")
        redirect_uri = self.plugin.get_option_value("oauth2_redirect_uri") or ""
        res = self._oauth_exchange_code(code, redirect_uri)
        return self.make_response(item, {
            "bot_token": self.plugin.get_option_value("bot_token"),
            "user_token": self.plugin.get_option_value("user_token"),
            "team_id": self.plugin.get_option_value("team_id"),
            "bot_user_id": self.plugin.get_option_value("bot_user_id"),
            "authed_user_id": self.plugin.get_option_value("authed_user_id"),
            "expires_at": self.plugin.get_option_value("oauth2_expires_at"),
            "raw": res,
        })

    def cmd_slack_oauth_refresh(self, item: dict) -> dict:
        res = self._oauth_refresh_token()
        return self.make_response(item, {
            "bot_token": self.plugin.get_option_value("bot_token"),
            "user_token": self.plugin.get_option_value("user_token"),
            "expires_at": self.plugin.get_option_value("oauth2_expires_at"),
            "raw": res,
        })

    def cmd_slack_auth_test(self, item: dict) -> dict:
        res = self._post_form("auth.test", {})
        # cache ids
        if res.get("team_id"):
            self.plugin.set_option_value("team_id", res.get("team_id"))
        if res.get("user_id"):
            self.plugin.set_option_value("authed_user_id", res.get("user_id"))
        return self.make_response(item, res)

    # ---------------------- Users ----------------------

    def cmd_slack_users_list(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        params = {}
        if p.get("limit"):
            params["limit"] = int(p.get("limit"))
        if p.get("cursor"):
            params["cursor"] = p.get("cursor")
        if p.get("include_locale"):
            params["include_locale"] = "true" if bool(p.get("include_locale")) else "false"
        res = self._get("users.list", params=params)
        return self.make_response(item, res)

    # ---------------------- Conversations ----------------------

    def cmd_slack_conversations_list(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        params = {}
        params["types"] = p.get("types") or "public_channel,private_channel,im,mpim"
        params["exclude_archived"] = "true" if p.get("exclude_archived", True) else "false"
        if p.get("limit"):
            params["limit"] = int(p.get("limit"))
        if p.get("cursor"):
            params["cursor"] = p.get("cursor")
        res = self._get("conversations.list", params=params)
        return self.make_response(item, res)

    def cmd_slack_conversations_history(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        channel = p.get("channel")
        if not channel:
            return self.make_response(item, "Param 'channel' required (channel ID).")
        params = {"channel": channel}
        for k in ("limit", "cursor", "oldest", "latest"):
            if p.get(k) is not None:
                params[k] = p.get(k)
        if p.get("inclusive") is not None:
            params["inclusive"] = "true" if bool(p.get("inclusive")) else "false"
        res = self._get("conversations.history", params=params)
        return self.make_response(item, res)

    def cmd_slack_conversations_replies(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        channel = p.get("channel")
        ts = p.get("ts")
        if not channel or not ts:
            return self.make_response(item, "Params 'channel' and 'ts' (thread root) are required.")
        params = {"channel": channel, "ts": ts}
        if p.get("limit"):
            params["limit"] = int(p.get("limit"))
        if p.get("cursor"):
            params["cursor"] = p.get("cursor")
        res = self._get("conversations.replies", params=params)
        return self.make_response(item, res)

    def cmd_slack_conversations_open(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        form: Dict[str, Any] = {}
        if p.get("users"):
            # users can be str (comma separated) or list
            if isinstance(p["users"], list):
                form["users"] = ",".join(p["users"])
            else:
                form["users"] = str(p["users"])
        if p.get("channel"):
            form["channel"] = p.get("channel")
        form["return_im"] = "true" if p.get("return_im", True) else "false"
        res = self._post_form("conversations.open", form)
        return self.make_response(item, res)

    # ---------------------- Chat (messages) ----------------------

    def cmd_slack_chat_post_message(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        channel = p.get("channel")
        if not channel:
            return self.make_response(item, "Param 'channel' required (ID).")
        payload: Dict[str, Any] = {"channel": channel}
        if p.get("text") is not None:
            payload["text"] = p.get("text")
        if p.get("thread_ts"):
            payload["thread_ts"] = p.get("thread_ts")
        if p.get("reply_broadcast") is not None:
            payload["reply_broadcast"] = bool(p.get("reply_broadcast"))
        if p.get("mrkdwn") is not None:
            payload["mrkdwn"] = bool(p.get("mrkdwn"))
        if p.get("unfurl_links") is not None:
            payload["unfurl_links"] = bool(p.get("unfurl_links"))
        if p.get("unfurl_media") is not None:
            payload["unfurl_media"] = bool(p.get("unfurl_media"))
        if p.get("blocks"):
            payload["blocks"] = p.get("blocks")
        if p.get("attachments"):
            payload["attachments"] = p.get("attachments")
        res = self._post_json("chat.postMessage", payload)
        return self.make_response(item, res)

    def cmd_slack_chat_delete(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        channel = p.get("channel")
        ts = p.get("ts")
        if not channel or not ts:
            return self.make_response(item, "Params 'channel' and 'ts' required.")
        res = self._post_form("chat.delete", {"channel": channel, "ts": ts})
        return self.make_response(item, res)

    # ---------------------- Files (Upload via External flow) ----------------------

    def _guess_mime(self, path: str) -> str:
        mt, _ = mimetypes.guess_type(path)
        return mt or "application/octet-stream"

    def cmd_slack_files_upload(self, item: dict) -> dict:
        """
        Upload file using files.getUploadURLExternal -> upload bytes -> files.completeUploadExternal.
        """
        p = item.get("params", {}) or {}
        local = self.prepare_path(p.get("path") or "")
        if not os.path.exists(local):
            return self.make_response(item, f"Local file not found: {local}")

        filename = os.path.basename(local)
        size = os.path.getsize(local)
        title = p.get("title") or filename
        channel = p.get("channel")  # single channel id preferred
        initial_comment = p.get("initial_comment")
        thread_ts = p.get("thread_ts")
        alt_text = p.get("alt_text")

        # 1) get upload URL
        form = {"filename": filename, "length": str(size)}
        if alt_text:
            form["alt_txt"] = alt_text
        step1 = self._post_form("files.getUploadURLExternal", form)
        upload_url = (step1.get("upload_url") or step1.get("data", {}).get("upload_url"))
        file_id = (step1.get("file_id") or step1.get("data", {}).get("file_id"))
        if not (upload_url and file_id):
            return self.make_response(item, "Failed to get upload URL")

        # 2) upload bytes to given URL
        with open(local, "rb") as fh:
            data = fh.read()
        # raw bytes POST; Slack accepts raw or multipart for this URL
        r = requests.post(upload_url, data=data, headers={"Content-Type": self._guess_mime(local)}, timeout=self._timeout())
        if not (200 <= r.status_code < 300):
            return self.make_response(item, f"Upload transport failed: HTTP {r.status_code}: {r.text}")

        # 3) complete upload + share
        files_arr = [{"id": file_id, "title": title}]
        complete_form: Dict[str, Any] = {"files": json.dumps(files_arr)}
        if channel:
            complete_form["channel_id"] = channel
        if initial_comment:
            complete_form["initial_comment"] = initial_comment
        if thread_ts:
            complete_form["thread_ts"] = thread_ts
        step3 = self._post_form("files.completeUploadExternal", complete_form)
        return self.make_response(item, {"file_id": file_id, "result": step3})

    # ---------------------- FS helpers ----------------------

    def prepare_path(self, path: str) -> str:
        if path in [".", "./"]:
            return self.plugin.window.core.config.get_user_dir("data")
        if self.is_absolute_path(path):
            return path
        return os.path.join(self.plugin.window.core.config.get_user_dir("data"), path)

    def is_absolute_path(self, path: str) -> bool:
        return os.path.isabs(path)