#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.18 00:25:36                  #
# ================================================== #

from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Dict, List, Optional
from urllib.parse import quote  # kept for parity, not strictly needed everywhere

import requests
from PySide6.QtCore import Slot

from pygpt_net.plugin.base.worker import BaseWorker, BaseSignals


class WorkerSignals(BaseSignals):
    pass


class Worker(BaseWorker):
    """
    Wolfram Alpha plugin worker: Short answers, Full JSON query, Math compute,
    Solve equations, Derivatives, Integrals, Unit conversions, Matrix ops, Plots.
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

                        # Generic query endpoints
                        if item["cmd"] == "wa_short":
                            response = self.cmd_wa_short(item)
                        elif item["cmd"] == "wa_spoken":
                            response = self.cmd_wa_spoken(item)
                        elif item["cmd"] == "wa_simple":
                            response = self.cmd_wa_simple(item)
                        elif item["cmd"] == "wa_query":
                            response = self.cmd_wa_query(item)

                        # Convenience math commands
                        elif item["cmd"] == "wa_calculate":
                            response = self.cmd_wa_calculate(item)
                        elif item["cmd"] == "wa_solve":
                            response = self.cmd_wa_solve(item)
                        elif item["cmd"] == "wa_derivative":
                            response = self.cmd_wa_derivative(item)
                        elif item["cmd"] == "wa_integral":
                            response = self.cmd_wa_integral(item)
                        elif item["cmd"] == "wa_units_convert":
                            response = self.cmd_wa_units_convert(item)
                        elif item["cmd"] == "wa_matrix":
                            response = self.cmd_wa_matrix(item)
                        elif item["cmd"] == "wa_plot":
                            response = self.cmd_wa_plot(item)

                        if response is not None:
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
        return (self.plugin.get_option_value("api_base") or "https://api.wolframalpha.com").rstrip("/")

    def _timeout(self) -> int:
        try:
            return int(self.plugin.get_option_value("http_timeout") or 30)
        except Exception:
            return 30

    def _appid(self) -> str:
        appid = (self.plugin.get_option_value("wa_appid") or "").strip()
        if not appid:
            raise RuntimeError("Missing Wolfram Alpha AppID (set 'wa_appid' in plugin options).")
        return appid

    def _units(self) -> Optional[str]:
        units = (self.plugin.get_option_value("units") or "").strip().lower()
        return units if units in ("metric", "nonmetric") else None

    def _headers(self) -> Dict[str, str]:
        return {
            "User-Agent": "pygpt-net-wolframalpha-plugin/1.0",
            "Accept": "*/*",
        }

    def _get_raw(self, path: str, params: dict | None = None) -> requests.Response:
        url = f"{self._api_base()}{path}"
        r = requests.get(url, headers=self._headers(), params=params or {}, timeout=self._timeout())
        return r

    def _handle_json(self, r: requests.Response) -> dict:
        # For /v2/query?output=json
        try:
            payload = r.json() if r.content else None
        except Exception:
            payload = r.text

        if not (200 <= r.status_code < 300):
            message = payload if isinstance(payload, str) else None
            raise RuntimeError(json.dumps({
                "status": r.status_code,
                "error": message or "HTTP error",
            }, ensure_ascii=False))

        # Normalize
        if isinstance(payload, dict):
            ret = payload
        else:
            ret = {"data": payload}

        ret["_meta"] = {
            "status": r.status_code,
            "content_type": r.headers.get("Content-Type"),
        }
        return ret

    def _handle_text(self, r: requests.Response) -> dict:
        # For short/spoken result endpoints
        txt = r.text if r.content else ""
        if not (200 <= r.status_code < 300):
            # WA short endpoints may return 501 if no concise answer
            return {
                "ok": False,
                "status": r.status_code,
                "text": txt,
                "_meta": {"content_type": r.headers.get("Content-Type")},
            }
        return {
            "ok": True,
            "status": r.status_code,
            "text": txt,
            "_meta": {"content_type": r.headers.get("Content-Type")},
        }

    def _save_bytes(self, data: bytes, out_path: str) -> str:
        local = self.prepare_path(out_path)
        os.makedirs(os.path.dirname(local), exist_ok=True)
        with open(local, "wb") as fh:
            fh.write(data)
        return local

    def _slug(self, s: str, maxlen: int = 80) -> str:
        s = re.sub(r"\s+", "_", s.strip())
        s = re.sub(r"[^a-zA-Z0-9_\-\.]", "", s)
        return (s[:maxlen] or "plot").strip("._-") or "plot"

    def _now(self) -> int:
        return int(time.time())

    def prepare_path(self, path: str) -> str:
        if path in [".", "./"]:
            return self.plugin.window.core.config.get_user_dir("data")
        if self.is_absolute_path(path):
            return path
        return os.path.join(self.plugin.window.core.config.get_user_dir("data"), path)

    def is_absolute_path(self, path: str) -> bool:
        return os.path.isabs(path)

    # ---------------------- Parsing helpers ----------------------

    def _extract_primary_plaintext(self, query_json: dict) -> Optional[str]:
        try:
            qr = query_json.get("queryresult") or {}
            pods = qr.get("pods") or []
            # Prefer primary pod
            for p in pods:
                if p.get("primary"):
                    texts = [sp.get("plaintext") for sp in (p.get("subpods") or []) if sp.get("plaintext")]
                    if texts:
                        return "\n".join(texts)
            # Fallback to common pod titles
            prefer_ids = {"Result", "Results", "ExactResult", "Exact result", "Decimal approximation", "Solution", "Solutions"}
            for p in pods:
                if (p.get("id") in prefer_ids) or (p.get("title") in prefer_ids):
                    texts = [sp.get("plaintext") for sp in (p.get("subpods") or []) if sp.get("plaintext")]
                    if texts:
                        return "\n".join(texts)
            # Last resort: first plaintext
            for p in pods:
                for sp in (p.get("subpods") or []):
                    if sp.get("plaintext"):
                        return sp["plaintext"]
        except Exception:
            pass
        return None

    def _matrix_literal(self, matrix: List[List[Any]]) -> str:
        rows = []
        for row in matrix:
            row_str = ",".join(str(x) for x in row)
            rows.append("{" + row_str + "}")
        return "{" + ",".join(rows) + "}"

    # ---------------------- Internal cross-call helper ----------------------

    def _call_cmd(self, cmd: str, params: dict) -> dict:
        """Call another command inside this worker with a proper envelope so make_response() works."""
        fn = getattr(self, f"cmd_{cmd}", None)
        if not callable(fn):
            raise RuntimeError(f"Unknown command: {cmd}")
        return fn({"cmd": cmd, "params": params})

    def _add_image(self, path: str):
        """Register saved image path in context for downstream UI/use."""
        try:
            if self.ctx is None:
                return
            if path:
                path = self.plugin.window.core.filesystem.to_workdir(path)
            # Ensure list exists
            if not hasattr(self.ctx, "images_before") or self.ctx.images_before is None:
                self.ctx.images_before = []
            # Avoid duplicates
            if path and path not in self.ctx.images_before:
                self.ctx.images_before.append(path)
        except Exception:
            # Keep silent: context may not be attached in some runs/tests
            pass

    # ---------------------- Endpoint commands ----------------------

    def cmd_wa_short(self, item: dict) -> dict:
        p = item.get("params", {})
        query = p.get("query") or p.get("i")
        if not query:
            return self.make_response(item, "Param 'query' required")
        params = {"appid": self._appid(), "i": query}
        units = self._units()
        if units:
            params["units"] = units
        r = self._get_raw("/v2/result", params=params)
        res = self._handle_text(r)
        return self.make_response(item, res)

    def cmd_wa_spoken(self, item: dict) -> dict:
        p = item.get("params", {})
        query = p.get("query") or p.get("i")
        if not query:
            return self.make_response(item, "Param 'query' required")
        params = {"appid": self._appid(), "i": query}
        units = self._units()
        if units:
            params["units"] = units
        r = self._get_raw("/v1/spoken", params=params)
        res = self._handle_text(r)
        return self.make_response(item, res)

    def cmd_wa_simple(self, item: dict) -> dict:
        p = item.get("params", {})
        query = p.get("query") or p.get("i")
        out = p.get("out")  # suggested file path relative to data dir
        if not query:
            return self.make_response(item, "Param 'query' required")
        params = {"appid": self._appid(), "i": query}
        units = self._units()
        if units:
            params["units"] = units
        # Optional presentation params
        bg = (p.get("background") or self.plugin.get_option_value("simple_background") or "white").lower()
        if bg in ("white", "transparent"):
            params["background"] = bg
        layout = (p.get("layout") or self.plugin.get_option_value("simple_layout") or "labelbar").lower()
        params["layout"] = layout
        width = p.get("width") or self.plugin.get_option_value("simple_width")
        if width:
            params["width"] = int(width)

        r = self._get_raw("/v2/simple", params=params)
        if not (200 <= r.status_code < 300):
            return self.make_response(item, {
                "ok": False,
                "status": r.status_code,
                "error": r.text,
                "_meta": {"content_type": r.headers.get("Content-Type")},
            })
        # Save image
        ext = "gif"
        ctype = r.headers.get("Content-Type", "")
        if "png" in ctype:
            ext = "png"
        elif "jpeg" in ctype or "jpg" in ctype:
            ext = "jpg"
        if not out:
            fname = f"wa_simple_{self._slug(query, 60)}_{self._now()}.{ext}"
            out = os.path.join("wolframalpha", fname)
        local = self._save_bytes(r.content, out)
        # register image in context
        self._add_image(local)
        return self.make_response(item, {
            "ok": True,
            "file": local,
            "_meta": {"status": r.status_code, "content_type": ctype},
        })

    def cmd_wa_query(self, item: dict) -> dict:
        p = item.get("params", {})
        query = p.get("query") or p.get("input")
        if not query:
            return self.make_response(item, "Param 'query' required")
        params: Dict[str, Any] = {
            "appid": self._appid(),
            "input": query,
            "output": "json",
            "format": p.get("format") or "plaintext,image",
        }
        units = self._units()
        if units:
            params["units"] = units
        if p.get("podstate"):
            params["podstate"] = p["podstate"]
        # Timeouts
        if p.get("scantimeout") is not None:
            params["scantimeout"] = int(p["scantimeout"])
        if p.get("podtimeout") is not None:
            params["podtimeout"] = int(p["podtimeout"])
        # Size
        if p.get("maxwidth") is not None:
            params["maxwidth"] = int(p["maxwidth"])

        assumptions = p.get("assumptions") or []
        base_url = f"{self._api_base()}/v2/query"
        req_params = []
        for k, v in params.items():
            req_params.append((k, v))
        if isinstance(assumptions, list):
            for a in assumptions:
                req_params.append(("assumption", a))

        r = requests.get(base_url, headers=self._headers(), params=req_params, timeout=self._timeout())
        data = self._handle_json(r)

        # Optional image download from pods
        if p.get("download_images"):
            max_images = int(p.get("max_images") or 10)
            saved: List[Dict[str, Any]] = []
            try:
                pods = (data.get("queryresult") or {}).get("pods") or []
                cnt = 0
                for pod in pods:
                    for sp in (pod.get("subpods") or []):
                        img = sp.get("img")
                        if img and img.get("src"):
                            if cnt >= max_images:
                                break
                            img_url = img["src"]
                            ir = requests.get(img_url, headers=self._headers(), timeout=self._timeout())
                            if 200 <= ir.status_code < 300:
                                ctype = ir.headers.get("Content-Type") or ""
                                ext = "png" if "png" in ctype else ("jpg" if ("jpeg" in ctype or "jpg" in ctype) else "gif")
                                fname = f"wa_pod_{self._slug(pod.get('id') or pod.get('title') or 'pod')}_{cnt}_{self._now()}.{ext}"
                                local = self._save_bytes(ir.content, os.path.join("wolframalpha", fname))
                                saved.append({"pod": pod.get("id") or pod.get("title"), "file": local})
                                # register image in context
                                self._add_image(local)
                                cnt += 1
                    if cnt >= max_images:
                        break
            except Exception:
                pass
            data["_downloaded_images"] = saved

        # Convenience primary plaintext
        primary = self._extract_primary_plaintext(data)
        if primary is not None:
            data["_primary_plaintext"] = primary

        return self.make_response(item, data)

    # ---------------------- Convenience math commands ----------------------

    def cmd_wa_calculate(self, item: dict) -> dict:
        p = item.get("params", {})
        expr = p.get("expr") or p.get("expression") or p.get("query")
        if not expr:
            return self.make_response(item, "Param 'expr' required")
        # Try short answer first
        short = self._call_cmd("wa_short", {"query": expr})
        sdata = short.get("data") or short
        if isinstance(sdata, dict) and sdata.get("ok"):
            return self.make_response(item, {"expr": expr, "result": sdata.get("text"), "_via": "short"})
        # Fallback to full JSON
        full = self._call_cmd("wa_query", {"query": expr})
        fdata = full.get("data") or full
        if isinstance(fdata, dict):
            primary = fdata.get("_primary_plaintext")
            if primary:
                return self.make_response(item, {"expr": expr, "result": primary, "_via": "query"})
        return self.make_response(item, {"expr": expr, "error": "No result"})

    def cmd_wa_solve(self, item: dict) -> dict:
        p = item.get("params", {})
        eq = p.get("equation") or p.get("eq")
        eqs = p.get("equations") or []
        var = p.get("var") or p.get("variable")
        vars_ = p.get("vars") or p.get("variables") or []
        domain = p.get("domain")  # reals|integers|complexes
        if not (eq or eqs):
            return self.make_response(item, "Param 'equation' or 'equations' required")
        if isinstance(eqs, list) and eq:
            eqs = [eq] + eqs
        elif not isinstance(eqs, list) and eq:
            eqs = [eq]
        if vars_ and not isinstance(vars_, list):
            vars_ = [vars_]
        if var and var not in vars_:
            vars_.append(var)
        vars_part = f" for {{{', '.join(vars_)}}}" if vars_ else ""
        dom_part = f" over the {domain}" if domain else ""
        query = f"solve {{{'; '.join(eqs)}}}{vars_part}{dom_part}"
        res = self._call_cmd("wa_query", {"query": query})
        data = res.get("data") or res
        if isinstance(data, dict) and data.get("_primary_plaintext"):
            return self.make_response(item, {"query": query, "solution": data["_primary_plaintext"], "_raw": data})
        return self.make_response(item, {"query": query, "error": "No solution", "_raw": data})

    def cmd_wa_derivative(self, item: dict) -> dict:
        p = item.get("params", {})
        expr = p.get("expr") or p.get("expression")
        var = p.get("var") or "x"
        order = int(p.get("order") or 1)
        at = p.get("at")  # e.g., "x=0"
        if not expr:
            return self.make_response(item, "Param 'expr' required")
        q = f"derivative order {order} of ({expr}) with respect to {var}"
        if at:
            q += f" at {at}"
        res = self._call_cmd("wa_query", {"query": q})
        data = res.get("data") or res
        if isinstance(data, dict) and data.get("_primary_plaintext"):
            return self.make_response(item, {"query": q, "derivative": data["_primary_plaintext"], "_raw": data})
        return self.make_response(item, {"query": q, "error": "No result", "_raw": data})

    def cmd_wa_integral(self, item: dict) -> dict:
        p = item.get("params", {})
        expr = p.get("expr") or p.get("expression")
        var = p.get("var") or "x"
        a = p.get("a")
        b = p.get("b")
        if not expr:
            return self.make_response(item, "Param 'expr' required")
        if a is not None and b is not None:
            q = f"integrate ({expr}) with respect to {var} from {a} to {b}"
        else:
            q = f"integrate ({expr}) with respect to {var}"
        res = self._call_cmd("wa_query", {"query": q})
        data = res.get("data") or res
        if isinstance(data, dict) and data.get("_primary_plaintext"):
            return self.make_response(item, {"query": q, "integral": data["_primary_plaintext"], "_raw": data})
        return self.make_response(item, {"query": q, "error": "No result", "_raw": data})

    def cmd_wa_units_convert(self, item: dict) -> dict:
        p = item.get("params", {})
        value = p.get("value")
        from_unit = p.get("from")
        to_unit = p.get("to")
        if value is None or not from_unit or not to_unit:
            return self.make_response(item, "Params 'value','from','to' required")
        q = f"convert {value} {from_unit} to {to_unit}"
        res = self._call_cmd("wa_query", {"query": q})
        data = res.get("data") or res
        if isinstance(data, dict) and data.get("_primary_plaintext"):
            return self.make_response(item, {"query": q, "conversion": data["_primary_plaintext"], "_raw": data})
        # Try short if no plaintext
        short = self._call_cmd("wa_short", {"query": q})
        sdata = short.get("data") or short
        if isinstance(sdata, dict) and sdata.get("ok"):
            return self.make_response(item, {"query": q, "conversion": sdata.get("text"), "_via": "short"})
        return self.make_response(item, {"query": q, "error": "No result", "_raw": data})

    def cmd_wa_matrix(self, item: dict) -> dict:
        p = item.get("params", {})
        op = (p.get("op") or "determinant").lower()  # determinant|inverse|eigenvalues|rank
        matrix = p.get("matrix")
        if not (matrix and isinstance(matrix, list) and all(isinstance(r, list) for r in matrix)):
            return self.make_response(item, "Param 'matrix' must be list of lists")
        literal = self._matrix_literal(matrix)
        if op == "determinant":
            q = f"determinant {literal}"
        elif op == "inverse":
            q = f"inverse {literal}"
        elif op == "eigenvalues":
            q = f"eigenvalues {literal}"
        elif op == "rank":
            q = f"rank {literal}"
        else:
            q = f"{op} {literal}"
        res = self._call_cmd("wa_query", {"query": q})
        data = res.get("data") or res
        if isinstance(data, dict) and data.get("_primary_plaintext"):
            return self.make_response(item, {"query": q, "result": data["_primary_plaintext"], "_raw": data})
        return self.make_response(item, {"query": q, "error": "No result", "_raw": data})

    def cmd_wa_plot(self, item: dict) -> dict:
        p = item.get("params", {})
        func = p.get("func") or p.get("f") or p.get("function")
        var = p.get("var") or "x"
        a = p.get("a")
        b = p.get("b")
        out = p.get("out")
        if not func:
            return self.make_response(item, "Param 'func' required")
        if a is not None and b is not None:
            q = f"plot {func} for {var} from {a} to {b}"
        else:
            q = f"plot {func}"
        # Use Simple API to get a ready image
        simple_res = self._call_cmd("wa_simple", {"query": q, "out": out})
        return self.make_response(item, simple_res.get("data") or simple_res)