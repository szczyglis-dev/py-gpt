#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.27 20:18:26                  #
# ================================================== #

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import Slot
from pygpt_net.plugin.base.worker import BaseWorker, BaseSignals

# Lazy import
try:
    import wikipedia as wiki
    from wikipedia.exceptions import (
        DisambiguationError,
        PageError,
        RedirectError,
        HTTPTimeoutError,
        WikipediaException,
    )
except Exception:  # fallback mapping for type hints
    wiki = None
    DisambiguationError = PageError = RedirectError = HTTPTimeoutError = WikipediaException = Exception  # type: ignore


class WorkerSignals(BaseSignals):
    pass


class Worker(BaseWorker):
    """
    Wikipedia plugin worker: language, search, suggest, summary, page, section, random, geosearch, open.
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
            self._apply_settings()  # sync module settings with plugin options
            for item in self.cmds:
                if self.is_stopped():
                    break
                try:
                    response = None
                    if item["cmd"] in self.plugin.allowed_cmds and self.plugin.has_cmd(item["cmd"]):

                        # -------- Language --------
                        if item["cmd"] == "wp_set_lang":
                            response = self.cmd_wp_set_lang(item)
                        elif item["cmd"] == "wp_get_lang":
                            response = self.cmd_wp_get_lang(item)
                        elif item["cmd"] == "wp_languages":
                            response = self.cmd_wp_languages(item)

                        # -------- Search / Suggest --------
                        elif item["cmd"] == "wp_search":
                            response = self.cmd_wp_search(item)
                        elif item["cmd"] == "wp_suggest":
                            response = self.cmd_wp_suggest(item)

                        # -------- Read --------
                        elif item["cmd"] == "wp_summary":
                            response = self.cmd_wp_summary(item)
                        elif item["cmd"] == "wp_page":
                            response = self.cmd_wp_page(item)
                        elif item["cmd"] == "wp_section":
                            response = self.cmd_wp_section(item)

                        # -------- Discover --------
                        elif item["cmd"] == "wp_random":
                            response = self.cmd_wp_random(item)
                        elif item["cmd"] == "wp_geosearch":
                            response = self.cmd_wp_geosearch(item)

                        # -------- Utilities --------
                        elif item["cmd"] == "wp_open":
                            response = self.cmd_wp_open(item)

                        if response:
                            responses.append(response)

                except DisambiguationError as e:
                    responses.append(self.make_response(item, self._wrap_disambig(e)))
                except (PageError, RedirectError, HTTPTimeoutError, WikipediaException) as e:
                    responses.append(self.make_response(item, self.throw_error(e)))
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

    # ---------------------- Helpers ----------------------

    def _require_lib(self):
        if wiki is None:
            raise RuntimeError("Missing 'wikipedia' package. Install with: pip install wikipedia")

    def _apply_settings(self):
        self._require_lib()
        # Keep module-level settings in sync with plugin options
        lang = (self.plugin.get_option_value("lang") or "en").strip()
        auto_rate = bool(self.plugin.get_option_value("rate_limit") or True)
        ua = (self.plugin.get_option_value("user_agent") or "").strip()
        try:
            wiki.set_lang(lang)
        except Exception:
            pass
        try:
            wiki.set_rate_limit(auto_rate)
        except Exception:
            pass
        if ua:
            try:
                wiki.set_user_agent(ua)
            except Exception:
                pass

    def _opt_bool(self, key: str, default: bool) -> bool:
        v = self.plugin.get_option_value(key)
        return bool(default if v is None else v)

    def _opt_int(self, key: str, default: int) -> int:
        v = self.plugin.get_option_value(key)
        try:
            return int(default if v is None else v)
        except Exception:
            return default

    def _params_bool(self, params: dict, key: str, fallback_opt: Optional[str], default: bool) -> bool:
        if key in params and params[key] is not None:
            return bool(params[key])
        if fallback_opt:
            return self._opt_bool(fallback_opt, default)
        return bool(default)

    def _params_int(self, params: dict, key: str, fallback_opt: Optional[str], default: int) -> int:
        if key in params and params[key] is not None:
            try:
                return int(params[key])
            except Exception:
                return default
        if fallback_opt:
            return self._opt_int(fallback_opt, default)
        return int(default)

    def _clip_text(self, text: str, max_chars: Optional[int]) -> str:
        if text is None:
            return ""
        if not max_chars or max_chars <= 0:
            return text
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 3] + "..."

    def _clip_list(self, items: List[Any], max_items: Optional[int]) -> List[Any]:
        if not isinstance(items, list):
            return []
        if not max_items or max_items <= 0 or len(items) <= max_items:
            return items
        return items[:max_items]

    def _wrap_disambig(self, e: DisambiguationError) -> dict:
        # Provide options to let the assistant choose a target
        return {
            "error": "Disambiguation required",
            "type": "DisambiguationError",
            "title": getattr(e, "title", None),
            "options": getattr(e, "options", []),
        }

    def _auto_suggest_param(self, p: dict) -> bool:
        return self._params_bool(p, "auto_suggest", "auto_suggest", True)

    def _redirect_param(self, p: dict) -> bool:
        return self._params_bool(p, "redirect", "redirect", True)

    # Decide whether to return full content (no clipping)
    def _full_content_param(self, p: dict) -> bool:
        if p.get("full") is not None:
            return bool(p["full"])
        if p.get("no_clip") is not None:  # alias
            return bool(p["no_clip"])
        return bool(self.plugin.get_option_value("content_full_default") or False)

    # ---------------------- Commands: Language ----------------------

    def cmd_wp_set_lang(self, item: dict) -> dict:
        p = item.get("params", {})
        lang = (p.get("lang") or "").strip()
        if not lang:
            return self.make_response(item, "Param 'lang' required")
        self.plugin.set_option_value("lang", lang)
        self._apply_settings()
        return self.make_response(item, {"ok": True, "lang": lang})

    def cmd_wp_get_lang(self, item: dict) -> dict:
        lang = (self.plugin.get_option_value("lang") or "en").strip()
        return self.make_response(item, {"lang": lang})

    def cmd_wp_languages(self, item: dict) -> dict:
        self._require_lib()
        p = item.get("params", {})
        short = bool(p.get("short", False))
        langs = wiki.languages()  # dict: code -> localized name
        if short:
            data = sorted(list(langs.keys()))
        else:
            data = langs
        max_items = self._opt_int("max_list_items", 50)
        if isinstance(data, list):
            data = self._clip_list(data, max_items)
        elif isinstance(data, dict):
            data = dict(list(data.items())[:max_items])
        return self.make_response(item, {"data": data})

    # ---------------------- Commands: Search / Suggest ----------------------

    def cmd_wp_search(self, item: dict) -> dict:
        self._require_lib()
        p = item.get("params", {})
        q = (p.get("q") or p.get("query") or "").strip()
        if not q:
            return self.make_response(item, "Param 'q' required")
        results_limit = self._params_int(p, "results", "results_default", 10)
        suggestion = bool(p.get("suggestion", False))
        if suggestion:
            res, sugg = wiki.search(q, results=results_limit, suggestion=True)
            return self.make_response(item, {"results": res, "suggestion": sugg})
        else:
            res = wiki.search(q, results=results_limit, suggestion=False)
            return self.make_response(item, {"results": res})

    def cmd_wp_suggest(self, item: dict) -> dict:
        self._require_lib()
        p = item.get("params", {})
        q = (p.get("q") or p.get("query") or "").strip()
        if not q:
            return self.make_response(item, "Param 'q' required")
        sugg = wiki.suggest(q)
        return self.make_response(item, {"suggestion": sugg})

    # ---------------------- Commands: Read ----------------------

    def cmd_wp_summary(self, item: dict) -> dict:
        self._require_lib()
        p = item.get("params", {})
        title = (p.get("title") or p.get("q") or p.get("query") or "").strip()
        if not title:
            return self.make_response(item, "Param 'title' (or 'q') required")
        sentences = self._params_int(p, "sentences", "summary_sentences", 3)
        auto_suggest = self._auto_suggest_param(p)
        redirect = self._redirect_param(p)
        summary = wiki.summary(title, sentences=sentences, auto_suggest=auto_suggest, redirect=redirect)
        url = None
        try:
            pg = wiki.page(title, auto_suggest=auto_suggest, redirect=redirect)
            url = getattr(pg, "url", None)
            title = getattr(pg, "title", title)
        except Exception:
            pass
        return self.make_response(item, {"title": title, "summary": summary, "url": url})

    def cmd_wp_page(self, item: dict) -> dict:
        self._require_lib()
        p = item.get("params", {})
        title = (p.get("title") or "").strip()
        if not title:
            return self.make_response(item, "Param 'title' required")
        auto_suggest = self._auto_suggest_param(p)
        redirect = self._redirect_param(p)
        content_chars = self._params_int(p, "content_chars", "content_max_chars", 5000)
        max_list = self._params_int(p, "max_list_items", "max_list_items", 50)
        full = self._full_content_param(p)

        include = p.get("include")
        if not include:
            include = ["title", "url", "summary", "content", "sections", "categories", "links", "images", "references"]

        pg = wiki.page(title, auto_suggest=auto_suggest, redirect=redirect)
        data: Dict[str, Any] = {}

        if "title" in include:
            data["title"] = getattr(pg, "title", title)
        if "url" in include:
            data["url"] = getattr(pg, "url", None)
        if "summary" in include:
            try:
                data["summary"] = getattr(pg, "summary", None)
            except Exception:
                data["summary"] = None
        if "content" in include:
            try:
                raw = getattr(pg, "content", None)
                data["content_body"] = raw if full else self._clip_text(raw, content_chars)
            except Exception:
                data["content_body"] = None
        if "sections" in include:
            try:
                data["sections"] = self._clip_list(getattr(pg, "sections", []), max_list)
            except Exception:
                data["sections"] = []
        if "categories" in include:
            try:
                data["categories"] = self._clip_list(getattr(pg, "categories", []), max_list)
            except Exception:
                data["categories"] = []
        if "links" in include:
            try:
                data["links"] = self._clip_list(getattr(pg, "links", []), max_list)
            except Exception:
                data["links"] = []
        if "images" in include:
            try:
                data["images"] = self._clip_list(getattr(pg, "images", []), max_list)
            except Exception:
                data["images"] = []
        if "references" in include:
            try:
                data["references"] = self._clip_list(getattr(pg, "references", []), max_list)
            except Exception:
                data["references"] = []

        if bool(p.get("open", False)):
            try:
                if data.get("url"):
                    self.plugin.open_url(data["url"])
            except Exception:
                pass

        return self.make_response(item, data)

    def cmd_wp_section(self, item: dict) -> dict:
        self._require_lib()
        p = item.get("params", {})
        title = (p.get("title") or "").strip()
        section = (p.get("section") or "").strip()
        if not title or not section:
            return self.make_response(item, "Params 'title' and 'section' required")
        auto_suggest = self._auto_suggest_param(p)
        redirect = self._redirect_param(p)
        content_chars = self._params_int(p, "content_chars", "content_max_chars", 5000)
        full = self._full_content_param(p)

        pg = wiki.page(title, auto_suggest=auto_suggest, redirect=redirect)
        txt = pg.section(section)

        return self.make_response(item, {
            "title": getattr(pg, "title", title),
            "section": section,
            "content_body": (txt or "") if full else self._clip_text(txt or "", content_chars),
            "url": getattr(pg, "url", None),
        })

    # ---------------------- Commands: Discover ----------------------

    def cmd_wp_random(self, item: dict) -> dict:
        self._require_lib()
        p = item.get("params", {})
        count = self._params_int(p, "results", "results_default", 1)
        res = wiki.random(pages=count)
        if isinstance(res, str):
            res = [res]
        return self.make_response(item, {"results": res})

    def cmd_wp_geosearch(self, item: dict) -> dict:
        self._require_lib()
        p = item.get("params", {})
        lat = p.get("lat") or p.get("latitude")
        lon = p.get("lon") or p.get("lng") or p.get("longitude")
        if lat is None or lon is None:
            return self.make_response(item, "Params 'lat' and 'lon' required")
        try:
            lat = float(lat)
            lon = float(lon)
        except Exception:
            return self.make_response(item, "Params 'lat' and 'lon' must be numbers")
        radius = self._params_int(p, "radius", None, 1000)
        results_limit = self._params_int(p, "results", "results_default", 10)
        title = p.get("title")
        res = wiki.geosearch(latitude=lat, longitude=lon, title=title, results=results_limit, radius=radius)
        return self.make_response(item, {"results": res})

    # ---------------------- Commands: Utilities ----------------------

    def cmd_wp_open(self, item: dict) -> dict:
        self._require_lib()
        p = item.get("params", {})
        url = p.get("url")
        title = p.get("title")
        auto_suggest = self._auto_suggest_param(p)
        redirect = self._redirect_param(p)

        if not url and not title:
            return self.make_response(item, "Provide 'url' or 'title'")
        if not url:
            pg = wiki.page(title, auto_suggest=auto_suggest, redirect=redirect)
            url = getattr(pg, "url", None)
        if not url:
            return self.make_response(item, "Unable to resolve URL")
        try:
            self.plugin.open_url(url)
        except Exception:
            pass
        return self.make_response(item, {"ok": True, "url": url})