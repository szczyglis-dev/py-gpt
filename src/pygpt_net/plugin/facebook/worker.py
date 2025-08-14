from __future__ import annotations

import base64
import hashlib
import http.server
import json
import mimetypes
import os
import random
import socket
import threading
import time
import webbrowser
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode, urlparse, parse_qs

import requests
from PySide6.QtCore import Slot

from pygpt_net.plugin.base.worker import BaseWorker, BaseSignals


class WorkerSignals(BaseSignals):
    pass


class Worker(BaseWorker):
    """
    Facebook (Meta Graph API) plugin worker:
    OAuth2 (PKCE), Me, Pages, Posts, Media. Auto-authorization when required.
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
                        if item["cmd"] == "fb_oauth_begin":
                            response = self.cmd_fb_oauth_begin(item)
                        elif item["cmd"] == "fb_oauth_exchange":
                            response = self.cmd_fb_oauth_exchange(item)
                        elif item["cmd"] == "fb_token_extend":
                            response = self.cmd_fb_token_extend(item)

                        # -------- Me --------
                        elif item["cmd"] == "fb_me":
                            response = self.cmd_fb_me(item)

                        # -------- Pages --------
                        elif item["cmd"] == "fb_pages_list":
                            response = self.cmd_fb_pages_list(item)
                        elif item["cmd"] == "fb_page_set_default":
                            response = self.cmd_fb_page_set_default(item)

                        # -------- Posts --------
                        elif item["cmd"] == "fb_page_posts":
                            response = self.cmd_fb_page_posts(item)
                        elif item["cmd"] == "fb_page_post_create":
                            response = self.cmd_fb_page_post_create(item)
                        elif item["cmd"] == "fb_page_post_delete":
                            response = self.cmd_fb_page_post_delete(item)

                        # -------- Media --------
                        elif item["cmd"] == "fb_page_photo_upload":
                            response = self.cmd_fb_page_photo_upload(item)

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

    # ---------------------- HTTP / helpers ----------------------

    def _graph_version(self) -> str:
        # expects like "v21.0"
        v = (self.plugin.get_option_value("graph_version") or "v21.0").strip("/")
        return v

    def _api_base(self) -> str:
        # final: https://graph.facebook.com/v21.0
        base = (self.plugin.get_option_value("api_base") or "https://graph.facebook.com").rstrip("/")
        return f"{base}/{self._graph_version()}"

    def _auth_base(self) -> str:
        # final: https://www.facebook.com/v21.0
        base = (self.plugin.get_option_value("authorize_base") or "https://www.facebook.com").rstrip("/")
        return f"{base}/{self._graph_version()}"

    def _timeout(self) -> int:
        try:
            return int(self.plugin.get_option_value("http_timeout") or 30)
        except Exception:
            return 30

    def _now(self) -> int:
        return int(time.time())

    def _auth_header(self, token: Optional[str] = None, user_context: bool = False) -> Dict[str, str]:
        # prefer explicit token; else resolve user token (auto-run OAuth if enabled)
        tok = (token or "").strip()
        if not tok:
            if user_context:
                tok = self._ensure_user_token(optional=True)
                if not tok and bool(self.plugin.get_option_value("oauth_auto_begin") or True):
                    self._auto_authorize_interactive()
                    tok = self._ensure_user_token(optional=False)
            else:
                tok = self._ensure_user_token(optional=True)
                if not tok and bool(self.plugin.get_option_value("oauth_auto_begin") or True):
                    self._auto_authorize_interactive()
                    tok = self._ensure_user_token(optional=False)
        if not tok:
            raise RuntimeError("Missing access token. Complete Facebook OAuth first.")
        return {
            "Authorization": f"Bearer {tok}",
            "User-Agent": "pygpt-net-facebook-plugin/1.0",
            "Accept": "application/json",
        }

    def _handle_response(self, r: requests.Response) -> dict:
        try:
            data = r.json() if r.content else {}
        except Exception:
            data = {"raw": r.text}
        if not (200 <= r.status_code < 300):
            # Graph errors come in "error" object
            try:
                err = (data or {}).get("error")
                if err:
                    raise RuntimeError(json.dumps({"status": r.status_code, "error": err}, ensure_ascii=False))
            except Exception:
                pass
            raise RuntimeError(f"HTTP {r.status_code}: {data or r.text}")
        # include rate meta if present
        data["_meta"] = {"status": r.status_code}
        return data

    def _get(self, path: str, params: dict = None, token: Optional[str] = None, user_context: bool = False):
        url = f"{self._api_base()}{path}"
        headers = self._auth_header(token=token, user_context=user_context)
        r = requests.get(url, headers=headers, params=params or {}, timeout=self._timeout())
        return self._handle_response(r)

    def _delete(self, path: str, params: dict = None, token: Optional[str] = None, user_context: bool = False):
        url = f"{self._api_base()}{path}"
        headers = self._auth_header(token=token, user_context=user_context)
        r = requests.delete(url, headers=headers, params=params or {}, timeout=self._timeout())
        return self._handle_response(r)

    def _post_json(self, path: str, payload: dict, token: Optional[str] = None, user_context: bool = False):
        url = f"{self._api_base()}{path}"
        headers = self._auth_header(token=token, user_context=user_context)
        headers["Content-Type"] = "application/json"
        r = requests.post(url, headers=headers, json=payload or {}, timeout=self._timeout())
        return self._handle_response(r)

    def _post_form(self, path: str, form: dict, files: dict | None = None, token: Optional[str] = None, user_context: bool = False):
        url = f"{self._api_base()}{path}"
        headers = self._auth_header(token=token, user_context=user_context)
        r = requests.post(url, headers=headers, data=form or {}, files=files, timeout=self._timeout())
        return self._handle_response(r)

    # ---------------------- Token storage ----------------------

    def _ensure_user_token(self, optional: bool = False) -> Optional[str]:
        access = (self.plugin.get_option_value("oauth2_access_token") or "").strip()
        exp = int(self.plugin.get_option_value("oauth2_expires_at") or 0)
        if access and exp and self._now() >= exp:
            # Facebook does not provide a standard refresh_token. Use fb_token_extend manually if needed.
            pass
        if not access and not optional:
            raise RuntimeError("User access token missing. Run OAuth first.")
        return access or None

    def _save_tokens(self, tok: dict):
        access = tok.get("access_token")
        expires_in = int(tok.get("expires_in") or 0)
        expires_at = self._now() + expires_in - 60 if expires_in else 0
        if access:
            self.plugin.set_option_value("oauth2_access_token", access)
        if expires_at:
            self.plugin.set_option_value("oauth2_expires_at", str(expires_at))

    # ---------------------- OAuth2 (PKCE) ----------------------

    def _gen_code_verifier(self, n: int = 64) -> str:
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
        return "".join(random.choice(alphabet) for _ in range(n))

    def _code_challenge(self, verifier: str) -> str:
        digest = hashlib.sha256(verifier.encode("ascii")).digest()
        return base64.urlsafe_b64encode(digest).decode().rstrip("=")

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
        base = preferred if preferred and preferred >= 1024 else 8732
        for p in range(base, base + 50):
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
                raise RuntimeError("Configured redirect uses a privileged or unavailable port. Use port >1024.")
            pref = int(self.plugin.get_option_value("oauth_local_port") or 8732)
            new_port = self._pick_port(host, pref)
            return f"{scheme}://{host}:{new_port}{path}"
        return redirect_uri

    def _build_auth_url(self, scopes: str, verifier: str, state: str, nonce: str, redirect_uri: Optional[str] = None) -> str:
        client_id = self.plugin.get_option_value("oauth2_client_id") or ""
        redirect_uri = redirect_uri or (self.plugin.get_option_value("oauth2_redirect_uri") or "")
        challenge = self._code_challenge(verifier)
        # Facebook Login dialog with PKCE (OIDC-compatible)
        return (
            f"{self._auth_base()}/dialog/oauth?"
            + urlencode({
                "client_id": client_id,
                "response_type": "code",
                "redirect_uri": redirect_uri,
                "scope": scopes,
                "state": state,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "nonce": nonce,
            })
        )

    def _run_local_callback_and_wait(self, auth_url: str, redirect_uri: str) -> (str, str):
        u = urlparse(redirect_uri)
        host = u.hostname or "127.0.0.1"
        port = u.port or 8732
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
        except PermissionError:
            raise RuntimeError(f"Cannot bind local callback on {host}:{port}. Use a port >1024.")
        except OSError as e:
            raise RuntimeError(f"Port {port} busy on {host}. Change oauth_local_port. ({e})")

        srv_thr = threading.Thread(target=httpd.serve_forever, daemon=True)
        srv_thr.start()

        try:
            if bool(self.plugin.get_option_value("oauth_open_browser") or True):
                webbrowser.open(auth_url)
        except Exception:
            pass

        got = event.wait(timeout=timeout_sec)
        try:
            httpd.shutdown()
        except Exception:
            pass
        srv_thr.join(timeout=5)

        if not got or not result["code"]:
            raise RuntimeError("No OAuth code received (timeout). Check redirect URI in Meta App settings.")
        return result["code"], result["state"]

    def _exchange_code_for_token(self, code: str):
        client_id = self.plugin.get_option_value("oauth2_client_id") or ""
        client_secret = self.plugin.get_option_value("oauth2_client_secret") or ""
        redirect_uri = self.plugin.get_option_value("oauth2_redirect_uri") or ""
        verifier = self.plugin.get_option_value("oauth2_code_verifier") or ""
        if not (client_id and redirect_uri and code):
            raise RuntimeError("Exchange failed: missing client_id/redirect_uri/code.")
        # With PKCE we may omit client_secret and include code_verifier
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "code": code,
        }
        if client_secret and bool(self.plugin.get_option_value("oauth2_confidential") or False):
            params["client_secret"] = client_secret
        else:
            if not verifier:
                raise RuntimeError("Missing code_verifier for PKCE exchange.")
            params["code_verifier"] = verifier

        url = f"{self._api_base()}/oauth/access_token"
        r = requests.get(url, params=params, timeout=self._timeout())
        res = self._handle_response(r)
        self._save_tokens(res)

    def _auto_authorize_interactive(self):
        client_id = self.plugin.get_option_value("oauth2_client_id") or ""
        redirect_cfg = self.plugin.get_option_value("oauth2_redirect_uri") or ""
        if not (client_id and redirect_cfg):
            raise RuntimeError("OAuth auto-start: set oauth2_client_id and oauth2_redirect_uri first.")

        scopes = (self.plugin.get_option_value("oauth2_scopes") or
                  "public_profile pages_show_list pages_read_engagement pages_manage_posts pages_read_user_content openid")
        verifier = self._gen_code_verifier()
        state = self._gen_code_verifier(32)
        nonce = self._gen_code_verifier(32)
        self.plugin.set_option_value("oauth2_code_verifier", verifier)
        self.plugin.set_option_value("oauth2_state", state)
        self.plugin.set_option_value("oauth2_nonce", nonce)

        effective_redirect = self._prepare_effective_redirect(redirect_cfg)
        auth_url = self._build_auth_url(scopes, verifier, state, nonce, redirect_uri=effective_redirect)

        if bool(self.plugin.get_option_value("oauth_open_browser") or True):
            try:
                webbrowser.open(auth_url)
            except Exception:
                pass

        if bool(self.plugin.get_option_value("oauth_local_server") or True) and self._redirect_is_local(effective_redirect):
            code, st = self._run_local_callback_and_wait(auth_url, effective_redirect)
            if (self.plugin.get_option_value("oauth2_state") or "") and st and st != self.plugin.get_option_value("oauth2_state"):
                raise RuntimeError("OAuth state mismatch.")
            self._exchange_code_for_token(code)
            try:
                me = self._get("/me", params={"fields": "id,name"}, user_context=True)
                usr = (me or {})
                if usr.get("id"):
                    self.plugin.set_option_value("user_id", usr["id"])
                if usr.get("name"):
                    self.plugin.set_option_value("user_name", usr["name"])
            except Exception:
                pass
            self.msg = f"Facebook: Authorization complete on {effective_redirect}."
            return

        self.msg = f"Authorize in browser and run fb_oauth_exchange with 'code'. URL: {auth_url}"

    # ---------------------- Auth commands ----------------------

    def cmd_fb_oauth_begin(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        client_id = self.plugin.get_option_value("oauth2_client_id") or ""
        redirect_cfg = self.plugin.get_option_value("oauth2_redirect_uri") or ""
        scopes = p.get("scopes") or (self.plugin.get_option_value("oauth2_scopes") or
                                     "public_profile pages_show_list pages_read_engagement pages_manage_posts pages_read_user_content openid")
        if not (client_id and redirect_cfg):
            return self.make_response(item, "Set oauth2_client_id and oauth2_redirect_uri in options first.")
        verifier = self._gen_code_verifier()
        state = p.get("state") or self._gen_code_verifier(32)
        nonce = self._gen_code_verifier(32)
        self.plugin.set_option_value("oauth2_code_verifier", verifier)
        self.plugin.set_option_value("oauth2_state", state)
        self.plugin.set_option_value("oauth2_nonce", nonce)
        effective_redirect = self._prepare_effective_redirect(redirect_cfg)
        auth_url = self._build_auth_url(scopes, verifier, state, nonce, redirect_uri=effective_redirect)
        if bool(self.plugin.get_option_value("oauth_open_browser") or True):
            try:
                webbrowser.open(auth_url)
            except Exception:
                pass
        return self.make_response(item, {"authorize_url": auth_url, "redirect_uri": effective_redirect})

    def cmd_fb_oauth_exchange(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
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
            me = self._get("/me", params={"fields": "id,name"}, user_context=True)
            if me.get("id"):
                self.plugin.set_option_value("user_id", me["id"])
            if me.get("name"):
                self.plugin.set_option_value("user_name", me["name"])
        except Exception:
            pass
        return self.make_response(item, {
            "access_token": self.plugin.get_option_value("oauth2_access_token"),
            "expires_at": self.plugin.get_option_value("oauth2_expires_at"),
        })

    def cmd_fb_token_extend(self, item: dict) -> dict:
        # Exchange short-lived user token for long-lived user token
        client_id = self.plugin.get_option_value("oauth2_client_id") or ""
        client_secret = self.plugin.get_option_value("oauth2_client_secret") or ""
        if not (client_id and client_secret):
            return self.make_response(item, "Set oauth2_client_id and oauth2_client_secret first.")
        access = (self.plugin.get_option_value("oauth2_access_token") or "").strip()
        if not access:
            return self.make_response(item, "No user access token to extend.")
        url = f"{self._api_base()}/oauth/access_token"
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "fb_exchange_token": access,
        }
        r = requests.get(url, params=params, timeout=self._timeout())
        res = self._handle_response(r)
        self._save_tokens(res)
        return self.make_response(item, {"access_token": res.get("access_token"), "expires_in": res.get("expires_in")})

    # ---------------------- Me ----------------------

    def cmd_fb_me(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        fields = p.get("fields") or "id,name"
        res = self._get("/me", params={"fields": fields}, user_context=True)
        if res.get("id"):
            self.plugin.set_option_value("user_id", res["id"])
        if res.get("name"):
            self.plugin.set_option_value("user_name", res["name"])
        return self.make_response(item, res)

    # ---------------------- Pages ----------------------

    def cmd_fb_pages_list(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        fields = p.get("fields") or "id,name,access_token,tasks"
        limit = int(p.get("limit") or 25)
        params = {"fields": fields, "limit": limit}
        if p.get("after"):
            params["after"] = p["after"]
        if p.get("before"):
            params["before"] = p["before"]
        res = self._get("/me/accounts", params=params, user_context=True)
        return self.make_response(item, res)

    def cmd_fb_page_set_default(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        page_id = p.get("page_id")
        if not page_id:
            return self.make_response(item, "Param 'page_id' required")
        # fetch name + access_token
        fetch_token = bool(p.get("fetch_token", True))
        name = None
        tok = None
        fields = "id,name" + (",access_token" if fetch_token else "")
        info = self._get(f"/{page_id}", params={"fields": fields}, user_context=True)
        name = info.get("name")
        tok = info.get("access_token")
        self.plugin.set_option_value("fb_page_id", page_id)
        if name:
            self.plugin.set_option_value("fb_page_name", name)
        if tok:
            self.plugin.set_option_value("fb_page_access_token", tok)
        return self.make_response(item, {"page_id": page_id, "page_name": name, "has_token": bool(tok)})

    def _ensure_page_id(self) -> str:
        pid = self.plugin.get_option_value("fb_page_id") or ""
        if not pid:
            raise RuntimeError("No default page_id set. Run fb_page_set_default or pass page_id in params.")
        return pid

    def _ensure_page_token(self, page_id: str) -> str:
        # prefer cached token for default page
        if page_id == (self.plugin.get_option_value("fb_page_id") or ""):
            tok = (self.plugin.get_option_value("fb_page_access_token") or "").strip()
            if tok:
                return tok
        # try to fetch fresh access_token via fields=access_token
        info = self._get(f"/{page_id}", params={"fields": "access_token"}, user_context=True)
        tok = info.get("access_token")
        if not tok:
            raise RuntimeError("Cannot resolve Page access token. Ensure permissions and roles are correct.")
        if page_id == (self.plugin.get_option_value("fb_page_id") or ""):
            self.plugin.set_option_value("fb_page_access_token", tok)
        return tok

    # ---------------------- Posts ----------------------

    def cmd_fb_page_posts(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        page_id = p.get("page_id") or self._ensure_page_id()
        token = self._ensure_page_token(page_id)
        fields = p.get("fields") or "id,message,created_time,permalink_url,is_published"
        limit = int(p.get("limit") or 25)
        params: Dict[str, Any] = {"fields": fields, "limit": limit}
        for k in ("since", "until", "after", "before"):
            if p.get(k):
                params[k] = p[k]
        res = self._get(f"/{page_id}/feed", params=params, token=token, user_context=False)
        return self.make_response(item, res)

    def _upload_photo(self, page_id: str, token: str, path: Optional[str] = None, url: Optional[str] = None,
                      caption: Optional[str] = None, published: bool = True, temporary: bool = False) -> dict:
        form: Dict[str, Any] = {"published": "true" if published else "false"}
        if caption:
            form["caption"] = caption
        if temporary:
            form["temporary"] = "true"
        files = None
        if path:
            local = self.prepare_path(path)
            if not os.path.exists(local):
                raise RuntimeError(f"Local file not found: {local}")
            mt, _ = mimetypes.guess_type(local)
            mt = mt or "application/octet-stream"
            files = {"source": (os.path.basename(local), open(local, "rb"), mt)}
        elif url:
            form["url"] = url
        else:
            raise RuntimeError("Provide 'path' or 'url' to upload photo.")
        res = self._post_form(f"/{page_id}/photos", form=form, files=files, token=token, user_context=False)
        return res

    def cmd_fb_page_photo_upload(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        page_id = p.get("page_id") or self._ensure_page_id()
        token = self._ensure_page_token(page_id)
        res = self._upload_photo(
            page_id=page_id,
            token=token,
            path=p.get("path"),
            url=p.get("url"),
            caption=p.get("caption"),
            published=bool(p.get("published", True)),
            temporary=bool(p.get("temporary", False)),
        )
        return self.make_response(item, res)

    def _upload_photos_unpublished(self, page_id: str, token: str, photos: List[dict]) -> List[dict]:
        # photos: [{"path": "..."}] or [{"url": "..."}]
        media = []
        for ph in photos:
            res = self._upload_photo(
                page_id=page_id,
                token=token,
                path=ph.get("path"),
                url=ph.get("url"),
                caption=ph.get("caption"),
                published=False,
                temporary=bool(ph.get("temporary", False)),
            )
            pid = res.get("id")
            if pid:
                media.append({"media_fbid": pid})
        return media

    def cmd_fb_page_post_create(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        page_id = p.get("page_id") or self._ensure_page_id()
        token = self._ensure_page_token(page_id)

        payload: Dict[str, Any] = {}
        if p.get("message") is not None:
            payload["message"] = p.get("message") or ""
        if p.get("link"):
            payload["link"] = p.get("link")
        published = bool(p.get("published", True))
        payload["published"] = published
        if not published and p.get("scheduled_publish_time"):
            payload["scheduled_publish_time"] = p.get("scheduled_publish_time")
            payload["unpublished_content_type"] = "SCHEDULED"
        if p.get("targeting"):
            payload["targeting"] = p.get("targeting")

        # attached_media via already uploaded photo ids or auto-upload URLs/paths
        attached_media = []
        media_fbids = p.get("media_fbids") or []
        if media_fbids:
            for mid in media_fbids:
                attached_media.append({"media_fbid": str(mid)})
        photo_urls = p.get("photo_urls") or []
        photo_paths = p.get("photo_paths") or []
        if photo_urls or photo_paths:
            lst = ([{"url": u} for u in photo_urls] + [{"path": ph} for ph in photo_paths])
            attached_media.extend(self._upload_photos_unpublished(page_id, token, lst))
        if attached_media:
            payload["attached_media"] = attached_media

        res = self._post_json(f"/{page_id}/feed", payload=payload, token=token, user_context=False)
        return self.make_response(item, res)

    def cmd_fb_page_post_delete(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        post_id = p.get("post_id")
        if not post_id:
            return self.make_response(item, "Param 'post_id' required (e.g. {pageid}_{postid})")
        # Page token required to delete
        page_id = (self.plugin.get_option_value("fb_page_id") or "")
        token = None
        if page_id:
            try:
                token = self._ensure_page_token(page_id)
            except Exception:
                token = None
        res = self._delete(f"/{post_id}", token=token, user_context=token is None)
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