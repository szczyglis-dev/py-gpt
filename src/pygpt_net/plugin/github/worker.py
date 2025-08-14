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
import json
import os
import time
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests
from PySide6.QtCore import Slot

from pygpt_net.plugin.base.worker import BaseWorker, BaseSignals


class WorkerSignals(BaseSignals):
    pass


class Worker(BaseWorker):
    """
    GitHub plugin worker: Auth (Device Flow or PAT), Users, Repos, Contents, Issues, Pull Requests, Search.
    Auto-authorization when required (Device Flow).
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
                        if item["cmd"] == "gh_device_begin":
                            response = self.cmd_gh_device_begin(item)
                        elif item["cmd"] == "gh_device_poll":
                            response = self.cmd_gh_device_poll(item)
                        elif item["cmd"] == "gh_set_pat":
                            response = self.cmd_gh_set_pat(item)

                        # -------- Users --------
                        elif item["cmd"] == "gh_me":
                            response = self.cmd_gh_me(item)
                        elif item["cmd"] == "gh_user_get":
                            response = self.cmd_gh_user_get(item)

                        # -------- Repos --------
                        elif item["cmd"] == "gh_repos_list":
                            response = self.cmd_gh_repos_list(item)
                        elif item["cmd"] == "gh_repo_get":
                            response = self.cmd_gh_repo_get(item)
                        elif item["cmd"] == "gh_repo_create":
                            response = self.cmd_gh_repo_create(item)
                        elif item["cmd"] == "gh_repo_delete":
                            response = self.cmd_gh_repo_delete(item)

                        # -------- Contents (files) --------
                        elif item["cmd"] == "gh_contents_get":
                            response = self.cmd_gh_contents_get(item)
                        elif item["cmd"] == "gh_file_put":
                            response = self.cmd_gh_file_put(item)
                        elif item["cmd"] == "gh_file_delete":
                            response = self.cmd_gh_file_delete(item)

                        # -------- Issues --------
                        elif item["cmd"] == "gh_issues_list":
                            response = self.cmd_gh_issues_list(item)
                        elif item["cmd"] == "gh_issue_create":
                            response = self.cmd_gh_issue_create(item)
                        elif item["cmd"] == "gh_issue_comment":
                            response = self.cmd_gh_issue_comment(item)
                        elif item["cmd"] == "gh_issue_close":
                            response = self.cmd_gh_issue_close(item)

                        # -------- Pull Requests --------
                        elif item["cmd"] == "gh_pulls_list":
                            response = self.cmd_gh_pulls_list(item)
                        elif item["cmd"] == "gh_pull_create":
                            response = self.cmd_gh_pull_create(item)
                        elif item["cmd"] == "gh_pull_merge":
                            response = self.cmd_gh_pull_merge(item)

                        # -------- Search --------
                        elif item["cmd"] == "gh_search_repos":
                            response = self.cmd_gh_search_repos(item)
                        elif item["cmd"] == "gh_search_issues":
                            response = self.cmd_gh_search_issues(item)
                        elif item["cmd"] == "gh_search_code":
                            response = self.cmd_gh_search_code(item)

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
        return (self.plugin.get_option_value("api_base") or "https://api.github.com").rstrip("/")

    def _web_base(self) -> str:
        return (self.plugin.get_option_value("web_base") or "https://github.com").rstrip("/")

    def _timeout(self) -> int:
        try:
            return int(self.plugin.get_option_value("http_timeout") or 30)
        except Exception:
            return 30

    def _headers(self) -> Dict[str, str]:
        token, scheme = self._resolve_token()
        if not token:
            # try auto device flow if enabled
            if bool(self.plugin.get_option_value("oauth_auto_begin") or True):
                self._auto_authorize_device()
                token, scheme = self._resolve_token()
        if not token:
            raise RuntimeError("Missing token. Provide PAT or complete OAuth Device Flow.")
        hdrs = {
            "Authorization": f"{scheme} {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "pygpt-net-github-plugin/1.0",
            "X-GitHub-Api-Version": self.plugin.get_option_value("api_version") or "2022-11-28",
        }
        return hdrs

    def _resolve_token(self) -> (Optional[str], str):
        # Prefer PAT if set; else OAuth device/web access token
        pat = (self.plugin.get_option_value("pat_token") or "").strip()
        if pat:
            scheme = (self.plugin.get_option_value("auth_scheme") or "token").strip() or "token"
            return pat, scheme  # PAT typically uses "token"
        access = (self.plugin.get_option_value("gh_access_token") or "").strip()
        if access:
            scheme = (self.plugin.get_option_value("auth_scheme") or "Bearer").strip() or "Bearer"
            return access, scheme
        return None, "Bearer"

    def _handle_response(self, r: requests.Response) -> dict:
        # Try read JSON; if not JSON, keep raw text
        try:
            payload = r.json() if r.content else None
        except Exception:
            payload = r.text

        if not (200 <= r.status_code < 300):
            message = None
            errors = None
            if isinstance(payload, dict):
                message = payload.get("message")
                errors = payload.get("errors")
            raise RuntimeError(json.dumps({
                "status": r.status_code,
                "error": message or (payload if isinstance(payload, str) else str(payload)),
                "errors": errors
            }, ensure_ascii=False))

        # Normalize to a dict envelope with 'data' + '_meta'
        if isinstance(payload, list):
            ret = {"data": payload}
        elif isinstance(payload, dict):
            ret = payload
        elif payload is None:
            ret = {}
        else:
            ret = {"data": payload}

        ret["_meta"] = {
            "status": r.status_code,
            "ratelimit-remaining": r.headers.get("X-RateLimit-Remaining"),
            "ratelimit-reset": r.headers.get("X-RateLimit-Reset"),
            "ratelimit-limit": r.headers.get("X-RateLimit-Limit"),
        }
        return ret

    def _get(self, path: str, params: dict | None = None):
        url = f"{self._api_base()}{path}"
        r = requests.get(url, headers=self._headers(), params=params or {}, timeout=self._timeout())
        return self._handle_response(r)

    def _delete(self, path: str, params: dict | None = None):
        url = f"{self._api_base()}{path}"
        r = requests.delete(url, headers=self._headers(), params=params or {}, timeout=self._timeout())
        return self._handle_response(r)

    def _delete_json(self, path: str, payload: dict | None = None, params: dict | None = None):
        url = f"{self._api_base()}{path}"
        r = requests.delete(
            url,
            headers=self._headers(),
            params=params or {},
            json=payload or {},
            timeout=self._timeout(),
        )
        return self._handle_response(r)

    def _post_json(self, path: str, payload: dict):
        url = f"{self._api_base()}{path}"
        r = requests.post(url, headers=self._headers(), json=payload or {}, timeout=self._timeout())
        return self._handle_response(r)

    def _patch_json(self, path: str, payload: dict):
        url = f"{self._api_base()}{path}"
        r = requests.patch(url, headers=self._headers(), json=payload or {}, timeout=self._timeout())
        return self._handle_response(r)

    def _put_json(self, path: str, payload: dict):
        url = f"{self._api_base()}{path}"
        r = requests.put(url, headers=self._headers(), json=payload or {}, timeout=self._timeout())
        return self._handle_response(r)

    def _now(self) -> int:
        return int(time.time())

    def _b64(self, b: bytes) -> str:
        return base64.b64encode(b).decode("utf-8")

    # ---------------------- Auth: Device Flow (auto) ----------------------

    def _device_begin(self, scopes: str) -> dict:
        url = f"{self._web_base()}/login/device/code"
        data = {"client_id": self.plugin.get_option_value("oauth_client_id") or "", "scope": scopes}
        hdrs = {"Accept": "application/json"}
        r = requests.post(url, data=data, headers=hdrs, timeout=self._timeout())
        if not (200 <= r.status_code < 300):
            raise RuntimeError(f"Device begin failed: HTTP {r.status_code} {r.text}")
        return r.json()

    def _device_poll(self, device_code: str) -> dict:
        url = f"{self._web_base()}/login/oauth/access_token"
        data = {
            "client_id": self.plugin.get_option_value("oauth_client_id") or "",
            "device_code": device_code,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        }
        hdrs = {"Accept": "application/json"}
        r = requests.post(url, data=data, headers=hdrs, timeout=self._timeout())
        if not (200 <= r.status_code < 300):
            raise RuntimeError(f"Device poll failed: HTTP {r.status_code} {r.text}")
        return r.json()

    def _auto_authorize_device(self):
        client_id = (self.plugin.get_option_value("oauth_client_id") or "").strip()
        if not client_id:
            raise RuntimeError("Set oauth_client_id or configure PAT token.")
        scopes = (self.plugin.get_option_value("oauth_scopes") or "repo read:org read:user user:email").strip()
        begin = self._device_begin(scopes)
        verification_uri = begin.get("verification_uri") or "https://github.com/login/device"
        verification_uri_complete = begin.get("verification_uri_complete") or (verification_uri + "?user_code=" + begin.get("user_code", ""))
        interval = int(begin.get("interval") or 5)
        expires_in = int(begin.get("expires_in") or 900)
        # Open browser to complete the flow
        try:
            self.plugin.open_url(verification_uri_complete)
        except Exception:
            pass

        # Polling loop until token received or expired
        start = self._now()
        while self._now() - start < expires_in:
            time.sleep(interval)
            res = self._device_poll(begin["device_code"])
            if res.get("error"):
                if res["error"] in ("authorization_pending", "slow_down"):
                    if res["error"] == "slow_down":
                        interval += 5
                    continue
                if res["error"] in ("expired_token", "access_denied"):
                    raise RuntimeError(f"Device flow aborted: {res['error']}")
            access = res.get("access_token")
            if access:
                self.plugin.set_option_value("gh_access_token", access)
                self.plugin.set_option_value("auth_scheme", (res.get("token_type") or "Bearer").title())
                self.plugin.set_option_value("oauth_scope_granted", res.get("scope") or "")
                # Cache identity
                try:
                    me = self._get("/user")
                    data = me if isinstance(me, dict) else {}
                    d = data.get("data") or data
                    if d.get("id"):
                        self.plugin.set_option_value("user_id", str(d["id"]))
                    if d.get("login"):
                        self.plugin.set_option_value("username", d["login"])
                except Exception:
                    pass
                self.msg = "GitHub: Authorization complete."
                return
        raise RuntimeError("Device flow timeout.")

    # ---------------------- Auth commands ----------------------

    def cmd_gh_device_begin(self, item: dict) -> dict:
        p = item.get("params", {})
        client_id = (self.plugin.get_option_value("oauth_client_id") or "").strip()
        if not client_id:
            return self.make_response(item, "Set oauth_client_id in options first.")
        scopes = p.get("scopes") or (self.plugin.get_option_value("oauth_scopes") or "repo read:org read:user user:email")
        begin = self._device_begin(scopes)
        try:
            if bool(self.plugin.get_option_value("oauth_open_browser") or True):
                self.plugin.open_url(begin.get("verification_uri_complete") or begin.get("verification_uri"))
        except Exception:
            pass
        return self.make_response(item, begin)

    def cmd_gh_device_poll(self, item: dict) -> dict:
        p = item.get("params", {})
        code = p.get("device_code")
        if not code:
            return self.make_response(item, "Param 'device_code' required")
        res = self._device_poll(code)
        if res.get("access_token"):
            self.plugin.set_option_value("gh_access_token", res["access_token"])
            self.plugin.set_option_value("auth_scheme", (res.get("token_type") or "Bearer").title())
            self.plugin.set_option_value("oauth_scope_granted", res.get("scope") or "")
        return self.make_response(item, res)

    def cmd_gh_set_pat(self, item: dict) -> dict:
        p = item.get("params", {})
        tok = (p.get("token") or "").strip()
        if not tok:
            return self.make_response(item, "Param 'token' required")
        self.plugin.set_option_value("pat_token", tok)
        if p.get("scheme"):
            self.plugin.set_option_value("auth_scheme", p["scheme"])
        return self.make_response(item, {"ok": True})

    # ---------------------- Users ----------------------

    def cmd_gh_me(self, item: dict) -> dict:
        res = self._get("/user")
        data = res.get("data") or res
        if data.get("id"):
            self.plugin.set_option_value("user_id", str(data["id"]))
        if data.get("login"):
            self.plugin.set_option_value("username", data["login"])
        return self.make_response(item, res)

    def cmd_gh_user_get(self, item: dict) -> dict:
        p = item.get("params", {})
        username = p.get("username")
        if not username:
            return self.make_response(item, "Param 'username' required")
        res = self._get(f"/users/{quote(username)}")
        return self.make_response(item, res)

    # ---------------------- Repos ----------------------

    def cmd_gh_repos_list(self, item: dict) -> dict:
        p = item.get("params", {})
        username = p.get("username")  # list for a user (public)
        org = p.get("org")
        params = {}
        if p.get("type"):
            params["type"] = p["type"]  # all, owner, member (for /user/repos)
        if p.get("visibility"):
            params["visibility"] = p["visibility"]  # all/public/private
        if p.get("sort"):
            params["sort"] = p["sort"]
        if p.get("direction"):
            params["direction"] = p["direction"]
        if p.get("per_page"):
            params["per_page"] = int(p["per_page"])
        if p.get("page"):
            params["page"] = int(p["page"])

        if org:
            res = self._get(f"/orgs/{quote(org)}/repos", params=params)
        elif username:
            res = self._get(f"/users/{quote(username)}/repos", params=params)
        else:
            res = self._get("/user/repos", params=params)
        return self.make_response(item, res)

    def cmd_gh_repo_get(self, item: dict) -> dict:
        p = item.get("params", {})
        owner = p.get("owner")
        repo = p.get("repo")
        if not (owner and repo):
            return self.make_response(item, "Params 'owner' and 'repo' required")
        res = self._get(f"/repos/{quote(owner)}/{quote(repo)}")
        return self.make_response(item, res)

    def cmd_gh_repo_create(self, item: dict) -> dict:
        p = item.get("params", {})
        name = p.get("name")
        if not name:
            return self.make_response(item, "Param 'name' required")
        payload = {
            "name": name,
            "description": p.get("description"),
            "private": bool(p.get("private", False)),
            "auto_init": bool(p.get("auto_init", True)),
        }
        org = p.get("org")
        if org:
            res = self._post_json(f"/orgs/{quote(org)}/repos", payload)
        else:
            res = self._post_json("/user/repos", payload)
        return self.make_response(item, res)

    def cmd_gh_repo_delete(self, item: dict) -> dict:
        p = item.get("params", {})
        owner = p.get("owner")
        repo = p.get("repo")
        confirm = bool(p.get("confirm", False))
        if not (owner and repo):
            return self.make_response(item, "Params 'owner' and 'repo' required")
        if not confirm:
            return self.make_response(item, "Confirm deletion by setting 'confirm': true")
        res = self._delete(f"/repos/{quote(owner)}/{quote(repo)}")
        return self.make_response(item, res)

    # ---------------------- Contents (files) ----------------------

    def cmd_gh_contents_get(self, item: dict) -> dict:
        p = item.get("params", {})
        owner, repo, path = p.get("owner"), p.get("repo"), (p.get("path") or "")
        if not (owner and repo):
            return self.make_response(item, "Params 'owner' and 'repo' required")
        params = {}
        if p.get("ref"):
            params["ref"] = p["ref"]
        path_enc = "/".join([quote(x) for x in path.strip("/").split("/")]) if path else ""
        res = self._get(f"/repos/{quote(owner)}/{quote(repo)}/contents/{path_enc}", params=params)
        return self.make_response(item, res)

    def _read_local_bytes(self, local_path: str) -> bytes:
        local = self.prepare_path(local_path)
        if not os.path.exists(local):
            raise RuntimeError(f"Local file not found: {local}")
        with open(local, "rb") as fh:
            return fh.read()

    def cmd_gh_file_put(self, item: dict) -> dict:
        p = item.get("params", {})
        owner, repo, path = p.get("owner"), p.get("repo"), p.get("path")
        if not (owner and repo and path):
            return self.make_response(item, "Params 'owner', 'repo', 'path' required")
        message = p.get("message") or f"Update {path}"
        branch = p.get("branch")
        sha = p.get("sha")  # if updating existing file; if not provided, we'll try to resolve
        content_str = p.get("content")
        local_path = p.get("local_path")

        if local_path and not content_str:
            data = self._read_local_bytes(local_path)
        elif content_str is not None:
            data = content_str.encode("utf-8")
        else:
            return self.make_response(item, "Provide 'content' or 'local_path'")

        # Resolve sha if not provided (update vs create)
        if not sha and bool(p.get("resolve_sha", True)):
            try:
                meta = self._get(f"/repos/{quote(owner)}/{quote(repo)}/contents/{quote(path)}", params={"ref": branch} if branch else None)
                md = meta.get("data") or meta
                if isinstance(md, dict) and md.get("sha"):
                    sha = md["sha"]
            except Exception:
                sha = None  # creating new

        payload: Dict[str, Any] = {
            "message": message,
            "content": self._b64(data),
        }
        if sha:
            payload["sha"] = sha
        if branch:
            payload["branch"] = branch
        if p.get("committer"):
            payload["committer"] = p["committer"]  # {"name":"", "email":""}
        if p.get("author"):
            payload["author"] = p["author"]

        res = self._put_json(f"/repos/{quote(owner)}/{quote(repo)}/contents/{quote(path)}", payload)
        return self.make_response(item, res)

    def cmd_gh_file_delete(self, item: dict) -> dict:
        p = item.get("params", {})
        owner, repo, path, message, sha = p.get("owner"), p.get("repo"), p.get("path"), p.get("message"), p.get("sha")
        if not (owner and repo and path and message and sha):
            return self.make_response(item, "Params 'owner','repo','path','message','sha' required")
        payload = {"message": message, "sha": sha}
        if p.get("branch"):
            payload["branch"] = p["branch"]
        # DELETE must carry JSON body
        res = self._delete_json(f"/repos/{quote(owner)}/{quote(repo)}/contents/{quote(path)}", payload=payload)
        return self.make_response(item, res)

    # ---------------------- Issues ----------------------

    def cmd_gh_issues_list(self, item: dict) -> dict:
        p = item.get("params", {})
        owner, repo = p.get("owner"), p.get("repo")
        if not (owner and repo):
            return self.make_response(item, "Params 'owner' and 'repo' required")
        params = {}
        for k in ("state", "labels", "creator", "mentioned", "assignee", "since", "per_page", "page"):
            if p.get(k) is not None:
                params[k] = p[k]
        res = self._get(f"/repos/{quote(owner)}/{quote(repo)}/issues", params=params)
        return self.make_response(item, res)

    def cmd_gh_issue_create(self, item: dict) -> dict:
        p = item.get("params", {})
        owner, repo, title = p.get("owner"), p.get("repo"), p.get("title")
        if not (owner and repo and title):
            return self.make_response(item, "Params 'owner','repo','title' required")
        payload = {"title": title}
        if p.get("body"):
            payload["body"] = p["body"]
        if p.get("assignees"):
            payload["assignees"] = p["assignees"]
        if p.get("labels"):
            payload["labels"] = p["labels"]
        res = self._post_json(f"/repos/{quote(owner)}/{quote(repo)}/issues", payload)
        return self.make_response(item, res)

    def cmd_gh_issue_comment(self, item: dict) -> dict:
        p = item.get("params", {})
        owner, repo, number, body = p.get("owner"), p.get("repo"), p.get("number"), p.get("body")
        if not (owner and repo and number and body):
            return self.make_response(item, "Params 'owner','repo','number','body' required")
        res = self._post_json(f"/repos/{quote(owner)}/{quote(repo)}/issues/{int(number)}/comments", {"body": body})
        return self.make_response(item, res)

    def cmd_gh_issue_close(self, item: dict) -> dict:
        p = item.get("params", {})
        owner, repo, number = p.get("owner"), p.get("repo"), p.get("number")
        if not (owner and repo and number):
            return self.make_response(item, "Params 'owner','repo','number' required")
        res = self._patch_json(f"/repos/{quote(owner)}/{quote(repo)}/issues/{int(number)}", {"state": "closed"})
        return self.make_response(item, res)

    # ---------------------- Pull Requests ----------------------

    def cmd_gh_pulls_list(self, item: dict) -> dict:
        p = item.get("params", {})
        owner, repo = p.get("owner"), p.get("repo")
        if not (owner and repo):
            return self.make_response(item, "Params 'owner' and 'repo' required")
        params = {}
        for k in ("state", "head", "base", "sort", "direction", "per_page", "page"):
            if p.get(k) is not None:
                params[k] = p[k]
        res = self._get(f"/repos/{quote(owner)}/{quote(repo)}/pulls", params=params)
        return self.make_response(item, res)

    def cmd_gh_pull_create(self, item: dict) -> dict:
        p = item.get("params", {})
        owner, repo, title, head, base = p.get("owner"), p.get("repo"), p.get("title"), p.get("head"), p.get("base")
        if not (owner and repo and title and head and base):
            return self.make_response(item, "Params 'owner','repo','title','head','base' required")
        payload = {"title": title, "head": head, "base": base}
        if p.get("body"):
            payload["body"] = p["body"]
        if p.get("draft") is not None:
            payload["draft"] = bool(p["draft"])
        res = self._post_json(f"/repos/{quote(owner)}/{quote(repo)}/pulls", payload)
        return self.make_response(item, res)

    def cmd_gh_pull_merge(self, item: dict) -> dict:
        p = item.get("params", {})
        owner, repo, number = p.get("owner"), p.get("repo"), p.get("number")
        if not (owner and repo and number):
            return self.make_response(item, "Params 'owner','repo','number' required")
        payload = {}
        if p.get("commit_title"):
            payload["commit_title"] = p["commit_title"]
        if p.get("commit_message"):
            payload["commit_message"] = p["commit_message"]
        if p.get("merge_method"):
            payload["merge_method"] = p["merge_method"]  # merge|squash|rebase
        res = self._put_json(f"/repos/{quote(owner)}/{quote(repo)}/pulls/{int(number)}/merge", payload)
        return self.make_response(item, res)

    # ---------------------- Search ----------------------

    def cmd_gh_search_repos(self, item: dict) -> dict:
        p = item.get("params", {})
        q = p.get("q")
        if not q:
            return self.make_response(item, "Param 'q' required")
        params = {"q": q}
        if p.get("sort"):
            params["sort"] = p["sort"]  # stars|forks|help-wanted-issues|updated
        if p.get("order"):
            params["order"] = p["order"]  # desc|asc
        if p.get("per_page"):
            params["per_page"] = int(p["per_page"])
        if p.get("page"):
            params["page"] = int(p["page"])
        res = self._get("/search/repositories", params=params)
        return self.make_response(item, res)

    def cmd_gh_search_issues(self, item: dict) -> dict:
        p = item.get("params", {})
        q = p.get("q")
        if not q:
            return self.make_response(item, "Param 'q' required")
        params = {"q": q}
        if p.get("sort"):
            params["sort"] = p["sort"]  # comments|reactions|reactions-+1|reactions--1|reactions-smile|created|updated
        if p.get("order"):
            params["order"] = p["order"]
        if p.get("per_page"):
            params["per_page"] = int(p["per_page"])
        if p.get("page"):
            params["page"] = int(p["page"])
        res = self._get("/search/issues", params=params)
        return self.make_response(item, res)

    def cmd_gh_search_code(self, item: dict) -> dict:
        p = item.get("params", {})
        q = p.get("q")
        if not q:
            return self.make_response(item, "Param 'q' required")
        params = {"q": q}
        if p.get("per_page"):
            params["per_page"] = int(p["per_page"])
        if p.get("page"):
            params["page"] = int(p["page"])
        res = self._get("/search/code", params=params)
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