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

import json
import mimetypes
import os
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

import requests
from PySide6.QtCore import Slot

from pygpt_net.plugin.base.worker import BaseWorker, BaseSignals


class WorkerSignals(BaseSignals):
    pass


class Worker(BaseWorker):
    """
    Bitbucket Cloud: Auth (Basic App Password or Bearer), Users, Workspaces, Repos,
    Source/Contents (files), Issues, Pull Requests, Search.
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

                        # -------- Auth / Setup --------
                        if item["cmd"] == "bb_auth_set_mode":
                            response = self.cmd_bb_auth_set_mode(item)
                        elif item["cmd"] == "bb_set_app_password":
                            response = self.cmd_bb_set_app_password(item)
                        elif item["cmd"] == "bb_set_bearer":
                            response = self.cmd_bb_set_bearer(item)
                        elif item["cmd"] == "bb_auth_check":
                            response = self.cmd_bb_auth_check(item)

                        # -------- Users / Workspaces --------
                        elif item["cmd"] == "bb_me":
                            response = self.cmd_bb_me(item)
                        elif item["cmd"] == "bb_user_get":
                            response = self.cmd_bb_user_get(item)
                        elif item["cmd"] == "bb_workspaces_list":
                            response = self.cmd_bb_workspaces_list(item)

                        # -------- Repos --------
                        elif item["cmd"] == "bb_repos_list":
                            response = self.cmd_bb_repos_list(item)
                        elif item["cmd"] == "bb_repo_get":
                            response = self.cmd_bb_repo_get(item)
                        elif item["cmd"] == "bb_repo_create":
                            response = self.cmd_bb_repo_create(item)
                        elif item["cmd"] == "bb_repo_delete":
                            response = self.cmd_bb_repo_delete(item)

                        # -------- Contents (files) --------
                        elif item["cmd"] == "bb_contents_get":
                            response = self.cmd_bb_contents_get(item)
                        elif item["cmd"] == "bb_file_put":
                            response = self.cmd_bb_file_put(item)
                        elif item["cmd"] == "bb_file_delete":
                            response = self.cmd_bb_file_delete(item)

                        # -------- Issues --------
                        elif item["cmd"] == "bb_issues_list":
                            response = self.cmd_bb_issues_list(item)
                        elif item["cmd"] == "bb_issue_create":
                            response = self.cmd_bb_issue_create(item)
                        elif item["cmd"] == "bb_issue_comment":
                            response = self.cmd_bb_issue_comment(item)
                        elif item["cmd"] == "bb_issue_update":
                            response = self.cmd_bb_issue_update(item)

                        # -------- Pull Requests --------
                        elif item["cmd"] == "bb_prs_list":
                            response = self.cmd_bb_prs_list(item)
                        elif item["cmd"] == "bb_pr_create":
                            response = self.cmd_bb_pr_create(item)
                        elif item["cmd"] == "bb_pr_merge":
                            response = self.cmd_bb_pr_merge(item)

                        # -------- Search --------
                        elif item["cmd"] == "bb_search_repos":
                            response = self.cmd_bb_search_repos(item)

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
        return (self.plugin.get_option_value("api_base") or "https://api.bitbucket.org/2.0").rstrip("/")

    def _timeout(self) -> int:
        try:
            return int(self.plugin.get_option_value("http_timeout") or 30)
        except Exception:
            return 30

    def _now(self) -> int:
        return int(time.time())

    def _auth_mode(self) -> str:
        # auto | basic | bearer
        mode = (self.plugin.get_option_value("auth_mode") or "auto").strip().lower()
        user = (self.plugin.get_option_value("bb_username") or "").strip()
        app = (self.plugin.get_option_value("bb_app_password") or "").strip()
        tok = (self.plugin.get_option_value("bb_access_token") or "").strip()
        if mode == "basic":
            return "basic"
        if mode == "bearer":
            return "bearer"
        # auto preference: bearer if token present else basic if user+app present
        if tok:
            return "bearer"
        if user and app:
            return "basic"
        return "bearer" if tok else "basic"

    def _requests_auth(self):
        # Let requests handle Basic header generation
        if self._auth_mode() == "basic":
            user = (self.plugin.get_option_value("bb_username") or "").strip()
            pwd = (self.plugin.get_option_value("bb_app_password") or "").strip()
            if not (user and pwd):
                raise RuntimeError("Basic auth selected but username/app_password missing.")
            return (user, pwd)
        return None

    def _headers(self) -> Dict[str, str]:
        hdrs = {
            "Accept": "application/json",
            "User-Agent": "pygpt-net-bitbucket-plugin/1.0",
        }
        if self._auth_mode() == "bearer":
            tok = (self.plugin.get_option_value("bb_access_token") or "").strip()
            if not tok:
                raise RuntimeError("Bearer auth selected but access token missing.")
            hdrs["Authorization"] = f"Bearer {tok}"
        return hdrs

    def _handle_response(self, r: requests.Response) -> dict:
        try:
            data = r.json() if r.content else {}
        except Exception:
            data = {"raw": r.text}

        if r.status_code not in (200, 201, 202, 204):
            # Bitbucket typical error payload: {"error":{"message":"...","detail":"..."}}
            msg = ""
            if isinstance(data, dict):
                err = data.get("error")
                if isinstance(err, dict):
                    msg = err.get("message") or err.get("detail") or ""
                elif isinstance(err, str):
                    msg = err
                else:
                    msg = data.get("message") or data.get("raw") or ""
            payload = {
                "status": r.status_code,
                "error": msg or (r.text or ""),
                "www-authenticate": r.headers.get("WWW-Authenticate"),
            }
            if r.status_code == 401 and self._auth_mode() == "basic":
                u = (self.plugin.get_option_value("bb_username") or "")
                if "@" in u:
                    payload["hint"] = "Use Bitbucket username (handle), not email."
            raise RuntimeError(json.dumps(payload, ensure_ascii=False))

        # Attach meta
        if isinstance(data, dict):
            data["_meta"] = {
                "status": r.status_code,
                "x-rate-remaining": r.headers.get("x-rate-limit-remaining"),
                "x-rate-reset": r.headers.get("x-rate-limit-reset"),
                "x-rate-limit": r.headers.get("x-rate-limit-limit"),
            }
        return data

    def _get(self, path: str, params: dict | None = None):
        url = f"{self._api_base()}{path}"
        r = requests.get(url, headers=self._headers(), params=params or {}, timeout=self._timeout(), auth=self._requests_auth())
        return self._handle_response(r)

    def _delete(self, path: str, params: dict | None = None):
        url = f"{self._api_base()}{path}"
        r = requests.delete(url, headers=self._headers(), params=params or {}, timeout=self._timeout(), auth=self._requests_auth())
        return self._handle_response(r)

    def _post_json(self, path: str, payload: dict, params: dict | None = None):
        url = f"{self._api_base()}{path}"
        r = requests.post(url, headers=self._headers(), params=params or {}, json=payload or {}, timeout=self._timeout(), auth=self._requests_auth())
        return self._handle_response(r)

    def _put_json(self, path: str, payload: dict, params: dict | None = None):
        url = f"{self._api_base()}{path}"
        r = requests.put(url, headers=self._headers(), params=params or {}, json=payload or {}, timeout=self._timeout(), auth=self._requests_auth())
        return self._handle_response(r)

    def _post_form(self, path: str, data: dict | List[tuple] | None = None, files: dict | None = None):
        url = f"{self._api_base()}{path}"
        r = requests.post(url, headers=self._headers(), data=data, files=files, timeout=self._timeout(), auth=self._requests_auth())
        return self._handle_response(r)

    def _guess_mime(self, path: str) -> str:
        mt, _ = mimetypes.guess_type(path)
        return mt or "application/octet-stream"

    # ---------------------- Auth commands ----------------------

    def cmd_bb_auth_set_mode(self, item: dict) -> dict:
        p = item.get("params", {})
        mode = (p.get("mode") or "").strip().lower()
        if mode not in ("auto", "basic", "bearer"):
            return self.make_response(item, "Param 'mode' must be: auto|basic|bearer")
        self.plugin.set_option_value("auth_mode", mode)
        return self.make_response(item, {"ok": True, "mode": mode})

    def cmd_bb_set_app_password(self, item: dict) -> dict:
        p = item.get("params", {})
        user = (p.get("username") or "").strip()
        app = (p.get("app_password") or "").strip()
        if not (user and app):
            return self.make_response(item, "Params 'username' and 'app_password' required")
        self.plugin.set_option_value("bb_username", user)
        self.plugin.set_option_value("bb_app_password", app)
        if p.get("set_mode"):
            self.plugin.set_option_value("auth_mode", "basic")
        return self.make_response(item, {"ok": True, "mode": self._auth_mode()})

    def cmd_bb_set_bearer(self, item: dict) -> dict:
        p = item.get("params", {})
        tok = (p.get("access_token") or "").strip()
        if not tok:
            return self.make_response(item, "Param 'access_token' required")
        self.plugin.set_option_value("bb_access_token", tok)
        if p.get("set_mode"):
            self.plugin.set_option_value("auth_mode", "bearer")
        return self.make_response(item, {"ok": True, "mode": self._auth_mode()})

    def cmd_bb_auth_check(self, item: dict) -> dict:
        # Simple /user ping with current mode
        try:
            res = self._get("/user")
            # Cache username if present
            data = res.get("data") or res
            if isinstance(data, dict):
                uu = data.get("uuid") or (data.get("user") or {}).get("uuid")
                un = data.get("username") or data.get("nickname")
                if uu:
                    self.plugin.set_option_value("user_uuid", uu)
                if un:
                    self.plugin.set_option_value("username", un)
            return self.make_response(item, {"ok": True, "mode": self._auth_mode(), "user": res})
        except Exception as e:
            return self.make_response(item, self.throw_error(e))

    # ---------------------- Users / Workspaces ----------------------

    def cmd_bb_me(self, item: dict) -> dict:
        res = self._get("/user")
        data = res.get("data") or res
        if isinstance(data, dict):
            if data.get("uuid"):
                self.plugin.set_option_value("user_uuid", data["uuid"])
            if data.get("username"):
                self.plugin.set_option_value("username", data["username"])
        return self.make_response(item, res)

    def cmd_bb_user_get(self, item: dict) -> dict:
        p = item.get("params", {})
        username = p.get("username")
        if not username:
            return self.make_response(item, "Param 'username' required")
        res = self._get(f"/users/{quote(username)}")
        return self.make_response(item, res)

    def cmd_bb_workspaces_list(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        params = {}
        if p.get("page"): params["page"] = int(p["page"])
        if p.get("pagelen"): params["pagelen"] = int(p["pagelen"])
        res = self._get("/workspaces", params=params)
        return self.make_response(item, res)

    # ---------------------- Repositories ----------------------

    def cmd_bb_repos_list(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        workspace = p.get("workspace")
        params = {}
        for k in ("role", "q", "sort", "page", "pagelen", "after"):
            if p.get(k) is not None:
                params[k] = p[k]
        if workspace:
            res = self._get(f"/repositories/{quote(workspace)}", params=params)
        else:
            res = self._get("/repositories", params=params)
        return self.make_response(item, res)

    def cmd_bb_repo_get(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        ws, repo = p.get("workspace"), p.get("repo")
        if not (ws and repo):
            return self.make_response(item, "Params 'workspace' and 'repo' required")
        res = self._get(f"/repositories/{quote(ws)}/{quote(repo)}")
        return self.make_response(item, res)

    def cmd_bb_repo_create(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        ws, repo = p.get("workspace"), p.get("repo")
        if not (ws and repo):
            return self.make_response(item, "Params 'workspace' and 'repo' required")
        payload: Dict[str, Any] = {
            "scm": p.get("scm") or "git",
            "is_private": bool(p.get("is_private", True)),
        }
        if p.get("description"): payload["description"] = p["description"]
        if p.get("project_key"): payload["project"] = {"key": p["project_key"]}
        res = self._post_json(f"/repositories/{quote(ws)}/{quote(repo)}", payload)
        return self.make_response(item, res)

    def cmd_bb_repo_delete(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        ws, repo = p.get("workspace"), p.get("repo")
        confirm = bool(p.get("confirm", False))
        if not (ws and repo):
            return self.make_response(item, "Params 'workspace' and 'repo' required")
        if not confirm:
            return self.make_response(item, "Confirm deletion by setting 'confirm': true")
        res = self._delete(f"/repositories/{quote(ws)}/{quote(repo)}")
        return self.make_response(item, res)

    # ---------------------- Contents (Source API) ----------------------

    def cmd_bb_contents_get(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        ws, repo = p.get("workspace"), p.get("repo")
        if not (ws and repo):
            return self.make_response(item, "Params 'workspace' and 'repo' required")
        path = (p.get("path") or "").strip().strip("/")
        ref = (p.get("ref") or "").strip()
        params: Dict[str, Any] = {}
        if p.get("format"): params["format"] = p["format"]  # meta|rendered
        if p.get("q"): params["q"] = p["q"]
        if p.get("sort"): params["sort"] = p["sort"]
        if p.get("max_depth") is not None: params["max_depth"] = int(p["max_depth"])
        if ref and path:
            res = self._get(f"/repositories/{quote(ws)}/{quote(repo)}/src/{quote(ref)}/{path}", params=params)
        elif ref and not path:
            res = self._get(f"/repositories/{quote(ws)}/{quote(repo)}/src/{quote(ref)}", params=params)
        elif path:
            res = self._get(f"/repositories/{quote(ws)}/{quote(repo)}/src/{path}", params=params)
        else:
            res = self._get(f"/repositories/{quote(ws)}/{quote(repo)}/src", params=params)
        return self.make_response(item, res)

    def _read_local_bytes(self, local_path: str) -> bytes:
        local = self.prepare_path(local_path)
        if not os.path.exists(local):
            raise RuntimeError(f"Local file not found: {local}")
        with open(local, "rb") as fh:
            return fh.read()

    def cmd_bb_file_put(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        ws, repo, remote_path = p.get("workspace"), p.get("repo"), p.get("path")
        if not (ws and repo and remote_path):
            return self.make_response(item, "Params 'workspace','repo','path' required")
        message = p.get("message") or f"Update {remote_path}"
        branch = p.get("branch")
        parents = p.get("parents")
        content_str = p.get("content")
        local_path = p.get("local_path")

        files = None
        data: Dict[str, Any] | List[tuple]
        if local_path:
            data_pairs: List[tuple] = [("message", message)]
            if branch: data_pairs.append(("branch", branch))
            if parents: data_pairs.append(("parents", parents))
            b = self._read_local_bytes(local_path)
            mime = self._guess_mime(local_path)
            files = {remote_path: (os.path.basename(local_path), b, mime)}
            data = data_pairs
        elif content_str is not None:
            data = {remote_path: content_str, "message": message}
            if branch: data["branch"] = branch
            if parents: data["parents"] = parents
        else:
            return self.make_response(item, "Provide 'content' or 'local_path'")

        res = self._post_form(f"/repositories/{quote(ws)}/{quote(repo)}/src", data=data, files=files)
        return self.make_response(item, res)

    def cmd_bb_file_delete(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        ws, repo = p.get("workspace"), p.get("repo")
        paths = p.get("paths") or p.get("path")
        if isinstance(paths, str): paths = [paths]
        if not (ws and repo and paths):
            return self.make_response(item, "Params 'workspace','repo','paths' required")
        message = p.get("message") or "Delete files"
        branch = p.get("branch")
        parents = p.get("parents")
        data: List[tuple] = [("message", message)]
        if branch: data.append(("branch", branch))
        if parents: data.append(("parents", parents))
        for path in paths:
            data.append(("files", path))
        res = self._post_form(f"/repositories/{quote(ws)}/{quote(repo)}/src", data=data)
        return self.make_response(item, res)

    # ---------------------- Issues ----------------------

    def cmd_bb_issues_list(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        ws, repo = p.get("workspace"), p.get("repo")
        if not (ws and repo):
            return self.make_response(item, "Params 'workspace' and 'repo' required")
        params: Dict[str, Any] = {}
        for k in ("q", "sort", "page", "pagelen"):
            if p.get(k) is not None: params[k] = p[k]
        if p.get("state"):
            q = params.get("q", "")
            clause = f'state="{p["state"]}"'
            params["q"] = f"{q} AND {clause}" if q else clause
        res = self._get(f"/repositories/{quote(ws)}/{quote(repo)}/issues", params=params)
        return self.make_response(item, res)

    def cmd_bb_issue_create(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        ws, repo, title = p.get("workspace"), p.get("repo"), p.get("title")
        if not (ws and repo and title):
            return self.make_response(item, "Params 'workspace','repo','title' required")
        payload: Dict[str, Any] = {"title": title}
        if p.get("content"): payload["content"] = {"raw": p["content"]}
        if p.get("assignee"): payload["assignee"] = {"username": p["assignee"]}
        res = self._post_json(f"/repositories/{quote(ws)}/{quote(repo)}/issues", payload)
        return self.make_response(item, res)

    def cmd_bb_issue_comment(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        ws, repo, iid, content = p.get("workspace"), p.get("repo"), p.get("id"), p.get("content")
        if not (ws and repo and iid and content):
            return self.make_response(item, "Params 'workspace','repo','id','content' required")
        payload = {"content": {"raw": content}}
        res = self._post_json(f"/repositories/{quote(ws)}/{quote(repo)}/issues/{int(iid)}/comments", payload)
        return self.make_response(item, res)

    def cmd_bb_issue_update(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        ws, repo, iid = p.get("workspace"), p.get("repo"), p.get("id")
        if not (ws and repo and iid):
            return self.make_response(item, "Params 'workspace','repo','id' required")
        payload: Dict[str, Any] = {}
        if p.get("state"): payload["state"] = p["state"]
        if p.get("title"): payload["title"] = p["title"]
        if p.get("content"): payload["content"] = {"raw": p["content"]}
        res = self._put_json(f"/repositories/{quote(ws)}/{quote(repo)}/issues/{int(iid)}", payload)
        return self.make_response(item, res)

    # ---------------------- Pull Requests ----------------------

    def cmd_bb_prs_list(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        ws, repo = p.get("workspace"), p.get("repo")
        if not (ws and repo):
            return self.make_response(item, "Params 'workspace' and 'repo' required")
        params: Dict[str, Any] = {}
        for k in ("state", "page", "pagelen", "q", "sort"):
            if p.get(k) is not None: params[k] = p[k]
        res = self._get(f"/repositories/{quote(ws)}/{quote(repo)}/pullrequests", params=params)
        return self.make_response(item, res)

    def cmd_bb_pr_create(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        ws, repo = p.get("workspace"), p.get("repo")
        title, src, dst = p.get("title"), p.get("source_branch"), p.get("destination_branch")
        if not (ws and repo and title and src and dst):
            return self.make_response(item, "Params 'workspace','repo','title','source_branch','destination_branch' required")
        payload: Dict[str, Any] = {
            "title": title,
            "source": {"branch": {"name": src}},
            "destination": {"branch": {"name": dst}},
        }
        if p.get("description"): payload["description"] = p["description"]
        if p.get("draft") is not None: payload["draft"] = bool(p["draft"])
        res = self._post_json(f"/repositories/{quote(ws)}/{quote(repo)}/pullrequests", payload)
        return self.make_response(item, res)

    def cmd_bb_pr_merge(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        ws, repo, pr_id = p.get("workspace"), p.get("repo"), p.get("id")
        if not (ws and repo and pr_id):
            return self.make_response(item, "Params 'workspace','repo','id' required")
        payload: Dict[str, Any] = {}
        if p.get("message"): payload["message"] = p["message"]
        if p.get("close_source_branch") is not None: payload["close_source_branch"] = bool(p["close_source_branch"])
        res = self._post_json(f"/repositories/{quote(ws)}/{quote(repo)}/pullrequests/{int(pr_id)}/merge", payload)
        return self.make_response(item, res)

    # ---------------------- Search ----------------------

    def cmd_bb_search_repos(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        params: Dict[str, Any] = {}
        if p.get("q"): params["q"] = p["q"]  # BBQL
        if p.get("sort"): params["sort"] = p["sort"]
        if p.get("page"): params["page"] = int(p["page"])
        if p.get("pagelen"): params["pagelen"] = int(p["pagelen"])
        res = self._get("/repositories", params=params)
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