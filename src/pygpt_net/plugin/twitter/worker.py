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

import socket
import base64
import hashlib
import http.server
import json
import mimetypes
import os
import random
import threading
import time

from typing import Any, Dict, List, Optional
from urllib.parse import urlencode, quote, urlparse, parse_qs

import requests
from PySide6.QtCore import Slot

from pygpt_net.plugin.base.worker import BaseWorker, BaseSignals


class WorkerSignals(BaseSignals):
    pass


class Worker(BaseWorker):
    """
    X (Twitter) plugin worker: Auth (OAuth2 PKCE), Users, Tweets, Search, Actions, Bookmarks, Media.
    Auto-authorization when required (similar to Google plugin).
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

                        # -------- Auth --------
                        if item["cmd"] == "x_oauth_begin":
                            response = self.cmd_x_oauth_begin(item)
                        elif item["cmd"] == "x_oauth_exchange":
                            response = self.cmd_x_oauth_exchange(item)
                        elif item["cmd"] == "x_oauth_refresh":
                            response = self.cmd_x_oauth_refresh(item)

                        # -------- Users --------
                        elif item["cmd"] == "x_me":
                            response = self.cmd_x_me(item)
                        elif item["cmd"] == "x_user_by_username":
                            response = self.cmd_x_user_by_username(item)
                        elif item["cmd"] == "x_user_by_id":
                            response = self.cmd_x_user_by_id(item)

                        # -------- Tweets & timelines --------
                        elif item["cmd"] == "x_user_tweets":
                            response = self.cmd_x_user_tweets(item)
                        elif item["cmd"] == "x_search_recent":
                            response = self.cmd_x_search_recent(item)
                        elif item["cmd"] == "x_tweet_create":
                            response = self.cmd_x_tweet_create(item)
                        elif item["cmd"] == "x_tweet_delete":
                            response = self.cmd_x_tweet_delete(item)
                        elif item["cmd"] == "x_tweet_reply":
                            response = self.cmd_x_tweet_reply(item)
                        elif item["cmd"] == "x_tweet_quote":
                            response = self.cmd_x_tweet_quote(item)

                        # -------- Tweet actions --------
                        elif item["cmd"] == "x_like":
                            response = self.cmd_x_like(item)
                        elif item["cmd"] == "x_unlike":
                            response = self.cmd_x_unlike(item)
                        elif item["cmd"] == "x_retweet":
                            response = self.cmd_x_retweet(item)
                        elif item["cmd"] == "x_unretweet":
                            response = self.cmd_x_unretweet(item)
                        elif item["cmd"] == "x_hide_reply":
                            response = self.cmd_x_hide_reply(item)

                        # -------- Bookmarks --------
                        elif item["cmd"] == "x_bookmarks_list":
                            response = self.cmd_x_bookmarks_list(item)
                        elif item["cmd"] == "x_bookmark_add":
                            response = self.cmd_x_bookmark_add(item)
                        elif item["cmd"] == "x_bookmark_remove":
                            response = self.cmd_x_bookmark_remove(item)

                        # -------- Media --------
                        elif item["cmd"] == "x_upload_media":
                            response = self.cmd_x_upload_media(item)
                        elif item["cmd"] == "x_media_set_alt_text":
                            response = self.cmd_x_media_set_alt_text(item)

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

    # ---------------------- HTTP / Auth helpers ----------------------

    def _api_base(self) -> str:
        return (self.plugin.get_option_value("api_base") or "https://api.x.com").rstrip("/")

    def _auth_base(self) -> str:
        return (self.plugin.get_option_value("authorize_base") or "https://x.com").rstrip("/")

    def _timeout(self) -> int:
        try:
            return int(self.plugin.get_option_value("http_timeout") or 30)
        except Exception:
            return 30

    def _now(self) -> int:
        return int(time.time())

    def _get(self, path: str, params: dict = None, user_context: bool = False):
        url = f"{self._api_base()}{path}"
        headers = self._auth_header(user_context=user_context)
        r = requests.get(url, headers=headers, params=params or {}, timeout=self._timeout())
        return self._handle_response(r)

    def _delete(self, path: str, params: dict = None, user_context: bool = False):
        url = f"{self._api_base()}{path}"
        headers = self._auth_header(user_context=user_context)
        r = requests.delete(url, headers=headers, params=params or {}, timeout=self._timeout())
        return self._handle_response(r)

    def _post_json(self, path: str, payload: dict, user_context: bool = False):
        url = f"{self._api_base()}{path}"
        headers = self._auth_header(user_context=user_context)
        headers["Content-Type"] = "application/json"
        r = requests.post(url, headers=headers, json=payload or {}, timeout=self._timeout())
        return self._handle_response(r)

    def _post_form(self, path: str, form: dict, files: dict | None = None, user_context: bool = False):
        url = f"{self._api_base()}{path}"
        headers = self._auth_header(user_context=user_context)
        r = requests.post(url, headers=headers, data=form or {}, files=files, timeout=self._timeout())
        return self._handle_response(r)

    def _handle_response(self, r: requests.Response) -> dict:
        try:
            data = r.json() if r.content else {}
        except Exception:
            data = {"raw": r.text}
        if not (200 <= r.status_code < 300):
            if isinstance(data, dict) and data.get("errors"):
                raise RuntimeError(json.dumps({"status": r.status_code, "errors": data.get("errors")}, ensure_ascii=False))
            raise RuntimeError(f"HTTP {r.status_code}: {data or r.text}")
        data["_meta"] = {
            "status": r.status_code,
            "x-rate-remaining": r.headers.get("x-rate-limit-remaining"),
            "x-rate-reset": r.headers.get("x-rate-limit-reset"),
        }
        return data

    def _auth_header(self, user_context: bool = False) -> Dict[str, str]:
        if user_context:
            token = self._ensure_user_token(optional=True)
            if not token and bool(self.plugin.get_option_value("oauth_auto_begin") or True):
                # try to auto-run PKCE auth and exchange
                self._auto_authorize_interactive()
                token = self._ensure_user_token(optional=False)
        else:
            token = (self.plugin.get_option_value("bearer_token") or "").strip()
            if not token:
                # fallback to user token if bearer not provided
                token = self._ensure_user_token(optional=True)
                if not token and bool(self.plugin.get_option_value("oauth_auto_begin") or True):
                    self._auto_authorize_interactive()
                    token = self._ensure_user_token(optional=False)
        if not token:
            raise RuntimeError("Missing bearer/access token. Configure bearer_token or complete OAuth2.")
        return {
            "Authorization": f"Bearer {token}",
            "User-Agent": "pygpt-net-x-plugin/1.1",
            "Accept": "application/json",
        }

    def _ensure_user_token(self, optional: bool = False) -> Optional[str]:
        access = (self.plugin.get_option_value("oauth2_access_token") or "").strip()
        exp = int(self.plugin.get_option_value("oauth2_expires_at") or 0)
        refresh = (self.plugin.get_option_value("oauth2_refresh_token") or "").strip()
        if access and exp and self._now() >= exp and refresh:
            self._refresh_access_token()
            access = (self.plugin.get_option_value("oauth2_access_token") or "").strip()
        if not access and not optional:
            raise RuntimeError("User access token missing. Run OAuth first.")
        return access or None

    def _save_tokens(self, tok: dict):
        access = tok.get("access_token")
        refresh = tok.get("refresh_token")
        expires_in = int(tok.get("expires_in") or 0)
        expires_at = self._now() + expires_in - 60 if expires_in else 0
        self.plugin.set_option_value("oauth2_access_token", access or "")
        if refresh:
            self.plugin.set_option_value("oauth2_refresh_token", refresh)
        if expires_at:
            self.plugin.set_option_value("oauth2_expires_at", str(expires_at))

    def _refresh_access_token(self):
        client_id = self.plugin.get_option_value("oauth2_client_id") or ""
        client_secret = self.plugin.get_option_value("oauth2_client_secret") or ""
        refresh = self.plugin.get_option_value("oauth2_refresh_token") or ""
        if not (client_id and refresh):
            raise RuntimeError("Cannot refresh: missing client_id or refresh_token")
        token_url = f"{self._api_base()}/2/oauth2/token"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh,
            "client_id": client_id,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if client_secret and bool(self.plugin.get_option_value("oauth2_confidential") or False):
            basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
            headers["Authorization"] = f"Basic {basic}"
            data.pop("client_id", None)
        r = requests.post(token_url, headers=headers, data=data, timeout=self._timeout())
        res = self._handle_response(r)
        self._save_tokens(res)

    # ---------------------- OAuth2 PKCE (auto) ----------------------

    def _gen_code_verifier(self, n: int = 64) -> str:
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
        return "".join(random.choice(alphabet) for _ in range(n))

    def _code_challenge(self, verifier: str) -> str:
        digest = hashlib.sha256(verifier.encode("ascii")).digest()
        return base64.urlsafe_b64encode(digest).decode().rstrip("=")

    # --- helpers for local callback port management ---

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
        # try preferred or next ones; finally ephemeral
        base = preferred if preferred and preferred >= 1024 else 8731
        for p in range(base, base + 50):
            if self._can_bind(host, p):
                return p
        # last resort ephemeral
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((host, 0))
        free_port = s.getsockname()[1]
        s.close()
        return free_port

    def _prepare_effective_redirect(self, redirect_uri: str) -> str:
        # choose a safe, available port for localhost/127.0.0.1
        u = urlparse(redirect_uri)
        host = u.hostname or "127.0.0.1"
        scheme = u.scheme or "http"
        path = u.path or "/"
        if not self._redirect_is_local(redirect_uri):
            return redirect_uri  # non-local redirect untouched

        port = u.port
        allow_fallback = bool(self.plugin.get_option_value("oauth_allow_port_fallback") or True)
        if not port or port < 1024 or not self._can_bind(host, port):
            if not allow_fallback and (not port or port < 1024):
                raise RuntimeError("Configured redirect_uri uses a privileged or unavailable port. Use a port >1024.")
            # prefer configured oauth_local_port, else 8731
            pref = int(self.plugin.get_option_value("oauth_local_port") or 8731)
            new_port = self._pick_port(host, pref)
            return f"{scheme}://{host}:{new_port}{path}"
        return redirect_uri

    # adjust signature to allow overriding redirect per session
    def _build_auth_url(self, scopes: str, verifier: str, state: str, redirect_uri: Optional[str] = None) -> str:
        client_id = self.plugin.get_option_value("oauth2_client_id") or ""
        redirect_uri = redirect_uri or (self.plugin.get_option_value("oauth2_redirect_uri") or "")
        challenge = self._code_challenge(verifier)
        return (
                f"{self._auth_base()}/i/oauth2/authorize?"
                + urlencode({
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scopes,
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        })
        )

    def _auto_authorize_interactive(self):
        client_id = self.plugin.get_option_value("oauth2_client_id") or ""
        redirect_cfg = self.plugin.get_option_value("oauth2_redirect_uri") or ""
        if not (client_id and redirect_cfg):
            raise RuntimeError("OAuth auto-start: set oauth2_client_id and oauth2_redirect_uri first.")

        scopes = (self.plugin.get_option_value("oauth2_scopes") or
                  "tweet.read users.read like.read like.write tweet.write bookmark.read bookmark.write tweet.moderate.write offline.access")
        verifier = self._gen_code_verifier()
        state = self._gen_code_verifier(32)
        self.plugin.set_option_value("oauth2_code_verifier", verifier)
        self.plugin.set_option_value("oauth2_state", state)

        # choose an effective local redirect (safe, available port)
        effective_redirect = self._prepare_effective_redirect(redirect_cfg)
        auth_url = self._build_auth_url(scopes, verifier, state, redirect_uri=effective_redirect)

        if bool(self.plugin.get_option_value("oauth_open_browser") or True):
            try:
                self.plugin.open_url(auth_url)
            except Exception:
                pass

        if bool(self.plugin.get_option_value("oauth_local_server") or True) and self._redirect_is_local(
                effective_redirect):
            code, st = self._run_local_callback_and_wait(auth_url, effective_redirect)
            if (self.plugin.get_option_value("oauth2_state") or "") and st and st != self.plugin.get_option_value(
                    "oauth2_state"):
                raise RuntimeError("OAuth state mismatch.")
            self._exchange_code_for_token(code)
            try:
                me = self._get("/2/users/me", user_context=True)
                usr = (me.get("data") or {})
                if usr.get("id"):
                    self.plugin.set_option_value("user_id", usr["id"])
                if usr.get("username"):
                    self.plugin.set_option_value("username", usr["username"])
            except Exception:
                pass
            self.msg = f"X: Authorization complete on {effective_redirect}."
            return

        self.msg = f"Authorize in browser and run x_oauth_exchange with 'code'. URL: {auth_url}"

    def _redirect_is_local(self, redirect_uri: str) -> bool:
        try:
            u = urlparse(redirect_uri)
            return u.scheme in ("http",) and (u.hostname in ("127.0.0.1", "localhost"))
        except Exception:
            return False

    def _run_local_callback_and_wait(self, auth_url: str, redirect_uri: str) -> (str, str):
        u = urlparse(redirect_uri)
        host = u.hostname or "127.0.0.1"
        port = u.port or 8731  # should be set already
        path_expected = u.path or "/"
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

        # bind here; if fails -> jasny komunikat
        try:
            httpd = http.server.HTTPServer((host, port), Handler)
        except PermissionError:
            raise RuntimeError(
                f"Cannot bind local callback on {host}:{port}. Use a port >1024 or change oauth_local_port.")
        except OSError as e:
            raise RuntimeError(
                f"Port {port} busy on {host}. Change oauth_local_port or whitelist a different port in X App. ({e})")

        srv_thr = threading.Thread(target=httpd.serve_forever, daemon=True)
        srv_thr.start()

        # ensure browser is open as last resort
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
        srv_thr.join(timeout=5)

        if not got or not result["code"]:
            raise RuntimeError(
                "No OAuth code received (timeout). Check that the callback URL exactly matches your X App settings.")
        return result["code"], result["state"]

    def _exchange_code_for_token(self, code: str):
        client_id = self.plugin.get_option_value("oauth2_client_id") or ""
        client_secret = self.plugin.get_option_value("oauth2_client_secret") or ""
        redirect_uri = self.plugin.get_option_value("oauth2_redirect_uri") or ""
        verifier = self.plugin.get_option_value("oauth2_code_verifier") or ""
        if not (client_id and redirect_uri and verifier and code):
            raise RuntimeError("Exchange failed: missing client_id/redirect_uri/verifier/code.")
        token_url = f"{self._api_base()}/2/oauth2/token"
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "code_verifier": verifier,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if client_secret and bool(self.plugin.get_option_value("oauth2_confidential") or False):
            basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
            headers["Authorization"] = f"Basic {basic}"
            data.pop("client_id", None)
        r = requests.post(token_url, headers=headers, data=data, timeout=self._timeout())
        res = self._handle_response(r)
        self._save_tokens(res)

    # ---------------------- Auth commands ----------------------

    def cmd_x_oauth_begin(self, item: dict) -> dict:
        p = item.get("params", {})
        client_id = self.plugin.get_option_value("oauth2_client_id") or ""
        redirect_cfg = self.plugin.get_option_value("oauth2_redirect_uri") or ""
        scopes = p.get("scopes") or (self.plugin.get_option_value("oauth2_scopes") or
                                     "tweet.read users.read like.read like.write tweet.write bookmark.read bookmark.write tweet.moderate.write offline.access")
        if not (client_id and redirect_cfg):
            return self.make_response(item, "Set oauth2_client_id and oauth2_redirect_uri in options first.")
        verifier = self._gen_code_verifier()
        state = p.get("state") or self._gen_code_verifier(32)
        self.plugin.set_option_value("oauth2_code_verifier", verifier)
        self.plugin.set_option_value("oauth2_state", state)
        effective_redirect = self._prepare_effective_redirect(redirect_cfg)
        auth_url = self._build_auth_url(scopes, verifier, state, redirect_uri=effective_redirect)
        if bool(self.plugin.get_option_value("oauth_open_browser") or True):
            try:
                self.plugin.open_url(auth_url)
            except Exception:
                pass
        return self.make_response(item, {"authorize_url": auth_url, "redirect_uri": effective_redirect})

    def cmd_x_oauth_exchange(self, item: dict) -> dict:
        p = item.get("params", {})
        code = p.get("code")
        state = p.get("state")
        expected_state = self.plugin.get_option_value("oauth2_state") or ""
        if not code:
            return self.make_response(item, "Param 'code' required.")
        if expected_state and state and state != expected_state:
            return self.make_response(item, "State mismatch.")
        self._exchange_code_for_token(code)
        # cache identity
        try:
            me = self._get("/2/users/me", user_context=True)
            usr = (me.get("data") or {})
            if usr.get("id"):
                self.plugin.set_option_value("user_id", usr["id"])
            if usr.get("username"):
                self.plugin.set_option_value("username", usr["username"])
        except Exception:
            pass
        return self.make_response(item, {
            "access_token": self.plugin.get_option_value("oauth2_access_token"),
            "refresh_token": self.plugin.get_option_value("oauth2_refresh_token"),
            "expires_at": self.plugin.get_option_value("oauth2_expires_at"),
        })

    def cmd_x_oauth_refresh(self, item: dict) -> dict:
        self._refresh_access_token()
        return self.make_response(item, {
            "access_token": self.plugin.get_option_value("oauth2_access_token"),
            "expires_at": self.plugin.get_option_value("oauth2_expires_at"),
        })

    # ---------------------- Users ----------------------

    def cmd_x_me(self, item: dict) -> dict:
        params = item.get("params", {}) or {}
        res = self._get("/2/users/me", params=params, user_context=True)
        data = res.get("data") or {}
        if data.get("id"):
            self.plugin.set_option_value("user_id", data["id"])
        if data.get("username"):
            self.plugin.set_option_value("username", data["username"])
        return self.make_response(item, res)

    def cmd_x_user_by_username(self, item: dict) -> dict:
        p = item.get("params", {})
        username = p.get("username")
        if not username:
            return self.make_response(item, "Param 'username' required")
        params = {}
        if p.get("user_fields"):
            params["user.fields"] = p.get("user_fields")
        if p.get("expansions"):
            params["expansions"] = p.get("expansions")
        if p.get("tweet_fields"):
            params["tweet.fields"] = p.get("tweet_fields")
        res = self._get(f"/2/users/by/username/{quote(username)}", params=params, user_context=False)
        return self.make_response(item, res)

    def cmd_x_user_by_id(self, item: dict) -> dict:
        p = item.get("params", {})
        uid = p.get("id")
        if not uid:
            return self.make_response(item, "Param 'id' required")
        params = {}
        if p.get("user_fields"):
            params["user.fields"] = p.get("user_fields")
        res = self._get(f"/2/users/{uid}", params=params, user_context=False)
        return self.make_response(item, res)

    # ---------------------- Timelines / Search ----------------------

    def cmd_x_user_tweets(self, item: dict) -> dict:
        p = item.get("params", {})
        uid = p.get("id")
        if not uid:
            return self.make_response(item, "Param 'id' (user id) required")
        params = {"max_results": p.get("max_results", 20)}
        for k in ("since_id", "until_id", "start_time", "end_time", "pagination_token"):
            if p.get(k):
                params[k] = p[k]
        if p.get("exclude"):
            params["exclude"] = ",".join(p["exclude"]) if isinstance(p["exclude"], list) else p["exclude"]
        params.setdefault("tweet.fields", p.get("tweet_fields", "id,text,created_at,public_metrics,conversation_id,referenced_tweets,attachments"))
        params.setdefault("expansions", p.get("expansions", "author_id,attachments.media_keys,referenced_tweets.id"))
        params.setdefault("media.fields", p.get("media_fields", "media_key,type,url,preview_image_url,height,width,alt_text"))
        res = self._get(f"/2/users/{uid}/tweets", params=params, user_context=False)
        return self.make_response(item, res)

    def cmd_x_search_recent(self, item: dict) -> dict:
        p = item.get("params", {})
        q = p.get("query")
        if not q:
            return self.make_response(item, "Param 'query' required")
        params = {"query": q, "max_results": p.get("max_results", 25)}
        for k in ("since_id", "until_id", "start_time", "end_time", "next_token"):
            if p.get(k):
                params[k] = p[k]
        params.setdefault("tweet.fields", p.get("tweet_fields", "id,text,created_at,public_metrics,conversation_id,referenced_tweets,attachments,lang"))
        params.setdefault("expansions", p.get("expansions", "author_id,attachments.media_keys,referenced_tweets.id"))
        params.setdefault("media.fields", p.get("media_fields", "media_key,type,url,preview_image_url,height,width,alt_text"))
        res = self._get("/2/tweets/search/recent", params=params, user_context=False)
        return self.make_response(item, res)

    # ---------------------- Tweet CRUD ----------------------

    def _ensure_user_id(self) -> str:
        uid = self.plugin.get_option_value("user_id") or ""
        if uid:
            return uid
        me = self._get("/2/users/me", user_context=True)
        uid = (me.get("data") or {}).get("id")
        if not uid:
            raise RuntimeError("Cannot resolve user_id (call x_me first).")
        self.plugin.set_option_value("user_id", uid)
        return uid

    def cmd_x_tweet_create(self, item: dict) -> dict:
        p = item.get("params", {})
        text = p.get("text", "")
        media_ids = p.get("media_ids") or []
        quote_id = p.get("quote_tweet_id")
        reply_to = p.get("in_reply_to_tweet_id")
        tagged_user_ids = p.get("tagged_user_ids") or []
        place_id = p.get("place_id")
        reply_settings = p.get("reply_settings")
        poll = p.get("poll")
        card_uri = p.get("card_uri")
        payload: Dict[str, Any] = {"text": text}
        if media_ids or tagged_user_ids:
            payload["media"] = {}
            if media_ids:
                payload["media"]["media_ids"] = media_ids
            if tagged_user_ids:
                payload["media"]["tagged_user_ids"] = tagged_user_ids
        if quote_id:
            payload["quote_tweet_id"] = quote_id
        if reply_to:
            payload["reply"] = {"in_reply_to_tweet_id": reply_to, "exclude_reply_user_ids": p.get("exclude_reply_user_ids")}
        if place_id:
            payload["geo"] = {"place_id": place_id}
        if reply_settings:
            payload["reply_settings"] = reply_settings
        if poll:
            payload["poll"] = poll
        if card_uri:
            payload["card_uri"] = card_uri
        res = self._post_json("/2/tweets", payload, user_context=True)
        return self.make_response(item, res)

    def cmd_x_tweet_delete(self, item: dict) -> dict:
        p = item.get("params", {})
        tid = p.get("id")
        if not tid:
            return self.make_response(item, "Param 'id' (tweet id) required")
        res = self._delete(f"/2/tweets/{tid}", user_context=True)
        return self.make_response(item, res)

    def cmd_x_tweet_reply(self, item: dict) -> dict:
        p = item.get("params", {})
        tid = p.get("in_reply_to_tweet_id")
        if not tid:
            return self.make_response(item, "Param 'in_reply_to_tweet_id' required")
        p2 = dict(p)
        p2["text"] = p.get("text", "")
        p2["in_reply_to_tweet_id"] = tid
        return self.cmd_x_tweet_create({"params": p2, "cmd": "x_tweet_create"})

    def cmd_x_tweet_quote(self, item: dict) -> dict:
        p = item.get("params", {})
        qid = p.get("quote_tweet_id")
        if not qid:
            return self.make_response(item, "Param 'quote_tweet_id' required")
        p2 = dict(p)
        p2["quote_tweet_id"] = qid
        return self.cmd_x_tweet_create({"params": p2, "cmd": "x_tweet_create"})

    # ---------------------- Actions ----------------------

    def cmd_x_like(self, item: dict) -> dict:
        p = item.get("params", {})
        tid = p.get("tweet_id")
        if not tid:
            return self.make_response(item, "Param 'tweet_id' required")
        uid = p.get("user_id") or self._ensure_user_id()
        res = self._post_json(f"/2/users/{uid}/likes", {"tweet_id": tid}, user_context=True)
        return self.make_response(item, res)

    def cmd_x_unlike(self, item: dict) -> dict:
        p = item.get("params", {})
        tid = p.get("tweet_id")
        if not tid:
            return self.make_response(item, "Param 'tweet_id' required")
        uid = p.get("user_id") or self._ensure_user_id()
        res = self._delete(f"/2/users/{uid}/likes/{tid}", user_context=True)
        return self.make_response(item, res)

    def cmd_x_retweet(self, item: dict) -> dict:
        p = item.get("params", {})
        tid = p.get("tweet_id")
        if not tid:
            return self.make_response(item, "Param 'tweet_id' required")
        uid = p.get("user_id") or self._ensure_user_id()
        res = self._post_json(f"/2/users/{uid}/retweets", {"tweet_id": tid}, user_context=True)
        return self.make_response(item, res)

    def cmd_x_unretweet(self, item: dict) -> dict:
        p = item.get("params", {})
        tid = p.get("tweet_id")
        if not tid:
            return self.make_response(item, "Param 'tweet_id' required")
        uid = p.get("user_id") or self._ensure_user_id()
        res = self._delete(f"/2/users/{uid}/retweets/{tid}", user_context=True)
        return self.make_response(item, res)

    def cmd_x_bookmarks_list(self, item: dict) -> dict:
        p = item.get("params", {})
        uid = p.get("user_id") or self._ensure_user_id()
        params = {"max_results": p.get("max_results", 50)}
        if p.get("pagination_token"):
            params["pagination_token"] = p["pagination_token"]
        params.setdefault("tweet.fields", p.get("tweet_fields", "id,text,created_at,public_metrics,attachments,referenced_tweets"))
        params.setdefault("expansions", p.get("expansions", "author_id,attachments.media_keys,referenced_tweets.id"))
        params.setdefault("media.fields", p.get("media_fields", "media_key,type,url,preview_image_url,height,width,alt_text"))
        res = self._get(f"/2/users/{uid}/bookmarks", params=params, user_context=True)
        return self.make_response(item, res)

    def cmd_x_bookmark_add(self, item: dict) -> dict:
        p = item.get("params", {})
        tid = p.get("tweet_id")
        if not tid:
            return self.make_response(item, "Param 'tweet_id' required")
        uid = p.get("user_id") or self._ensure_user_id()
        res = self._post_json(f"/2/users/{uid}/bookmarks", {"tweet_id": tid}, user_context=True)
        return self.make_response(item, res)

    def cmd_x_bookmark_remove(self, item: dict) -> dict:
        p = item.get("params", {})
        tid = p.get("tweet_id")
        if not tid:
            return self.make_response(item, "Param 'tweet_id' required")
        uid = p.get("user_id") or self._ensure_user_id()
        res = self._delete(f"/2/users/{uid}/bookmarks/{tid}", user_context=True)
        return self.make_response(item, res)

    def cmd_x_hide_reply(self, item: dict) -> dict:
        p = item.get("params", {})
        tid = p.get("tweet_id")
        hidden = bool(p.get("hidden", True))
        if not tid:
            return self.make_response(item, "Param 'tweet_id' required")
        res = self._post_json(f"/2/tweets/{tid}/hidden", {"hidden": hidden}, user_context=True)
        return self.make_response(item, res)

    # ---------------------- Media ----------------------

    def _guess_mime(self, path: str) -> str:
        mt, _ = mimetypes.guess_type(path)
        return mt or "application/octet-stream"

    def cmd_x_upload_media(self, item: dict) -> dict:
        p = item.get("params", {})
        local = self.prepare_path(p.get("path") or "")
        if not os.path.exists(local):
            return self.make_response(item, f"Local file not found: {local}")
        media_type = p.get("media_type") or self._guess_mime(local)
        category = p.get("media_category") or ("tweet_image" if media_type.startswith("image/") else
                                               "tweet_gif" if media_type == "image/gif" else
                                               "tweet_video" if media_type.startswith("video/") else "tweet_image")
        chunk_size = int(p.get("chunk_size") or (1024 * 1024))
        poll = bool(p.get("wait_for_processing", True))

        init_form = {
            "command": "INIT",
            "media_type": media_type,
            "total_bytes": str(os.path.getsize(local)),
            "media_category": category,
        }
        init_res = self._post_form("/2/media/upload", init_form, user_context=True)
        data = init_res.get("data") or init_res
        media_id = str(data.get("id") or data.get("media_id") or "")
        if not media_id:
            return self.make_response(item, "Failed to INIT media upload")

        seg = 0
        with open(local, "rb") as fh:
            while True:
                buf = fh.read(chunk_size)
                if not buf:
                    break
                files = {"media": ("blob", buf, media_type)}
                append_form = {"command": "APPEND", "media_id": media_id, "segment_index": str(seg)}
                self._post_form("/2/media/upload", append_form, files=files, user_context=True)
                seg += 1

        fin_res = self._post_form("/2/media/upload", {"command": "FINALIZE", "media_id": media_id}, user_context=True)
        fin_data = fin_res.get("data") or fin_res
        proc = ((fin_data or {}).get("processing_info") or {})
        if poll and proc:
            while True:
                time.sleep(int(proc.get("check_after_secs") or 2))
                st = self._get("/2/media/upload", params={"command": "STATUS", "media_id": media_id}, user_context=True)
                sdata = st.get("data") or st
                pinfo = (sdata or {}).get("processing_info") or {}
                state = (pinfo or {}).get("state")
                if state in ("succeeded", None):
                    break
                if state == "failed":
                    raise RuntimeError(f"Media processing failed: {sdata}")
                proc = pinfo

        return self.make_response(item, {"media_id": media_id, "media_key": fin_data.get("media_key")})

    def cmd_x_media_set_alt_text(self, item: dict) -> dict:
        p = item.get("params", {})
        media_id = p.get("media_id")
        alt_text = p.get("alt_text")
        if not (media_id and alt_text):
            return self.make_response(item, "Params 'media_id' and 'alt_text' required")
        payload = {"id": media_id, "metadata": {"alt_text": {"text": alt_text}}}
        res = self._post_json("/2/media/metadata", payload, user_context=True)
        return self.make_response(item, res)

    # ---------------------- FS helpers ----------------------

    def prepare_path(self, path: str) -> str:
        if path in [".", "./"]:
            return self.plugin.window.core.config.get_user_dir("data")
        if self.is_absolute_path(path):
            return path
        return os.path.join(self.plugin.window.core.config.get_user_dir("data"), path)

    def is_absolute_path(self, path: str) -> bool:
        return os.path.isabs(path)